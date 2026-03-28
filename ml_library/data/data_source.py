from typing import Any, Optional, Dict
from urllib.parse import urlsplit, urlparse
from .adapter.abstract_data_connector import AbstractDataConnector
from .adapter import create_connector
from ..utils.log import *
from ..utils.config import load_config
from ..utils.node_definition import node, node_property, node_function


class DataSource:
    def __init__(self, uri: Optional[str] = None, config_path: Optional[str] = None):
        self._uri = uri
        self._config: Dict[str, Any] = {}
        self._connector: Optional[AbstractDataConnector] = None
        self._config_path = config_path or "config.yaml"

    def _create_data_connector(self) -> AbstractDataConnector:
        self._parse_uri()
        
        scheme = self._config.get("scheme", "")
        
        if scheme in ("postgresql", "postgres"):
            connector_config = {
                "uri": self._uri,
                "queries": self._get_queries()
            }
            return create_connector("postgresql", connector_config)
        elif scheme == "csv":
            cfg = load_config(self._config_path)
            return create_connector("csv", {
                "interactions_path": cfg.get("csv.interactions_path"),
                "items_path": cfg.get("csv.items_path"),
                "users_path": cfg.get("csv.users_path"),
            })
        else:
            raiselog(ValueError(f"Unsupported URI scheme: {scheme}"))

    def _parse_uri(self):
        if self._uri is None:
            cfg = load_config(self._config_path)
            uri = cfg.get("database.uri")
            if not uri:
                raiselog(ValueError("No URI provided and no default in config"))
            self._uri = uri
        
        parsed_uri = urlparse(self._uri)
        user = parsed_uri.username
        password = parsed_uri.password
        host = parsed_uri.hostname
        port = parsed_uri.port
        self._config = {
            "scheme": parsed_uri.scheme,
            "netloc": parsed_uri.netloc,
            "username": user,
            "password": password,
            "host": host,
            "port": port,
            "path": parsed_uri.path,
            "params": parsed_uri.params,
            "query": parsed_uri.query,
            "fragment": parsed_uri.fragment,
        }

    def _get_queries(self) -> Dict[str, str]:
        cfg = load_config(self._config_path)
        return {
            "interactions": cfg.get("queries.interactions", ""),
            "items": cfg.get("queries.items", ""),
            "users": cfg.get("queries.users", ""),
        }

    def get_connector(self) -> AbstractDataConnector:
        if self._connector is None:
            self._connector = self._create_data_connector()
        return self._connector
