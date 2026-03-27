from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import yaml


class Config:
    _instance: Optional["Config"] = None
    _config: Dict[str, Any] = {}

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, config_path: str):
        cls = self.__class__
        path = Path(config_path)
        if path.exists():
            with open(path, "r") as f:
                cls._config.update(yaml.safe_load(f) or {})
        return self

    def get(self, key: str, default: Any = None) -> Any:
        cls = self.__class__
        keys = key.split(".")
        value = cls._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    @property
    def config(self) -> Dict[str, Any]:
        global _config
        return _config
    
    
def load_config(config_path: str = "config.yaml") -> Config:
    return Config().load(config_path)
