from __future__ import annotations
import functools
import inspect
import importlib
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, TYPE_CHECKING, get_type_hints, get_origin, get_args
from enum import Enum
import re
import random
import string
from types import UnionType

from pydantic import color
from singleton_decorator import singleton
from ..log import *
from pprint import pprint
import pandas as pd


COMMON_TYPE_COLOR_MAP = {
    int: "#FF5733",
    float: "#33FF57",
    str: "#5733FF",
    bool: "#FF33A1",
    list: "#FFA133",
    List: "#FFA133",
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

def type_to_fieldtype(t) -> str:
    if t in (int, float, str, bool, list, dict, tuple):
        return "textarea"
    return None

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
        return []
    
    origin = get_origin(t)
    if origin is Union or origin is UnionType:
        args = get_args(t)
        return [getattr(arg, "__name__", str(arg)) for arg in args if arg is not type(None)]
    
    return [getattr(t, "__name__", str(t))]

class NodeInputMode(Enum):
    REQUIRED = 1
    HIDDEN = 2

def node(friendly_name: str | None = None, color: str = "", description: str = "", icon: str = "", function: str = ""):
    def decorator(cls):
        global NodeRegistry
        meta = {
            "label": friendly_name or humanize(cls.__name__),
            "full_class_path": f"{cls.__module__}.{cls.__name__}",
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

        _function_call = None
        _return_type = None
        _id = None
        _label = None
        _description = None
        _args = None
        if hasattr(cls, "FUNCTION") and hasattr(cls, "RETURN_TYPE"):
            _function_call = cls.FUNCTION
            _return_type = cls.RETURN_TYPE
        elif function!="" and hasattr(cls, function) and callable(getattr(cls, function)):
            _function_call = function
            _return_type = get_type_hints(getattr(cls, function)).get("return", None)
        for attr_name, attr in cls.__dict__.items():
            if hasattr(attr, "_node_method"):
                _id = attr_name
                _function_call = attr._node_method["id"]
                _return_type = attr._node_method["return"]
                _label = attr._node_method["friendly_name"]
                _description = attr._node_method["description"]
                _args = attr._node_method["args"]
        if _function_call is not None and _return_type is not None:
            _type_color = NodeRegistry._register_type(_return_type)
            meta["outputs"].append({
                "id": _id or _function_call,
                "label": _label or humanize(_function_call),
                "type": serialize_type(_return_type),
                "color": _type_color,
                "description": _description or "",
            })
            if _args is not None and len(_args)>0:
                for arg in _args:
                    _arg_color = NodeRegistry._register_type(arg["type"])
                    meta["inputs"].append({
                        "id": arg["id"],
                        "label": arg["label"],
                        "type": serialize_type(arg["type"]),
                        "color": _arg_color,
                        "description": "",
                        "connection_count": 1,
                    })
                    field_type = type_to_fieldtype(arg["type"])
                    if field_type:
                        meta["fields"].append({
                            "name": arg["id"],
                            "label": arg["label"],
                            "type": field_type,
                            "options": [],
                        })

        cls._node_meta = meta
        NodeRegistry._register_node(cls.__name__, meta)
        return cls

    return decorator


def node_method(func=None, output_label: str = "", description: str = ""):
    def decorator(f):
        actual_func = f
        if hasattr(f, '__func__'):
            actual_func = f.__func__
        
        sig = inspect.signature(actual_func)
        type_hints = get_type_hints(actual_func)
        args = []
        if sig.parameters:
            for param in sig.parameters.values():
                if param.name in ('self', 'cls'):
                    continue
                argument = {
                    "id": param.name,
                    "label": humanize(param.name),
                    "type": type_hints.get(param.name, None) or param.annotation if param.annotation != inspect.Parameter.empty else None,
                    "default": None if param.default is inspect.Parameter.empty else param.default
                }
                args.append(argument)
        f._node_method = {
            "id": actual_func.__name__,
            "return": type_hints.get("return", None),
            "friendly_name": output_label,
            "description": description,
            "args": args,
        }
        return f
    
    if func is None:
        return decorator
    return decorator(func)

