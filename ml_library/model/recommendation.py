from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Type
from scipy.sparse import csr_matrix, coo_matrix
import pandas as pd
import numpy as np
from .base_model import BaseModel, BaseRegistry


class ModelRecommendationRegistry(BaseRegistry):
    _registry: Dict[str, Type[ModelRecommendation]] = {}

    @classmethod
    def register(cls, model_type: str, friendly_name: Optional[str] = None):
        def decorator(model_class: Type[ModelRecommendation]):
            cls._registry[model_type] = model_class
            model_class._friendly_name = friendly_name or model_class.__name__
            return model_class
        return decorator


class ModelRecommendation(BaseModel):
    _friendly_name: str = "Recommendation Model"

    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def fit(self, **kwargs) -> Any:
        pass

    @abstractmethod
    def predict(self, **kwargs) -> Any:
        pass

    def get_model_class(self, class_name: str) -> Any:
        return next((cls for cls in ModelRecommendationRegistry._registry.values() if cls.__name__ == class_name), None)

    def _model_persistence_features(self):
        return {}
