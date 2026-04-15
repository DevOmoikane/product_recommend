from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class TrainRequest(BaseModel):
    model_type: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    user_col: Optional[str] = None
    item_col: Optional[str] = None
    rating_col: Optional[str] = None
    interactions_query: Optional[str] = None
    items_query: Optional[str] = None
    users_query: Optional[str] = None
    save_model: Optional[bool] = True
    model_path: Optional[str] = None
    use_weighted: Optional[bool] = False


class RecommendRequest(BaseModel):
    user_id: int
    n_items: int = 10
    filter_already_liked: bool = True
    items_to_exclude: Optional[List[int]] = None


class SimilarItemsRequest(BaseModel):
    item_id: int
    n_items: int = 10


class WorkflowNodeRequest(BaseModel):
    id: str
    type: str
    fields: Dict[str, Any] = {}
    processing_function: str = "output"


class WorkflowConnectionRequest(BaseModel):
    from_node: str
    from_output: str
    to_node: str
    to_input: str


class WorkflowDefinitionRequest(BaseModel):
    name: str
    description: str = ""
    nodes: List[WorkflowNodeRequest]
    connections: List[WorkflowConnectionRequest] = []


class WorkflowExecutionRequest(BaseModel):
    workflow: WorkflowDefinitionRequest
    initial_data: Dict[str, Any] = {}


class ConfigUpdateRequest(BaseModel):
    content: str