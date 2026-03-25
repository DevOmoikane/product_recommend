import pandas as pd
from typing import Optional, Dict
from .abstract_data_connector import AbstractDataConnector
from ...utils.log import *


class CSVConnector(AbstractDataConnector):
    def __init__(
        self,
        interactions_path: Optional[str] = None,
        items_path: Optional[str] = None,
        users_path: Optional[str] = None,
        encoding: str = "utf-8"
    ):
        self._interactions_path = interactions_path
        self._items_path = items_path
        self._users_path = users_path
        self._encoding = encoding

    def connect(self):
        pass

    def get_interactions(self, query: Optional[str] = None) -> pd.DataFrame:
        p = query or self._interactions_path
        if not p:
            raiselog(ValueError("No interactions path provided"))
        return pd.read_csv(p, encoding=self._encoding)

    def get_items(self, query: Optional[str] = None) -> pd.DataFrame:
        p = query or self._items_path
        if not p:
            raiselog(ValueError("No items path provided"))
        return pd.read_csv(p, encoding=self._encoding)

    def get_users(self, query: Optional[str] = None) -> pd.DataFrame:
        p = query or self._users_path
        if not p:
            raiselog(ValueError("No users path provided"))
        return pd.read_csv(p, encoding=self._encoding)
