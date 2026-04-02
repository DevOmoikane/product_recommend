from ..regression import ModelRegression, ModelRegressionRegistry
from sklearn.ensemble import RandomForestRegressor
from typing import Any
import numpy as np
import pandas as pd
from ...utils.nodes.node_definition import node


@ModelRegressionRegistry.register("rfr", friendly_name="Random Forest Regressor")
@node(
    friendly_name="Random Forest Regressor",
    description="Random Forest Regressor",
    icon="fa fa-tree",
    color="#5E0953"
)
class ModelRFR(ModelRegression):

    @classmethod
    def INPUT_TYPES(cls):
        super_input_types = super().INPUT_TYPES()
        this_input_types = {
            "required": {
                "n_estimators": {"type": int, "default": None, "description": "Number of trees in the forest"},
                "max_depth": {"type": int, "default": None, "description": "Maximum depth of the tree"},
                "min_samples_split": {"type": int, "default": None, "description": "Minimum number of samples required to split an internal node"},
                "min_samples_leaf": {"type": int, "default": None, "description": "Minimum number of samples required to be at a leaf node"},
                "max_features": {"type": str, "default": None, "description": "Number of features to consider when looking for the best split"},
                "random_state": {"type": int, "default": None, "description": "Seed for the random number generator"},
            }
        }
        all_types = super_input_types.copy()
        all_types["required"].update(this_input_types["required"])
        return all_types

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = RandomForestRegressor(**kwargs)

    def fit(self, X_train: Any, y_train: Any, **kwargs) -> Any:
        self._model.fit(X_train, y_train, **kwargs)
        return self

    def predict(self, X: Any) -> Any:
        return self._model.predict(X)