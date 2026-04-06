import importlib
from typing import Any
from ..log import *


# TODO: How to define a workflow as the front end can send this information with the node types and connected outputs and inputs
# we can receive a workflow for: saving it and executing it
# For saving is straight forward
# For executing, it must create instances of the nodes used and how the inputs/outputs are connected (also if the data was entered in the fields)
# * instances of nodes
# * have the references of fields and what output data goes to what input data
# * (plus) send the status of execution (possibly only if it takes a lot of time)
# * must probably, change the node definition to have a class that can be serialized as to send/receive the node definition


# I dont need to re-create a node, just for sending the node definition, is already done down, so this class should be for creating only the object instances
def create_instance_from_string(full_path: str):
    try:
        module_path, _, class_name = full_path.rpartition('.')
        module = importlib.import_module(module_path)
        class_obj = getattr(module, class_name)
        return class_obj
    except (ImportError, AttributeError) as e:
        logerror(f"Error creating instance from string: {e}")
        return None

class GenericInstance:
    def __init__(self, _class: str):
        self._class = _class
        self.inputs = []
        self.outputs = []
        self.fields = []
        # find the class with the name _class provided and instantiate
        self._instance = create_instance_from_string(self._class)

    def execute(self, method: str, *args, **kwargs) -> Any:
        if hasattr(self._instance, method):
            method_instance = getattr(self._instance, method)
            if callable(method_instance):
                result = method_instance(*args, **kwargs)
                return result
        else:
            logerror(f"Method {method} not found in class {self._class}")
            return None


