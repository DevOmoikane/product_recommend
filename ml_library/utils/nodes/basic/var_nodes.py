from __future__ import annotations
from typing import Dict, Any, Optional, List, Type, ClassVar
from ..node_definition import node, node_method

@node(
    friendly_name="String Node",
    description="A node that holds a string value.",
    category="Basic",
    icon="fa fa-font",
    color="#FF5733",
    begin_node=True
)
class StringNode:

    @node_method(output_label="value")
    @classmethod
    def get_value(cls, value: str) -> str:
        return value


@node(
    friendly_name="Integer Node",
    description="A node that holds an integer value.",
    category="Basic",
    icon="fa fa-hashtag",
    color="#33C1FF",
    begin_node=True
)
class IntegerNode:
    @node_method(output_label="value")
    @classmethod
    def get_value(cls, value: int) -> int:
        return value
    

@node(
    friendly_name="Pair Node",
    description="A node that holds a key-value pair.",
    category="Basic",
    icon="fa fa-key",
    color="#FF33A1",
    begin_node=True
)
class PairNode:
    @node_method(output_label="pair")
    @classmethod
    def get_value(cls, key: str, value: str) -> Dict[str, str]:
        return {key: value}
