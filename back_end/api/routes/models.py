from fastapi import APIRouter, HTTPException
from back_end.api.dependencies.config import get_config
from back_end.core.model_base import ModelRegistry
from ml_library.utils.log import raiselog

router = APIRouter(prefix="/api/models", tags=["models"])

config = get_config("config.yaml")


@router.post("/load")
async def load_model(model_path: str = None, model_name: str = None):
    try:
        path = model_path or config.get("persistence.default_model", "./models/model.pkl")
        return {"status": "success", "model_path": path}

    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@router.get("/list")
async def list_models():
    return {"available_models": ModelRegistry.list_models()}