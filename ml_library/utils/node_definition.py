from __future__ import annotations
import functools
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING, get_type_hints
import re
import random
import string
from singleton_decorator import singleton
from .log import *
import pprint


@singleton
class _NodeRegistry:

    def __init__(self):
        self._node_registry = []
        self._function_registry = []
        self._type_registry = []
        

    def _register_node(self, name, meta):
        self._node_registry.append({name: meta})

    def _register_function(self, meta):
        self._function_registry.append(meta)

    def _register_type(self, t):
        # check if type is already registered
        type_map = {t["type"]: t for t in self._type_registry}
        if t["type"] not in type_map:
            t["color"] = f"#{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            self._type_registry.append(t)

    def get_nodes(self):
        return self._node_registry
    
    def get_functions(self):
        return self._function_registry
    
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


def node(*, friendly_name: str | None = None, color: str = "", description: str = "", icon: str = ""):
    def decorator(cls):

        meta = {
            "label": friendly_name or humanize(cls.__name__),
            "icon": icon,
            "color": color,
            "description": description,
            "inputs": [],
            "outputs": [],
            "fields": [],
            "methods": []
        }

        for attr_name, attr in cls.__dict__.items():
            attr = getattr(cls, attr_name)
            if hasattr(attr, "_node_property"):
                print(f"\nNode property: {attr._node_property}\n")
                kind = attr._node_property["kind"]
                data = {
                    "id": attr_name,
                    "label": attr._node_property["label"],
                    "type": serialize_type(attr._node_property["type"]),
                    "color": attr._node_property.get("color", ""),
                }
                if kind == "input":
                    meta["inputs"].append(data)
                elif kind == "output":
                    meta["outputs"].append(data)
                else:
                    meta["fields"].append(data)
                # create a random color for the field
                NodeRegistry._register_type({"type": serialize_type(attr._node_property["type"])})

            if hasattr(attr, "_node_function"):
                # meta["methods"][attr_name] = attr._node_function
                meta["methods"].append({"name": attr_name, "args": attr._node_function["args"], "return": attr._node_function["return"] })

        cls._node_meta = meta
        NodeRegistry._register_node(cls.__name__, meta)
        return cls

    return decorator

def node_property(type_: type, kind: str = "field", label: str | None = None):
    def decorator(func):
        print(f"Registering property {func.__name__} of type {type_} with kind {kind} and label {label} ")
        func._node_property = {
            "id": func.__name__,
            "label": label or humanize(func.__name__),
            "type": type_,
            "kind": kind
        }
        try:
            pprint(func)
        except:
            pass
        return func
    return decorator


def node_function(func):
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    metadata = {
        "id": func.__name__,
        "name": humanize(func.__name__),
        "args": [],
        "return": type_hints.get("return", None)
    }

    for name, param in sig.parameters.items():
        metadata["args"].append({
            "name": name,
            "type": type_hints.get(name, None),
            "default": None if param.default is inspect.Parameter.empty else param.default
        })

    func._node_function = metadata

    # Register standalone functions
    NodeRegistry._register_function(metadata)

    return func
