from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from back_end.api.dependencies.config import get_config, reload_config

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    content: str


@router.get("")
async def get_config():
    try:
        with open("config.yaml", "r") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def save_config(request: ConfigUpdateRequest):
    try:
        with open("config.yaml", "w") as f:
            f.write(request.content)
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config_endpoint():
    try:
        reload_config("config.yaml")
        return {"status": "success", "message": "Configuration reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))