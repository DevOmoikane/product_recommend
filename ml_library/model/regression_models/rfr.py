from ..regression import ModelRegression, ModelRegressionRegistry
from sklearn.ensemble import RandomForestRegressor
from typing import Any
import numpy as np
import pandas as pd
from ...utils.node_definition import node


@ModelRegressionRegistry.register("rfr", friendly_name="Random Forest Regressor")
@node(
    friendly_name="Random Forest Regressor",
    description="Random Forest Regressor",
    icon="fa fa-tree",
    color="#5E0953"
)
class ModelRFR(ModelRegression):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = RandomForestRegressor(**kwargs)

    def fit(self, X_train: Any, y_train: Any, **kwargs) -> Any:
        self._model.fit(X_train, y_train, **kwargs)
        return self

    def predict(self, X: Any) -> Any:
        return self._model.predict(X)