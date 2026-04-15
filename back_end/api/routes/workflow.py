from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio

from back_end.api.schemas.requests import (
    WorkflowDefinitionRequest,
    WorkflowExecutionRequest,
)
from back_end.api.schemas.responses import WorkflowStatusResponse
from ml_library.utils.nodes.workflow import (
    WorkflowStorage,
    ExecutionStore,
    WorkflowExecutor,
    WorkflowDefinitionModel,
    WorkflowNode,
    WorkflowConnection,
    ExecutionStatus,
)
from ml_library.utils.log import loginfo, logobject, logerror, raiselog
from back_end.api.dependencies.config import get_config

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

config = get_config("config.yaml")
workflow_storage = WorkflowStorage(config)
execution_store = ExecutionStore()
active_executors: Dict[str, WorkflowExecutor] = {}

workflow_connections: Dict[str, List[WebSocket]] = {}


async def run_workflow_async(execution_id: str, workflow: WorkflowDefinitionModel, initial_data: Dict):
    executor = WorkflowExecutor(workflow, execution_id, execution_store, config)
    active_executors[execution_id] = executor

    def on_status(status: Dict):
        asyncio.create_task(workflow_broadcast(execution_id, status))

    executor.execute(initial_data, on_status)

    if execution_id in active_executors:
        del active_executors[execution_id]


async def workflow_broadcast(execution_id: str, status: Dict):
    for connection in workflow_connections.get(execution_id, []):
        try:
            await connection.send_json(status)
        except Exception:
            pass


@router.post("/execute")
async def execute_workflow(request: WorkflowExecutionRequest):
    try:
        loginfo(f"Received workflow execution request: {request.workflow.name}")
        logobject(request, "workflow execution request details")
        workflow = WorkflowDefinitionModel(
            name=request.workflow.name,
            description=request.workflow.description,
            nodes=[WorkflowNode(**n.dict()) for n in request.workflow.nodes],
            connections=[WorkflowConnection(**c.dict()) for c in request.workflow.connections]
        )

        executor = WorkflowExecutor(workflow, "", execution_store, config)
        errors = executor.validate()
        if errors:
            raiselog(HTTPException(status_code=400, detail="; ".join(errors)), f"Validation errors: {errors}", True)

        execution_id = execution_store.create(workflow, request.initial_data)

        asyncio.create_task(run_workflow_async(execution_id, workflow, request.initial_data))

        return {"execution_id": execution_id, "status": "pending"}

    except HTTPException as e:
        raiselog(e, f"HTTP error executing workflow: {e}", True)
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)), f"Error executing workflow: {e}", True)


@router.get("/{execution_id}/status")
async def get_workflow_status(execution_id: str):
    execution = execution_store.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution.to_dict()


@router.post("/stop/{execution_id}")
async def stop_workflow(execution_id: str):
    executor = active_executors.get(execution_id)
    if not executor:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")
    executor.stop()
    return {"status": "stopping", "execution_id": execution_id}


@router.post("/save")
async def save_workflow(request: WorkflowDefinitionRequest):
    try:
        workflow = WorkflowDefinitionModel(
            name=request.name,
            description=request.description,
            nodes=[WorkflowNode(**n.dict()) for n in request.nodes],
            connections=[WorkflowConnection(**c.dict()) for c in request.connections]
        )
        if workflow_storage.save(workflow):
            return {"status": "success", "message": f"Workflow '{request.name}' saved"}
        raise HTTPException(status_code=500, detail="Failed to save workflow")
    except Exception as e:
        logerror(f"Error saving workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_workflows():
    return {"workflows": workflow_storage.list()}


@router.get("/{name}")
async def get_workflow(name: str):
    workflow = workflow_storage.load(name)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow.to_dict()


@router.delete("/{name}")
async def delete_workflow(name: str):
    if workflow_storage.delete(name):
        return {"status": "success", "message": f"Workflow '{name}' deleted"}
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.websocket("/{execution_id}")
async def workflow_websocket(websocket: WebSocket, execution_id: str):
    await websocket.accept()

    if execution_id not in workflow_connections:
        workflow_connections[execution_id] = []
    workflow_connections[execution_id].append(websocket)

    try:
        execution = execution_store.get(execution_id)
        if execution:
            await websocket.send_json({
                "type": "initial_status",
                "data": execution.to_dict()
            })

        while execution.status not in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.STOPPED]:
            await asyncio.sleep(1)
            logobject(execution, f"Execution {execution_id} current status: {execution.status}")
        logobject(execution, f"Execution {execution_id} final status: {execution.status}")
        await websocket.send_json({
            "type": "execution_completed",
            "data": execution.to_dict()
        })
    except WebSocketDisconnect:
        pass
    finally:
        if execution_id in workflow_connections:
            workflow_connections[execution_id] = [c for c in workflow_connections[execution_id] if c != websocket]
            if not workflow_connections[execution_id]:
                del workflow_connections[execution_id]