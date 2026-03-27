from typing import Dict, Any, Optional
from .abstract_data_connector import AbstractDataConnector
from .postgresql_connector import PostgreSQLConnector
from .csv_connector import CSVConnector


def create_connector(
    source_type: str,
    config: Optional[Dict[str, Any]] = None
) -> AbstractDataConnector:
    config = config or {}
    
    if source_type == "postgresql":
        return PostgreSQLConnector(
            uri=config.get("uri", ""),
            queries=config.get("queries", {})
        )
    elif source_type == "csv":
        return CSVConnector(
            interactions_path=config.get("interactions_path"),
            items_path=config.get("items_path"),
            users_path=config.get("users_path"),
            encoding=config.get("encoding", "utf-8")
        )
    else:
        raise ValueError(f"Unknown connector type: {source_type}")


__all__ = [
    "AbstractDataConnector",
    "PostgreSQLConnector",
    "CSVConnector",
    "create_connector",
]
