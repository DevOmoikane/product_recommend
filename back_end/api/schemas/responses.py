from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class TrainResponse(BaseModel):
    status: str
    model_type: str
    model_name: str
    matrix_shape: Optional[tuple] = None
    saved_path: Optional[str] = None


class SimilarItemsResponse(BaseModel):
    item_id: int
    similar_items: List[Dict[str, Any]]


class ClientDataResponse(BaseModel):
    client: Optional[Dict[str, Any]] = None
    interactions: List[Dict[str, Any]] = []
    orders: List[Dict[str, Any]] = []
    total_interactions: int = 0
    total_orders: int = 0


class RecommendationItem(BaseModel):
    item_id: int
    name: Optional[str] = None
    score: float


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[Dict[str, Any]]


class WorkflowStatusResponse(BaseModel):
    execution_id: str
    status: str
    node_statuses: Dict[str, Any]
    results: Dict[str, Any]
    error: Optional[str] = None