from ..regression import ModelRegression, ModelRegressionRegistry
from sklearn.ensemble import GradientBoostingRegressor
from typing import Any
import numpy as np
import pandas as pd
from ...utils.nodes.node_definition import node


@ModelRegressionRegistry.register("gbr", friendly_name="Gradient Boosting Regressor")
@node(
    friendly_name="Gradient Boosting Regressor",
    description="Gradient Boosting Regressor",
    icon="fa fa-tree",
    color="#095E0D"
)
class ModelGBR(ModelRegression):

    @classmethod
    def INPUT_TYPES(cls):
        super_input_types = super().INPUT_TYPES()
        this_input_types = {
            "required": {
                "max_depth": {"type": int, "default": None, "description": "Maximum depth of the tree"},
                "n_estimators": {"type": int, "default": None, "description": "Number of trees in the forest"},
                "learning_rate": {"type": float, "default": None, "description": "Learning rate for the tree"},
                "subsample": {"type": float, "default": None, "description": "Fraction of samples used for fitting the individual base learners"},
                "random_state": {"type": int, "default": None, "description": "Seed for the random number generator"},
            }
        }
        all_types = super_input_types.copy()
        all_types["required"].update(this_input_types["required"])
        return all_types

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = GradientBoostingRegressor(**kwargs)

    def train(self, data: Any, **kwargs):
        super().train(data, **kwargs)

    def predict(self, X: Any) -> Any:
        return self._model.predict(X)
