from fastapi import APIRouter, HTTPException
from back_end.api.schemas.requests import RecommendRequest, SimilarItemsRequest
from back_end.core.recommender import Recommender
from back_end.core.regression_trainer import RegressionTrainer
from back_end.api.dependencies.config import get_config
from ml_library.utils.log import loginfo, logwarning, logerror, raiselog

router = APIRouter(prefix="/api/recommend", tags=["recommendations"])

config = get_config("config.yaml")

recommender_new_item: Recommender = None
recommender_repurchase: RegressionTrainer = None


@router.post("")
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


@router.post("/new-item")
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


@router.post("/repurchase")
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


@router.post("/similar")
async def get_similar_items(request: SimilarItemsRequest):
    global recommender_new_item

    if recommender_new_item is None:
        model_path = config.get("persistence.default_model", "./models/model.pkl")
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