import numpy as np
import pandas as pd
from typing import Any, Optional, Dict, Tuple
from back_end.core.model_base import ModelBase
from ml_library.utils.config import load_config
from back_end.core.model_base import ModelRegistry


class Trainer(ModelBase):
    def __init__(self, uri: Optional[str] = None, config_path: Optional[str] = None):
        super().__init__(uri=uri, config_path=config_path)
        self._model_name: str = ""

    def fit(
        self,
        model_type: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        user_col: Optional[str] = None,
        item_col: Optional[str] = None,
        rating_col: Optional[str] = None,
        interactions_query: Optional[str] = None,
        items_query: Optional[str] = None,
        users_query: Optional[str] = None,
        model_name: Optional[str] = None,
        use_weighted: Optional[bool] = False
    ) -> Any:
        params = params or {}
        model_name = model_name or "new_item"
        self._model_name = model_name

        model_type = model_type or self._config.get("models.default", "als")
        default_params = self._config.get(f"models.{model_type}", {})
        params = {**default_params, **params}

        self.load_data(interactions_query, items_query, users_query)
        self.build_matrix(user_col, item_col, rating_col, use_weighted=use_weighted)

        self.model = ModelRegistry.create(model_type, **params)
        self._model_type = model_type

        self.model.fit(self._weighted_matrix if self._weighted_matrix is not None else self._matrix, show_progress=False)

        self.set_mappings(*self.get_mappings())
        self.set_matrix(self._matrix)

        return self.model
