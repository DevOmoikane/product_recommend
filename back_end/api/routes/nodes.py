from fastapi import APIRouter, HTTPException
from ml_library.utils.nodes.node_definition import NodeRegistry
from ml_library.utils.log import logerror

router = APIRouter(prefix="/api/node-definitions", tags=["nodes"])


@router.get("")
async def get_node_definitions():
    try:
        node_definitions = NodeRegistry.get_nodes()
        return node_definitions
    except Exception as e:
        logerror(f"Error getting node definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))