from ..recommendation import ModelRecommendation, ModelRecommendationRegistry
from implicit.als import AlternatingLeastSquares
from typing import Any
import numpy as np
import pandas as pd


@ModelRecommendationRegistry.register("als",  friendly_name="Alternating Least Squares")
class ModelALS(ModelRecommendation):
    def __init__(self, **kwargs):
        self._model = AlternatingLeastSquares(**kwargs)

    def fit(self, user_item_matrix: Any, **kwargs) -> Any:
        self._model.fit(user_item_matrix, **kwargs)
        return self

    def predict(self, user_id: int, N: int = 10) -> Any:
        return self._model.recommend(user_id, self._model.item_factors, N=N)
