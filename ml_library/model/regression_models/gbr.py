from ..regression import ModelRegression, ModelRegressionRegistry
from sklearn.ensemble import GradientBoostingRegressor
from typing import Any
import numpy as np
import pandas as pd
from ...utils.node_definition import node


@ModelRegressionRegistry.register("gbr", friendly_name="Gradient Boosting Regressor")
@node(
    friendly_name="Gradient Boosting Regressor",
    description="Gradient Boosting Regressor",
    icon="fa fa-tree",
    color="#095E0D"
)
class ModelGBR(ModelRegression):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = GradientBoostingRegressor(**kwargs)

    def train(self, data: Any, **kwargs):
        super().train(data, **kwargs)

    def predict(self, X: Any) -> Any:
        return self._model.predict(X)
