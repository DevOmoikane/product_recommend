import pandas as pd
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import NullPool
from typing import Optional, Dict, Any
from .abstract_data_connector import AbstractDataConnector
from ...utils.log import *
from ...utils.nodes.node_definition import node, node_method


@node(
    friendly_name="PostgreSQL Connector",
    description="Connects to a PostgreSQL database and retrieves data using provided queries.",
    category="Data Connectors",
    icon="fa fa-database",
    color="#336791"
)
class PostgreSQLConnector(AbstractDataConnector):
    def __init__(self, uri: str, queries: Optional[Dict[str, str]] = None):
        self._uri = uri
        self._engine: Optional[Engine] = None
        self._queries = queries or {}

    @node_method(output_label="data")
    @classmethod
    def get_data(cls, uri: str, queries: Optional[Dict[str, str]] = None) -> Dict[str, pd.DataFrame]:
        logobject(queries, "get_data => queries = ")
        if queries is not None and isinstance(queries, dict):
            for key, value in (queries or {}).items():
                loginfo(f"Query for {key}: {value}")
        loginfo(f"queries = {queries}")
        connector = cls(uri, queries)
        data = {
            "interactions": connector.get_interactions(),
            "items": connector.get_items(),
            "users": connector.get_users()
        }
        connector.disconnect()
        data = {}
        return data

    def connect(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self._uri,
                poolclass=NullPool,
                echo=False
            )
        return self._engine

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        engine = self.connect()
        with engine.connect() as conn:
            result = conn.execute(
                __import__("sqlalchemy").text(query),
                params or {}
            )
            columns = list(result.keys())
            data = result.fetchall()
            return pd.DataFrame(data, columns=columns)

    def get_interactions(self, query: Optional[str] = None) -> pd.DataFrame:
        q = query or self._queries.get("interactions", "")
        if not q:
            raiselog(ValueError("No interactions query provided"))
        return self.execute_query(q)

    def get_items(self, query: Optional[str] = None) -> pd.DataFrame:
        q = query or self._queries.get("items", "")
        if not q:
            raiselog(ValueError("No items query provided"))
        return self.execute_query(q)

    def get_users(self, query: Optional[str] = None) -> pd.DataFrame:
        q = query or self._queries.get("users", "")
        if not q:
            raiselog(ValueError("No users query provided"))
        return self.execute_query(q)

    def disconnect(self):
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
