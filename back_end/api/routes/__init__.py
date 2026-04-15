from back_end.api.routes.workflow import router as workflow_router
from back_end.api.routes.training import router as training_router
from back_end.api.routes.recommendations import router as recommendations_router
from back_end.api.routes.models import router as models_router
from back_end.api.routes.config import router as config_router
from back_end.api.routes.nodes import router as nodes_router

__all__ = [
    "workflow_router",
    "training_router",
    "recommendations_router",
    "models_router",
    "config_router",
    "nodes_router",
]