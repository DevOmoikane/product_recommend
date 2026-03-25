import joblib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

import implicit
from implicit.als import AlternatingLeastSquares
from implicit.bpr import BayesianPersonalizedRanking
from implicit.lmf import LogisticMatrixFactorization
from implicit.nearest_neighbours import (
    BM25Recommender,
    CosineRecommender,
    TFIDFRecommender,
    ItemItemRecommender,
    bm25_weight,
)
from implicit.recommender_base import RecommenderBase

from sklearn.linear_model import (
    LogisticRegression,
    LinearRegression,
)
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    AdaBoostRegressor,
    ExtraTreesRegressor,
    BaggingRegressor,
    StackingRegressor,
    VotingRegressor,
    ExtraTreesRegressor,
    BaggingRegressor,
)
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

from scipy.sparse import csr_matrix, coo_matrix
import pandas as pd
import numpy as np
from ml_library.data.data_source import DataSource
from ml_library.utils.log import *


if TYPE_CHECKING:
    from app.model_base import ModelBase


class ModelRegistry:
    _models: Dict[str, type] = {
        "als": AlternatingLeastSquares,
        "bpr": BayesianPersonalizedRanking,
        "lmf": LogisticMatrixFactorization,
        "cosine": CosineRecommender,
        "tfidf": TFIDFRecommender,
        "bm25": BM25Recommender,
        #"iir": ItemItemRecommender, # it expects a double for the buffer
    }

    @classmethod
    def create(cls, model_type: str, **kwargs) -> Any:
        if model_type not in cls._models:
            raiselog(ValueError(f"Unknown model type: {model_type}. Available: {list(cls._models.keys())}"))
        return cls._models[model_type](**kwargs)

    @classmethod
    def register(cls, name: str, model_class: type):
        cls._models[name] = model_class

    @classmethod
    def list_models(cls) -> list:
        return list(cls._models.keys())

global_model: RecommenderBase = None

class ModelBase:
    def __init__(self, uri: Optional[str] = None, config_path: Optional[str] = None):
        self._uri = uri
        self._config_path = config_path or "config.yaml"
        self._data_source = DataSource(uri, config_path)
        self._config = self._load_config(self._config_path)
        self._interactions_df: Optional[pd.DataFrame] = None
        self._items_df: Optional[pd.DataFrame] = None
        self._users_df: Optional[pd.DataFrame] = None
        self._user_mapping: Dict[int, int] = {}
        self._item_mapping: Dict[int, int] = {}
        self._reverse_user_mapping: Dict[int, int] = {}
        self._reverse_item_mapping: Dict[int, int] = {}
        self._matrix: Optional[csr_matrix] = None
        self._weighted_matrix: Optional[csr_matrix] = None
        self._model_type: str = "newitem"
        self._user_cols: Optional[str] = None
        self._item_cols: Optional[str] = None
        self._rating_cols: Optional[str] = None

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not Path(path).exists():
            raiselog(FileNotFoundError(f"Config file not found: {path}"))
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _save_model(self, model_path: str, **kwargs):
        if global_model is None:
            raiselog(ValueError("No model to save"))
        
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._user_cols = kwargs.get("user_columns", self._config.get("column_mapping.user_id", "client_id"))
        self._item_cols = kwargs.get("item_columns", self._config.get("column_mapping.item_id", "product_id"))
        self._rating_cols = kwargs.get("rating_columns", self._config.get("column_mapping.rating", "quantity"))
        user_items = global_model.user_items if hasattr(global_model, "user_items") and global_model.user_items is not None else self._weighted_matrix
        joblib.dump({
            "model": global_model,
            "model_type": self._model_type,
            "user_columns": self._user_cols,
            "item_columns": self._item_cols,
            "rating_columns": self._rating_cols,
            "user_mapping": self._user_mapping,
            "item_mapping": self._item_mapping,
            "reverse_user_mapping": self._reverse_user_mapping,
            "reverse_item_mapping": self._reverse_item_mapping,
        }, model_path)

    def save_model(self, model_path: Optional[str] = None, **kwargs):
        if model_path is None:
            model_path = self._config.get("persistence.default_model", "./models/model.pkl")
        self._save_model(model_path, **kwargs)
        return model_path

    def _load_model(self, model_path: str):
        if not Path(model_path).exists():
            raiselog(FileNotFoundError(f"Model file not found: {model_path}"))
        
        loginfo(f"Loading model from {model_path}...")
        data = joblib.load(model_path)
        # force the data["model"] to be of type RecommenderBase
        if not isinstance(data["model"], RecommenderBase):
            raiselog(ValueError(f"Loaded model is not of type RecommenderBase: {type(data['model'])}"))
        global global_model
        global_model = data["model"]
        self._model_type = data.get("model_type", "")
        self._user_cols = data.get("user_columns", self._config.get("column_mapping.user_id", "client_id"))
        self._item_cols = data.get("item_columns", self._config.get("column_mapping.item_id", "product_id"))
        self._rating_cols = data.get("rating_columns", self._config.get("column_mapping.rating", "quantity"))
        self._user_mapping = data.get("user_mapping", {})
        self._item_mapping = data.get("item_mapping", {})
        self._reverse_user_mapping = data.get("reverse_user_mapping", {})
        self._reverse_item_mapping = data.get("reverse_item_mapping", {})
        # logobject(data, "Loaded model data")
        return global_model

    def load_model(self, model_path: Optional[str] = None):
        if model_path is None:
            model_path = self._config.get("persistence.default_model", "./models/model.pkl")
        return self._load_model(model_path)

    def set_mappings(
        self,
        user_mapping: Dict[int, int],
        item_mapping: Dict[int, int],
        reverse_user_mapping: Dict[int, int],
        reverse_item_mapping: Dict[int, int]
    ):
        self._user_mapping = user_mapping
        self._item_mapping = item_mapping
        self._reverse_user_mapping = reverse_user_mapping
        self._reverse_item_mapping = reverse_item_mapping

    def set_matrix(self, matrix: csr_matrix):
        self._matrix = matrix

    def set_model(self, model: Any):
        global_model = model

    def load_interactions(self, query: Optional[str] = None) -> pd.DataFrame:
        connector = self._data_source.get_connector()
        self._interactions_df = connector.get_interactions(query)
        return self._interactions_df

    def load_items(self, query: Optional[str] = None) -> pd.DataFrame:
        connector = self._data_source.get_connector()
        self._items_df = connector.get_items(query)
        return self._items_df

    def load_users(self, query: Optional[str] = None) -> pd.DataFrame:
        connector = self._data_source.get_connector()
        self._users_df = connector.get_users(query)
        return self._users_df

    def load_data(
        self,
        interactions_query: Optional[str] = None,
        items_query: Optional[str] = None,
        users_query: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        self.load_interactions(interactions_query)
        self.load_items(items_query)
        self.load_users(users_query)
        return {
            "interactions": self._interactions_df,
            "items": self._items_df,
            "users": self._users_df,
        }

    def get_mappings(self) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, int]]:
        return self._user_mapping, self._item_mapping, self._reverse_user_mapping, self._reverse_item_mapping

    @property
    def matrix(self) -> Optional[csr_matrix]:
        return self._matrix
    
    @property
    def model(self) -> RecommenderBase:
        global global_model
        return global_model
    
    @model.setter
    def model(self, value: RecommenderBase):
        global global_model
        global_model = value

    def build_matrix(
        self,
        user_col: Optional[str] = None,
        item_col: Optional[str] = None,
        rating_col: Optional[str] = None,
        use_weighted: bool = False
    ) -> csr_matrix:
        user_col = user_col or self._config.get("column_mapping.user_id", "client_id")
        item_col = item_col or self._config.get("column_mapping.item_id", "product_id")
        rating_col = rating_col or self._config.get("column_mapping.rating", "quantity")

        if self._interactions_df is None:
            raiselog(ValueError("No interactions loaded. Call load_interactions() first."))

        df = self._interactions_df.copy()
        df.dropna(axis=0, how="any", inplace=True)

        user_cat = df[user_col].astype("category")
        item_cat = df[item_col].astype("category")
        df["user_idx"] = user_cat.cat.codes.astype(np.int32)
        df["item_idx"] = item_cat.cat.codes.astype(np.int32)

        rows = df["user_idx"].to_numpy()
        cols = df["item_idx"].to_numpy()
        data = df[rating_col].astype(np.float32).to_numpy()

        self._matrix = coo_matrix(
            (data, (rows, cols)),
            # shape=(len(rows), len(cols))
        ).tocsr()
        if use_weighted:
            self._weighted_matrix = bm25_weight(self._matrix, K1=self._config.get("models.weighted.k1", 100), B=self._config.get("models.weighted.b", 0.8)).tocsr()

        self._user_mapping = dict(enumerate(user_cat.cat.categories))
        self._item_mapping = dict(enumerate(item_cat.cat.categories))
        self._reverse_user_mapping = {v: k for k, v in self._user_mapping.items()}
        self._reverse_item_mapping = {v: k for k, v in self._item_mapping.items()}

        return self._weighted_matrix if self._weighted_matrix is not None else self._matrix