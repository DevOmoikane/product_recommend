import importlib
import json
import uuid
import threading
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from pprint import pformat
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from ..log import *
from ..config import load_config, Config
from .node_definition import auto_detect_merge_strategy, is_list_type, is_dict_type, is_set_type, is_tuple_type, get_compatible_merge_strategies


def debug_broadcast_wrapper(execution_id: str, node_id: str, callback: Callable[[Dict], None]):
    def _broadcast_debug(message: str, data: Any):
        callback({
            "type": "debug_log",
            "execution_id": execution_id,
            "node_id": node_id,
            "message": message,
            "data": str(data)[:500] if data is not None else None
        })
    return _broadcast_debug


def create_instance_from_string(full_path: str):
    try:
        module_path, _, class_name = full_path.rpartition('.')
        module = importlib.import_module(module_path)
        class_obj = getattr(module, class_name)
        return class_obj
    except (ImportError, AttributeError) as e:
        logerror(f"Error creating instance from string: {e}")
        return None


class GenericInstance:
    def __init__(self, _class: str):
        self._class = _class
        self.inputs = []
        self.outputs = []
        self.fields = []
        self._instance = create_instance_from_string(self._class)

    def execute(self, method: str, *args, **kwargs) -> Any:
        if hasattr(self._instance, method):
            method_instance = getattr(self._instance, method)
            if callable(method_instance):
                result = method_instance(*args, **kwargs)
                return result
        else:
            logerror(f"Method {method} not found in class {self._class}")
            return None


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowNode:
    id: str
    type: str
    fields: Dict[str, Any] = field(default_factory=dict)
    processing_function: str = "output"


@dataclass
class WorkflowConnection:
    from_node: str
    from_output: str
    to_node: str
    to_input: str


@dataclass
class WorkflowDefinitionModel:
    name: str
    description: str = ""
    nodes: List[WorkflowNode] = field(default_factory=list)
    connections: List[WorkflowConnection] = field(default_factory=list)
    initial_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "fields": n.fields,
                    "processing_function": n.processing_function
                }
                for n in self.nodes
            ],
            "connections": [
                {
                    "from_node": c.from_node,
                    "from_output": c.from_output,
                    "to_node": c.to_node,
                    "to_input": c.to_input
                }
                for c in self.connections
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinitionModel":
        nodes = [WorkflowNode(**n) for n in data.get("nodes", [])]
        connections = [WorkflowConnection(**c) for c in data.get("connections", [])]
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            nodes=nodes,
            connections=connections
        )


@dataclass
class WorkflowExecution:
    execution_id: str
    workflow: WorkflowDefinitionModel
    initial_data: Dict[str, Any]
    status: ExecutionStatus = ExecutionStatus.PENDING
    node_statuses: Dict[str, NodeStatus] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "node_statuses": {k: v.value for k, v in self.node_statuses.items()},
            "results": self.results,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None
        }


class WorkflowStorage:
    def __init__(self, config: Optional[Config] = None):
        self._config = config
        self._storage_path = Path(
            (config.get("workflows.storage_path", "./workflows/") if config else "./workflows/")
        )
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, workflow: WorkflowDefinitionModel) -> bool:
        try:
            filepath = self._storage_path / f"{workflow.name}.json"
            with open(filepath, "w") as f:
                json.dump(workflow.to_dict(), f, indent=2)
            loginfo(f"Saved workflow '{workflow.name}' to {filepath}")
            return True
        except Exception as e:
            logerror(f"Error saving workflow '{workflow.name}': {e}")
            return False

    def load(self, name: str) -> Optional[WorkflowDefinitionModel]:
        try:
            filepath = self._storage_path / f"{name}.json"
            if not filepath.exists():
                return None
            with open(filepath, "r") as f:
                data = json.load(f)
            return WorkflowDefinitionModel.from_dict(data)
        except Exception as e:
            logerror(f"Error loading workflow '{name}': {e}")
            return None

    def list(self) -> List[str]:
        try:
            return [f.stem for f in self._storage_path.glob("*.json")]
        except Exception as e:
            logerror(f"Error listing workflows: {e}")
            return []

    def delete(self, name: str) -> bool:
        try:
            filepath = self._storage_path / f"{name}.json"
            if filepath.exists():
                filepath.unlink()
                loginfo(f"Deleted workflow '{name}'")
                return True
            return False
        except Exception as e:
            logerror(f"Error deleting workflow '{name}': {e}")
            return False


class ExecutionStore:
    def __init__(self):
        self._executions: Dict[str, WorkflowExecution] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def create(self, workflow: WorkflowDefinitionModel, initial_data: Dict[str, Any]) -> str:
        execution_id = str(uuid.uuid4())
        node_statuses = {node.id: NodeStatus.PENDING for node in workflow.nodes}
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow=workflow,
            initial_data=initial_data,
            node_statuses=node_statuses
        )
        with self._lock:
            self._executions[execution_id] = execution
        loginfo(f"Created execution {execution_id} for workflow '{workflow.name}'")
        return execution_id

    def get(self, execution_id: str) -> Optional[WorkflowExecution]:
        with self._lock:
            return self._executions.get(execution_id)

    def update_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        node_statuses: Optional[Dict[str, NodeStatus]] = None,
        results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution:
                execution.status = status
                if node_statuses:
                    execution.node_statuses.update(node_statuses)
                if results:
                    execution.results.update(results)
                if error:
                    execution.error = error
                if status == ExecutionStatus.RUNNING and not execution.started_at:
                    execution.started_at = datetime.now()
                elif status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.STOPPED):
                    execution.ended_at = datetime.now()
        self._notify_subscribers(execution_id)

    def update_node_status(self, execution_id: str, node_id: str, status: NodeStatus, result: Any = None):
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution:
                execution.node_statuses[node_id] = status
                if result is not None:
                    execution.results[node_id] = result
        self._notify_subscribers(execution_id)

    def subscribe(self, execution_id: str, callback: Callable):
        self._subscribers[execution_id].append(callback)

    def unsubscribe(self, execution_id: str, callback: Callable):
        if callback in self._subscribers[execution_id]:
            self._subscribers[execution_id].remove(callback)

    def _notify_subscribers(self, execution_id: str):
        execution = self.get(execution_id)
        if execution:
            for callback in self._subscribers.get(execution_id, []):
                try:
                    callback(execution.to_dict())
                except Exception as e:
                    logerror(f"Error notifying subscriber: {e}")

    def delete(self, execution_id: str):
        with self._lock:
            if execution_id in self._executions:
                del self._executions[execution_id]
                loginfo(f"Deleted execution {execution_id} from store")


class WorkflowExecutor:
    def __init__(
        self,
        workflow: WorkflowDefinitionModel,
        execution_id: str,
        execution_store: ExecutionStore,
        config: Optional[Config] = None
    ):
        self.workflow = workflow
        self.execution_id = execution_id
        self._execution_store = execution_store
        self._config = config
        self._stop_requested = False
        self._stop_grace_period = config.get("workflows.execution.stop_grace_period_seconds", 30) if config else 30
        self._force_kill_after = config.get("workflows.execution.force_kill_after_seconds", 60) if config else 60

    def validate(self) -> List[str]:
        errors = []
        node_map = {node.id: node for node in self.workflow.nodes}

        for node in self.workflow.nodes:
            cls = create_instance_from_string(node.type)
            if cls is None:
                errors.append(f"Node '{node.id}': Cannot instantiate class '{node.type}'")
                continue
            if not hasattr(cls, node.processing_function):
                errors.append(f"Node '{node.id}': Processing function '{node.processing_function}' not found in class")

        for conn in self.workflow.connections:
            if conn.from_node not in node_map:
                errors.append(f"Connection: Source node '{conn.from_node}' not found")
            if conn.to_node not in node_map:
                errors.append(f"Connection: Target node '{conn.to_node}' not found")
            else:
                source_types = self._get_node_output_types(conn.from_node, conn.from_output)
                target_input_types = self._get_node_input_types(node_map[conn.to_node])
                target_types = target_input_types.get(conn.to_input, [])
                if not self._types_compatible(source_types, target_types):
                    errors.append(
                        f"Connection: Incompatible types - "
                        f"{conn.from_node}.{conn.from_output} ({source_types}) -> "
                        f"{conn.to_node}.{conn.to_input} ({target_types})"
                    )

        cycle_errors = self._check_circular_dependencies()
        errors.extend(cycle_errors)

        return errors

    def _check_circular_dependencies(self) -> List[str]:
        errors = []
        graph = defaultdict(list)
        for conn in self.workflow.connections:
            graph[conn.from_node].append(conn.to_node)

        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    return path + [neighbor]

            rec_stack.remove(node)
            return None

        for node in graph:
            if node not in visited:
                cycle = has_cycle(node, [])
                if cycle:
                    errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
                    break

        return errors

    def _topological_sort(self) -> List[WorkflowNode]:
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        node_map = {node.id: node for node in self.workflow.nodes}

        for conn in self.workflow.connections:
            graph[conn.from_node].append(conn.to_node)
            in_degree[conn.to_node] += 1

        queue = [node_id for node_id in node_map if in_degree[node_id] == 0]
        sorted_nodes = []

        while queue:
            node_id = queue.pop(0)
            sorted_nodes.append(node_map[node_id])

            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(node_map):
            logwarning(f"Topological sort incomplete: {len(sorted_nodes)}/{len(node_map)} nodes")

        return sorted_nodes

    @debug_return
    def _get_node_input_types(self, node: WorkflowNode) -> Dict[str, Any]:
        node_type = create_instance_from_string(node.type)
        if node_type is None:
            return {}
        if not hasattr(node_type, "_node_meta"):
            return {}
        meta = node_type._node_meta
        input_types = {}
        for inp in meta.get("inputs", []):
            input_types[inp["id"]] = inp.get("type")
        return input_types

    @debug_return
    def _get_node_input_merge(self, node: WorkflowNode) -> Dict[str, str]:
        node_type = create_instance_from_string(node.type)
        if node_type is None:
            return {}
        if not hasattr(node_type, "_node_meta"):
            return {}
        return node_type._node_meta.get("input_merge", {})

    @debug_return
    def _get_node_output_types(self, node_id: str, output_name: str) -> List[str]:
        node_map = {node.id: node for node in self.workflow.nodes}
        node = node_map.get(node_id)
        if node is None:
            return []
        node_type = create_instance_from_string(node.type)
        if node_type is None:
            return []
        if not hasattr(node_type, "_node_meta"):
            return []
        meta = node_type._node_meta
        for out in meta.get("outputs", []):
            if out["id"] == output_name:
                return out.get("type", [])
        return []

    def _types_compatible(self, source_types: List[str], target_types: List[str]) -> bool:
        if not source_types or not target_types:
            return True
        compatible_strategies = get_compatible_merge_strategies(source_types, target_types)
        return len(compatible_strategies) > 0

    def _get_output_id_for_function(self, node: WorkflowNode, func_name: str) -> str:
        node_type = create_instance_from_string(node.type)
        if node_type is None or not hasattr(node_type, "_node_meta"):
            return func_name
        meta = node_type._node_meta
        for out in meta.get("outputs", []):
            if out.get("function") == func_name or out.get("id") == func_name:
                return out.get("id", func_name)
        return func_name

    @debug_return
    def _merge_values(self, values: List[Any], strategy: str) -> Any:
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        
        if strategy == "update":
            result = {}
            for v in values:
                if isinstance(v, dict):
                    result.update(v)
            return result
        
        if strategy == "append":
            result = []
            for v in values:
                if isinstance(v, list):
                    result.extend(v)
                else:
                    result.append(v)
            return result
        
        if strategy == "extend":
            result = []
            for v in values:
                if isinstance(v, (list, tuple)):
                    result.extend(v)
                else:
                    result.append(v)
            return tuple(result)
        
        if strategy == "union":
            result = set()
            for v in values:
                if isinstance(v, (set, frozenset)):
                    result |= v
                elif isinstance(v, (list, tuple)):
                    result.update(v)
                else:
                    result.add(v)
            return result
        
        if strategy == "first":
            return values[0]
        
        if strategy == "last":
            return values[-1]
        
        return values[-1]

    @debug_return
    def _resolve_inputs(self, node: WorkflowNode, results: Dict[str, Any], on_status: Optional[Callable[[Dict], None]] = None) -> Dict[str, Any]:
        input_connections = defaultdict(list)

        for conn in self.workflow.connections:
            loginfo(f"Processing connection: {conn.from_node} -> {conn.to_node} with output {conn.from_output} to input {conn.to_input}")
            loginfo(f"Node id = {node.id}, results = {pformat(results)}")
            if conn.to_node == node.id and conn.from_node in results:
                value = results[conn.from_node].get(conn.from_output)
                if value is not None:
                    input_connections[conn.to_input].append(value)

        logobject(input_connections, "Input Connections")

        input_types = self._get_node_input_types(node)
        input_merge = self._get_node_input_merge(node)

        logobject(input_merge, "Input Merge => ")

        inputs = {}

        for field_name, field_value in node.fields.items():
            if field_name not in inputs:
                inputs[field_name] = field_value
        logobject(inputs, "Inputs (2) => ")

        for key, value in self.workflow.initial_data.items():
            if key not in inputs:
                inputs[key] = value
        logobject(inputs, "Inputs (3) => ")

        for input_name, values in input_connections.items():
            loginfo(f"Processing input: {input_name} with {len(values)} values => {pformat(values)}")
            if len(values) >= 1:
                expected_types = input_types.get(input_name)
                strategy = input_merge.get(input_name)
                if not strategy:
                    strategy = auto_detect_merge_strategy(expected_types)
                logobject(strategy, f"Strategy for {input_name} => ")
                inputs[input_name] = self._merge_values(values, strategy)
            elif len(values) == 0:
                inputs[input_name] = values[0] if values else None
        logobject(inputs, "Inputs (1) => ")

        if on_status is not None:
            inputs["_broadcast"] = debug_broadcast_wrapper(self.execution_id, node.id, on_status)

        return inputs

    def execute(self, initial_data: Dict[str, Any], on_status: Callable[[Dict], None]):
        self.workflow.initial_data = initial_data

        errors = self.validate()
        if errors:
            self._execution_store.update_status(
                self.execution_id,
                ExecutionStatus.FAILED,
                error="; ".join(errors)
            )
            return

        self._execution_store.update_status(self.execution_id, ExecutionStatus.RUNNING)

        sorted_nodes = self._topological_sort()
        results = {}

        for node in sorted_nodes:
            if self._stop_requested:
                self._execution_store.update_status(
                    self.execution_id,
                    ExecutionStatus.STOPPED
                )
                for remaining_node in sorted_nodes[sorted_nodes.index(node):]:
                    self._execution_store.update_node_status(
                        self.execution_id,
                        remaining_node.id,
                        NodeStatus.SKIPPED
                    )
                return

            self._execution_store.update_node_status(
                self.execution_id,
                node.id,
                NodeStatus.RUNNING
            )
            on_status({
                "type": "node_started",
                "execution_id": self.execution_id,
                "node_id": node.id
            })

            try:
                cls = create_instance_from_string(node.type)
                inputs = self._resolve_inputs(node, results, on_status)
                method_inputs = {k: v for k, v in inputs.items() if not k.startswith("_")}

                method = getattr(cls, node.processing_function)
                output = method(**method_inputs)

                output_id = self._get_output_id_for_function(node, node.processing_function)
                results[node.id] = {output_id: output}

                self._execution_store.update_node_status(
                    self.execution_id,
                    node.id,
                    NodeStatus.COMPLETED,
                    {output_id: output}
                )

                on_status({
                    "type": "node_completed",
                    "execution_id": self.execution_id,
                    "node_id": node.id,
                    "result": {output_id: str(output)[:200]}
                })

            except Exception as e:
                logerror(f"Error executing node '{node.id}': {e}")
                self._execution_store.update_status(
                    self.execution_id,
                    ExecutionStatus.FAILED,
                    error=f"Node '{node.id}' failed: {str(e)}"
                )
                on_status({
                    "type": "node_failed",
                    "execution_id": self.execution_id,
                    "node_id": node.id,
                    "error": str(e)
                })
                return

        self._execution_store.update_status(
            self.execution_id,
            ExecutionStatus.COMPLETED
        )
        on_status({
            "type": "execution_completed",
            "execution_id": self.execution_id,
            "results": {node_id: list(results.get(node_id, {}).keys()) for node_id in results}
        })

    def stop(self):
        self._stop_requested = True
        loginfo(f"Stop requested for execution {self.execution_id}")