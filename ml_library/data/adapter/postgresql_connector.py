import pandas as pd
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import NullPool
from typing import Optional, Dict, Any
from .abstract_data_connector import AbstractDataConnector
from ...utils.log import *


class PostgreSQLConnector(AbstractDataConnector):
    def __init__(self, uri: str, queries: Optional[Dict[str, str]] = None):
        self._uri = uri
        self._engine: Optional[Engine] = None
        self._queries = queries or {}

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

    def get_user(self, user_id: int) -> pd.DataFrame:
        query = """
            SELECT id, name, description, image_url, created_at, updated_at
            FROM clients
            WHERE id = :user_id
        """
        return self.execute_query(query, {"user_id": user_id})

    def get_user_interactions(self, user_id: int) -> pd.DataFrame:
        query = """
            SELECT 
                delivery_orders.id as order_id,
                delivery_orders.created_at as order_date,
                delivery_order_items.product_id,
                products.name as product_name,
                products.sku,
                delivery_order_items.quantity,
                delivery_order_items.unit_price,
                (delivery_order_items.quantity * delivery_order_items.unit_price) as total
            FROM delivery_orders
            JOIN delivery_order_items ON delivery_orders.id = delivery_order_items.delivery_order_id
            JOIN products ON delivery_order_items.product_id = products.id
            WHERE delivery_orders.client_id = :user_id
            ORDER BY delivery_orders.created_at DESC
            LIMIT 100
        """
        return self.execute_query(query, {"user_id": user_id})

    def get_user_orders(self, user_id: int) -> pd.DataFrame:
        query = """
            SELECT 
                delivery_orders.id as order_id,
                delivery_orders.created_at as order_date,
                delivery_orders.proof_document,
                COUNT(delivery_order_items.id) as item_count,
                SUM(delivery_order_items.quantity * delivery_order_items.unit_price) as total_amount
            FROM delivery_orders
            LEFT JOIN delivery_order_items ON delivery_orders.id = delivery_order_items.delivery_order_id
            WHERE delivery_orders.client_id = :user_id
            GROUP BY delivery_orders.id, delivery_orders.created_at, delivery_orders.proof_document
            ORDER BY delivery_orders.created_at DESC
            LIMIT 50
        """
        return self.execute_query(query, {"user_id": user_id})
