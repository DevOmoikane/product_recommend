from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, ClassVar
import joblib
from pathlib import Path
from ..utils.log import *
from ..utils.nodes.node_definition import node, node_method


class BaseRegistry(ABC):
    _registry: Dict[str, Any] = {}

    @abstractmethod
    def register(cls, model_type: str, friendly_name: Optional[str] = None):
        pass

    @classmethod
    def create(cls, model_type: str, **kwargs) -> Any:
        if model_type not in cls._registry:
            raise ValueError(f"Model type '{model_type}' is not registered.")
        return cls._registry[model_type](**kwargs)

    @classmethod
    def available(cls) -> List[Dict[str, str]]:
        return [{"type": model_type, "friendly_name": model_class._friendly_name} for model_type, model_class in cls._registry.items()]


class BaseModel(ABC):

    def __init__(self):
        self._model: Any = None

    def _set_model(self, model: Any) -> None:
        self._model = model

    @property
    def friendly_name(self) -> str:
        if hasattr(self.__class__, "_friendly_name"):
            return self.__class__._friendly_name
        return self.__class__.__name__

    def save_model(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.__class__.log_instance_info(self)
        variables = self._model_persistence_features()

        data = {
            "class": self.__class__.__name__,
            "model": self._model,
        }

        for persistence_key, persistence_variable in variables.items():
            value = getattr(self, persistence_variable, None)
            if value is not None:
                loginfo(f"Adding persistence variable '{persistence_variable}' with value: {value} to model persistence data under key '{persistence_key}'")
                data[persistence_key] = value

        joblib.dump(data, path)

    def _model_persistence_features(self) -> Dict[str, Any]:
        return {}

    @abstractmethod
    def get_model_class(self, class_name: str) -> Any:
        pass

    @classmethod
    def load_model(cls, path: str) -> BaseModel:
        if not Path(path).exists():
            raise ValueError(f"Model file '{path}' does not exist.")
        loaded_model = joblib.load(path)
        if loaded_model is None or type(loaded_model) is not dict:
            raise ValueError(f"Loaded model from '{path}' is not a valid dictionary.")
        model_class_name = loaded_model.get("class")
        model_class = cls.get_model_class(cls, model_class_name)
        logobject(model_class, f"Type of model class for '{model_class_name}' is {type(model_class)}")
        if model_class is None:
            raise ValueError(f"Model class '{model_class_name}' is not registered.")
        model_instance = model_class()
        logobject(model_instance, f"Created model instance of type {type(model_instance)}")
        model_instance._set_model(loaded_model.get("model"))
        loaded_model.pop("class", None)
        loaded_model.pop("model", None)
        _persistence_features = model_instance._model_persistence_features()
        for persistence_key, persistence_variable in _persistence_features.items():
            if persistence_key in loaded_model:
                value = loaded_model[persistence_key]
                setattr(model_instance, persistence_variable, value)
                loginfo(f"Set persistence variable '{persistence_variable}' to value: {value} from loaded model data key '{persistence_key}'")
            else:
                logwarning(f"Persistence key '{persistence_key}' not found in loaded model data. Variable '{persistence_variable}' will not be set.")

        cls.log_instance_info(model_instance)

        # when returning the model, also return the remaining variables loaded from the persistence file
        return model_instance, loaded_model

    @classmethod
    def log_instance_info(cls, instance: BaseModel):
        logdebug(f"Instance of type {type(instance)} with friendly name '{instance.__class__._friendly_name}'")
        for cls in instance.__class__.mro():
            for var_name, var_value in cls.__dict__.items():
                logdebug(f"{cls.__name__} - {var_name}: {var_value}")


@node(
    friendly_name="Model Saver",
    description="Save a generated model to disk.",
    icon="fa fa-tree",
    color="#DDE00F"
)
class ModelSaver:
    @node_method
    @staticmethod
    def save(model: BaseModel, path: str) -> BaseModel:
        model.save_model(path)
        return model
    
@node(
    friendly_name="Model Loader",
    description="Load a model from disk.",
    icon="fa fa-tree",
    color="#DDE00F"
)
class ModelLoader:
    @node_method
    @classmethod
    def load(cls, path: str) -> BaseModel | None:
        try:
            return cls.load_model(path)
        except Exception as e:
            return None

