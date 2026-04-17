from __future__ import annotations
from typing import Dict, Any, Optional, List, Type, ClassVar, Callable
from ..node_definition import node, node_method
from ....utils.log import *


@node(
    friendly_name="Debug Node",
    description="Prints the object to the log with an optional message",
    category="Basic",
    icon="fa fa-bug",
    color="#007bff",
    end_node=True
)
class DebugNode:
    @node_method(output_label="debug")
    @classmethod
    def print_object(cls, obj: Any, msg: str | None = None, _broadcast: Callable[[str, Any], None] | None = None) -> None:
        logobject(obj, msg)
        if _broadcast is not None:
            _broadcast(msg, obj)
