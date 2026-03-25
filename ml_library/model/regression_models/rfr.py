from ..regression import ModelRegression, ModelRegressionRegistry
from sklearn.ensemble import RandomForestRegressor
from typing import Any
import numpy as np
import pandas as pd


@ModelRegressionRegistry.register("rfr", friendly_name="Random Forest Regressor")
class ModelRFR(ModelRegression):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = RandomForestRegressor(**kwargs)

    def fit(self, X_train: Any, y_train: Any, **kwargs) -> Any:
        self._model.fit(X_train, y_train, **kwargs)
        return self

    def predict(self, X: Any) -> Any:
        return self._model.predict(X)