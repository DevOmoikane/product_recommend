from fastapi import APIRouter, HTTPException
from back_end.api.schemas.requests import TrainRequest
from back_end.api.schemas.responses import TrainResponse
from back_end.core.trainer import Trainer
from back_end.core.regression_trainer import RegressionTrainer
from back_end.api.dependencies.config import get_config
from ml_library.utils.log import loginfo, logwarning, raiselog

router = APIRouter(prefix="/api", tags=["training"])

config = get_config("config.yaml")

trainer: Trainer = None
trainer_regression: RegressionTrainer = None


@router.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest):
    global trainer, trainer_regression

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