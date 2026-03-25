from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
import pandas as pd


class AbstractDataConnector(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def connect(self) -> Any:
        pass

    @abstractmethod
    def get_interactions(self, query: Optional[str] = None) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_items(self, query: Optional[str] = None) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_users(self, query: Optional[str] = None) -> pd.DataFrame:
        pass
