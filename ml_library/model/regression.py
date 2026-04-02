from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Type, ClassVar
from scipy.sparse import csr_matrix, coo_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, LabelEncoder, StandardScaler, MinMaxScaler, RobustScaler
import pandas as pd
import numpy as np
from .base_model import BaseModel, BaseRegistry


class ModelRegressionRegistry(BaseRegistry):
    _registry: Dict[str, Type[ModelRegression]] = {}

    @classmethod
    def register(cls, model_type: str, friendly_name: Optional[str] = None):
        def decorator(model_class: Type[ModelRegression]):
            cls._registry[model_type] = model_class
            model_class._friendly_name = friendly_name or model_class.__name__
            return model_class
        return decorator
    

class ModelRegression(BaseModel):
    _friendly_name: str = "Regression Model"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": {"type": pd.DataFrame, "description": "Input data for training the model"},
                "data_columns": {"type": List[str], "description": "List of columns to be used as features"},
                "value_columns": {"type": List[str], "description": "List of columns to be used as target values"},
                "drop_columns": {"type": List[str], "default": None, "description": "List of columns to be dropped from the data"},
                "scale_columns": {"type": List[str], "default": None, "description": "List of columns to be scaled"},
                "ohe_columns": {"type": List[str], "default": None, "description": "List of columns to be one-hot encoded"},
                "le_columns": {"type": List[str], "default": None, "description": "List of columns to be label encoded"},
            }
        }
    
    @classmethod
    def OUT(cls):
        return {
            "type": Any,
            "label": "",
            "function": "predict",
        }

    def __init__(self, **kwargs):
        super().__init__()
        self._matrix: Optional[csr_matrix] = None
        self._weighted_matrix: Optional[csr_matrix] = None

        self._config: Optional[Dict[str, Any]] = kwargs.get("config", None)

        self._data_columns: Optional[List[str]] = None
        self._value_columns: Optional[List[str]] = None
        self._drop_columns: Optional[List[str]] = None
        self._scale_columns: Optional[List[str]] = None
        self._ohe_columns: Optional[List[str]] = None
        self._le_columns: Optional[List[str]] = None

        self._original_data: Optional[pd.DataFrame] = None
        self._work_data: Optional[pd.DataFrame] = None

        if kwargs:
            if "data_columns" in kwargs:
                self._data_columns = kwargs["data_columns"]
            if "value_columns" in kwargs:
                self._value_columns = kwargs["value_columns"]
            if "drop_columns" in kwargs:
                self._drop_columns = kwargs["drop_columns"]
            if "scale_columns" in kwargs:
                self._scale_columns = kwargs["scale_columns"]
            if "ohe_columns" in kwargs:
                self._ohe_columns = kwargs["ohe_columns"]
            if "le_columns" in kwargs:
                self._le_columns = kwargs["le_columns"]

    def get_model_class(self, class_name: str) -> Any:
        return next((cls for cls in ModelRegressionRegistry._registry.values() if cls.__name__ == class_name), None)

    def _model_persistence_features(self) -> Dict[str, str]:
        return {
            "config": "_config",
            "data_columns": "_data_columns",
            "value_columns": "_value_columns",
            "drop_columns": "_drop_columns",
            "scale_columns": "_scale_columns",
            "ohe_columns": "_ohe_columns",
            "le_columns": "_le_columns"
        }

    def _fit(self, X_train: Any, y_train: Any, **kwargs) -> None:
        self._model.fit(X_train, y_train, **kwargs)

    def _check_and_create_ohe_columns(self) -> None:
        if "use_ohe_columns" not in self._config or not self._config["use_ohe_columns"]:
            return
        
        # convert ohe columns
        # check if we have ohe columns
        if self._ohe_columns is None:
            self._ohe_columns = []
            # check columns for non numeric values and consider them as ohe columns
            for column in self._work_data.columns:
                if not pd.api.types.is_numeric_dtype(self._work_data[column]):
                    self._ohe_columns.append(column)

        ohe = OneHotEncoder()
        ohe.fit(self._work_data[self._ohe_columns])

        if ohe.categories_:
            merge_ohe_columns = np.concatenate(ohe.categories_)
            ohe_data = ohe.transform(self._work_data[self._ohe_columns])
            ohe_df = pd.DataFrame.sparse.from_spmatrix(ohe_data.toarray(), columns=merge_ohe_columns)
            self._work_data = pd.concat([self._work_data.drop(self._ohe_columns, axis=1), ohe_df], axis=1)

    def _process_scaler(self) -> None:
        if "use_scaler" not in self._config or not self._config["use_scaler"]:
            return
        
        scaler_type = self._config.get("scaler", None)
        scaler: Any = None
        if scaler_type is None:
            return
        if scaler_type == "minmax":
            scaler = MinMaxScaler()
        elif scaler_type == "standard":
            scaler = StandardScaler()
        elif scaler_type == "robust":
            scaler = RobustScaler()
        self._work_data.loc[:, self._scale_columns] = scaler.fit_transform(self._work_data.loc[:, self._scale_columns])

    def train(self, data: Any, **kwargs) -> None:
        #TODO: change to correct behavior
        # from the data convert the not numbers to catalogs and remove them from the 
        self._original_data = data.copy()
        self._work_data = data.copy()

        self._check_and_create_ohe_columns()

        self._process_scaler()

        # check for the number of unique items in every column and if it is less than 10, consider it as a catalog and remove it from the data
        for column in self._work_data[self._data_columns].columns:
            if self._work_data[column].nunique() < 10:
                pass
        
        X = self._work_data.drop(self._value_columns, axis=1)
        y = self._work_data[self._value_columns]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=12)

        X_train.reset_index(inplace = True)
        X_test.reset_index(inplace = True)
        
        self._fit(X_train, y_train, **kwargs)

    @abstractmethod
    def predict(self, X: Any) -> Any:
        pass
