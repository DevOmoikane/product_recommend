from __future__ import annotations
from typing import Dict, Any, Optional, List, Type, ClassVar
from ..node_definition import node, node_method


@node(
    friendly_name="Config String Node",
    description="A node that retrieves a string value from the configuration.",
    icon="fa fa-cog",
    color="#FF5733",
    begin_node=True
)
class ConfigString:

    @node_method(output_label="value")
    @classmethod
    def get_config(cls, key: str) -> str:
        return ""
    

@node(
    friendly_name="Config Number Node",
    description="A node that retrieves a number value from the configuration.",
    icon="fa fa-cog",
    color="#33C1FF",
    begin_node=True
)
class ConfigNumber:

    @node_method(output_label="value")
    @classmethod
    def get_config(cls, key: str) -> float:
        return 0.0
    

@node(
    friendly_name="Config Boolean Node",
    description="A node that retrieves a boolean value from the configuration.",
    icon="fa fa-cog",
    color="#33C1FF",
    begin_node=True
)
class ConfigBoolean:

    @node_method(output_label="value")
    @classmethod
    def get_config(cls, key: str) -> bool:
        return False

