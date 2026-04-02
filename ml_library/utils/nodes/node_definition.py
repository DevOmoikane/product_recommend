from __future__ import annotations
import functools
import inspect
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, TYPE_CHECKING, get_type_hints
from enum import Enum
import re
import random
import string

from pydantic import color
from singleton_decorator import singleton
from ..log import *
import pprint
import pandas as pd


COMMON_TYPE_COLOR_MAP = {
    int: "#FF5733",
    float: "#33FF57",
    str: "#5733FF",
    bool: "#FF33A1",
    list: "#FFA133",
    dict: "#33A1FF",
    Dict: "#33A1FF",
    Any: "#FFFFFF",
    tuple: "#A1FF33",
    Tuple: "#A1FF33",
    Union: "#A133FF",
    Optional: "#FF33FF",
    Callable: "#33FFA1",
    pd.DataFrame: "#FFA1FF",
    pd.Series: "#A1A1A1",
    type(None): "#FFFFFF",
}

@singleton
class _NodeRegistry:

    def __init__(self):
        self._node_registry = []
        self._type_registry = []

    def _register_node(self, name, meta):
        self._node_registry.append({name: meta})

    def _register_type(self, _type: Any | None = None) -> str:
        # check if type is already registered
        type_map = {t["type"]: t for t in self._type_registry}
        if _type and _type not in type_map:
            _color_int = int(COMMON_TYPE_COLOR_MAP.get(_type, f"#{random.randint(0, 0xFFFFFF):06X}").lstrip("#"), 16)
            new_type = {
                "type": _type,
                "color": f"#{_color_int:06X}"
            }
            self._type_registry.append(new_type)
        _color = next((t["color"] for t in self._type_registry if t["type"] == _type), "#FFFFFF")
        return _color

    def get_nodes(self):
        return self._node_registry
    
    def get_types(self):
        return self._type_registry

NodeRegistry: _NodeRegistry = _NodeRegistry()

def humanize(name: str) -> str:
    words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', name)
    return ' '.join(word.capitalize() for word in words)


def serialize_type(t):
    if t is None:
        return None
    return getattr(t, "__name__", str(t))

class NodeInputMode(Enum):
    REQUIRED = 1
    HIDDEN = 2

def node(friendly_name: str | None = None, color: str = "", description: str = "", icon: str = ""):
    def decorator(cls):
        global NodeRegistry
        meta = {
            "label": friendly_name or humanize(cls.__name__),
            "icon": icon,
            "color": color,
            "description": description,
            "inputs": [],
            "outputs": [],
            "fields": []
        }

        # check if class has INPUT_TYPES method
        if hasattr(cls, "INPUT_TYPES") and callable(getattr(cls, "INPUT_TYPES")):
            input_types = cls.INPUT_TYPES()
            for input_name, input_info in input_types.get("required", {}).items():
                _type_color = NodeRegistry._register_type(input_info.get("type"))
                meta["inputs"].append({
                    "id": input_name,
                    "label": input_info.get("label", humanize(input_name)),
                    "type": serialize_type(input_info.get("type")),
                    "color": _type_color,
                    "description": input_info.get("description", ""),
                    "connection_count": input_info.get("connection_count", 1),
                })

        cls._node_meta = meta
        NodeRegistry._register_node(cls.__name__, meta)
        return cls

    return decorator

