from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import logging

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

from app.trainer import Trainer
from app.regression_trainer import RegressionTrainer
from app.recommender import Recommender
from ml_library.utils.config import load_config
from ml_library.data.data_source import DataSource
from ml_library.utils.log import *


app = FastAPI(title="Product Recommendation API", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

config = load_config("config.yaml")

trainer: Optional[Trainer] = None
trainer_regression: Optional[RegressionTrainer] = None
recommender_new_item: Optional[Recommender] = None
recommender_repurchase: Optional[RegressionTrainer] = None


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


class TrainResponse(BaseModel):
    status: str
    model_type: str
    model_name: str
    matrix_shape: Optional[tuple] = None
    saved_path: Optional[str] = None


class RecommendRequest(BaseModel):
    user_id: int
    n_items: int = 10
    filter_already_liked: bool = True
    items_to_exclude: Optional[List[int]] = None


class SimilarItemsRequest(BaseModel):
    item_id: int
    n_items: int = 10


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest):
    global trainer, trainer_regression, recommender_new_item
    
    try:
        trainer = Trainer(config_path="config.yaml")
        
        model = trainer.fit(
            model_type=request.model_type,
            params=request.params,
            user_col=request.user_col,
            item_col=request.item_col,
            rating_col=request.rating_col,
            interactions_query=request.interactions_query,
            items_query=request.items_query,
            users_query=request.users_query,
            model_name="new_item",
            use_weighted=request.use_weighted
        )
        
        matrix_shape = None
        if trainer.matrix is not None:
            matrix_shape = trainer.matrix.shape
        
        saved_path = None
        if request.save_model:
            saved_path = trainer.save_model(
                model_path=request.model_path or config.get("persistence.default_model", "./models/model.pkl"),
                user_col=request.user_col,
                item_col=request.item_col,
                rating_col=request.rating_col,
                interactions_query=request.interactions_query,
                items_query=request.items_query,
                users_query=request.users_query
            )
        
        trainer_regression = RegressionTrainer(config_path="config.yaml")
        trainer_regression.fit(use_weighted=request.use_weighted)
        
        repurchase_model_path = config.get("persistence.repurchase_model", "./models/model_repurchase.pkl")
        trainer_regression.save_model(repurchase_model_path)
        loginfo(f"Repurchase regression model trained and saved to {repurchase_model_path}")
        
        return TrainResponse(
            status="success",
            model_type=trainer._model_type,
            model_name="new_item",
            matrix_shape=matrix_shape,
            saved_path=saved_path
        )
    
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))

@app.post("/recommend/new-item")
async def recommend_new_items(request: RecommendRequest):
    global recommender_new_item
    
    if recommender_new_item is None:
        model_path = config.get("persistence.default_model", "./models/model.pkl")
        recommender_new_item = Recommender(model_path)
    
    try:
        recommendations = recommender_new_item.recommend_new_item(
            user_id=request.user_id,
            n_items=request.n_items,
            items_to_exclude=request.items_to_exclude,
        )
        
        return {
            "user_id": request.user_id,
            "recommendations": [
                {"item_id": item_id, "name": name, "score": score}
                for item_id, name, score in recommendations
            ]
        }
    
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@app.post("/recommend/repurchase")
async def recommend_repurchase_items(request: RecommendRequest):
    global recommender_repurchase
    
    try:
        if recommender_repurchase is None:
            model_path = config.get("persistence.repurchase_model", "./models/model_repurchase.pkl")
            recommender_repurchase = RegressionTrainer(config_path="config.yaml")
            try:
                recommender_repurchase.load_model(model_path)
                loginfo(f"Loaded repurchase model from {model_path}")
            except Exception as e:
                logwarning(f"Could not load repurchase model: {e}. Training new model...")
                recommender_repurchase.fit()
                recommender_repurchase.save_model(model_path)
        
        recommendations = recommender_repurchase.recommend_repurchase(
            user_id=request.user_id,
            n_items=request.n_items,
            items_to_exclude=request.items_to_exclude,
        )
        
        return {
            "user_id": request.user_id,
            "recommendations": [
                {"item_id": item_id, "name": name, "score": score}
                for item_id, name, score in recommendations
            ]
        }
    
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@app.post("/recommend")
async def recommend_items(request: RecommendRequest):
    global recommender_new_item
    
    if recommender_new_item is None:
        model_path = config.get("persistence.default_model", "./models/model.pkl")
        recommender_new_item = Recommender(model_path)
    
    try:
        recommendations = recommender_new_item.recommend(
            user_id=request.user_id,
            n_items=request.n_items,
            filter_already_liked_items=request.filter_already_liked,
            items_to_exclude=request.items_to_exclude,
        )
        
        return {
            "user_id": request.user_id,
            "recommendations": [
                {"item_id": item_id, "score": score}
                for item_id, score in recommendations
            ]
        }
    
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@app.post("/items/similar")
async def get_similar_items(request: SimilarItemsRequest):
    global recommender_new_item
    
    if recommender_new_item is None:
        model_path = config.get("persistence.default_models.new_item", "./models/model_newitem.pkl")
        recommender_new_item = Recommender(model_path)
    
    try:
        similar_items = recommender_new_item.get_similar_items(
            item_id=request.item_id,
            n_items=request.n_items,
        )
        
        return {
            "item_id": request.item_id,
            "similar_items": [
                {"item_id": item_id, "score": score}
                for item_id, score in similar_items
            ]
        }
    
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@app.post("/models/load")
async def load_model(model_path: Optional[str] = None, model_name: Optional[str] = None):
    global recommender_new_item, recommender_repurchase
    
    try:
        path = model_path or config.get("persistence.default_model", "./models/model.pkl")
        return {"status": "success", "model_path": path}
    
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@app.get("/models/list")
async def list_models():
    from app.model_base import ModelRegistry
    return {"available_models": ModelRegistry.list_models()}


class ClientDataResponse(BaseModel):
    client: Optional[Dict[str, Any]] = None
    interactions: List[Dict[str, Any]] = []
    orders: List[Dict[str, Any]] = []
    total_interactions: int = 0
    total_orders: int = 0


@app.get("/client/{client_id}", response_model=ClientDataResponse)
async def get_client_data(client_id: int):
    try:
        data_source = DataSource(config_path="config.yaml")
        connector = data_source.get_connector()
        
        client_data = connector.get_user(client_id)
        interactions_data = connector.get_user_interactions(client_id)
        
        orders = []
        if hasattr(connector, 'get_user_orders'):
            orders_data = connector.get_user_orders(client_id)
            orders = orders_data.to_dict('records') if hasattr(orders_data, 'to_dict') else []
        
        return ClientDataResponse(
            client=client_data.to_dict('records')[0] if hasattr(client_data, 'to_dict') and len(client_data) > 0 else (client_data if isinstance(client_data, dict) else None),
            interactions=interactions_data.to_dict('records') if hasattr(interactions_data, 'to_dict') else [],
            orders=orders,
            total_interactions=len(interactions_data) if hasattr(interactions_data, '__len__') else 0,
            total_orders=len(orders)
        )
    except Exception as e:
        raiselog(HTTPException(status_code=500, detail=str(e)))


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/favicon.ico")
async def serve_favicon():
    return FileResponse("static/favicon.ico")


class ConfigUpdateRequest(BaseModel):
    content: str


@app.get("/config")
async def get_config():
    try:
        with open("config.yaml", "r") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config")
async def save_config(request: ConfigUpdateRequest):
    try:
        with open("config.yaml", "w") as f:
            f.write(request.content)
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/reload")
async def reload_config():
    global config
    try:
        config = load_config("config.yaml")
        return {"status": "success", "message": "Configuration reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))