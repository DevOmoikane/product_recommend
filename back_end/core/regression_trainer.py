import numpy as np
import pandas as pd
import pickle
import os
from typing import Any, Optional, Dict, List, Tuple
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from ml_library.utils.config import load_config
from ml_library.data.data_source import DataSource
from ml_library.utils.log import *


class RegressionTrainer:
    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or "config.yaml"
        self._config = load_config(self._config_path)
        self._data_source = DataSource(config_path=self._config_path)
        
        self.model: Optional[GradientBoostingRegressor] = None
        self.user_encoder: Optional[LabelEncoder] = None
        self.item_encoder: Optional[LabelEncoder] = None
        self.scaler: Optional[StandardScaler] = None
        
        self._user_features: Dict[int, np.ndarray] = {}
        self._item_features: Dict[int, np.ndarray] = {}
        self._user_item_matrix: pd.DataFrame = None
        self._all_items: pd.DataFrame = None

        self._user_id_key = self._config.get("column_mapping.user_id", "client_id")
        self._item_id_key = self._config.get("column_mapping.item_id", "product_id")
        self._rating_key = self._config.get("column_mapping.rating", "quantity")

    def fit(
        self,
        use_weighted: Optional[bool] = False,
        model_type: Optional[str] = "gbr",
        **kwargs
    ) -> Any:
        loginfo("Starting regression model training for repurchase recommendations")
        
        connector = self._data_source.get_connector()
        interactions = connector.get_interactions()
        items = connector.get_items()
        users = connector.get_users()
        
        loginfo(f"Loaded interactions: {len(interactions)} rows")
        loginfo(f"Loaded items: {len(items)} rows")
        loginfo(f"Loaded users: {len(users)} rows")
        
        # interactions = interactions.dropna(subset=['client_id', 'product_id', 'quantity'])
        interactions.dropna(inplace=True, axis=0)
        interactions[self._user_id_key] = interactions[self._user_id_key].astype(int)
        interactions[self._item_id_key] = interactions[self._item_id_key].astype(int)
        interactions[self._rating_key] = interactions[self._rating_key].astype(float)
        
        if 'unit_price' in interactions.columns:
            interactions['unit_price'] = interactions['unit_price'].fillna(0).astype(float)
        if 'minimal_price' in interactions.columns:
            interactions['minimal_price'] = interactions['minimal_price'].fillna(0).astype(float)
        
        self.user_encoder = LabelEncoder()
        self.item_encoder = LabelEncoder()
        
        all_user_ids = interactions[self._user_id_key].unique()
        all_item_ids = interactions[self._item_id_key].unique()
        
        self.user_encoder.fit(all_user_ids)
        self.item_encoder.fit(all_item_ids)
        
        interactions['user_idx'] = self.user_encoder.transform(interactions[self._user_id_key])
        interactions['item_idx'] = self.item_encoder.transform(interactions[self._item_id_key])
        
        self._user_item_matrix = interactions.pivot_table(
            index=self._user_id_key, 
            columns=self._item_id_key, 
            values=self._rating_key,
            aggfunc='sum',
            fill_value=0
        )
        
        user_features = self._compute_user_features(interactions, users)
        item_features = self._compute_item_features(interactions, items)
        
        self._user_features = {row[self._user_id_key]: row.drop(self._user_id_key).values for _, row in user_features.iterrows()}
        self._item_features = {row[self._item_id_key]: row.drop(self._item_id_key).values for _, row in item_features.iterrows()}
        self._all_items = items
        
        X, y = self._prepare_training_data(interactions, user_features, item_features)
        
        loginfo(f"Training data shape: X={X.shape}, y={len(y)}")
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        if model_type == "rf":
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
        else:
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        
        loginfo(f"Training {model_type} model...")
        self.model.fit(X_scaled, y)
        loginfo("Model training complete")
        
        return self.model

    def _compute_user_features(self, interactions: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
        user_stats = interactions.groupby('client_id').agg({
            'quantity': ['sum', 'mean', 'std', 'count'],
            'unit_price': ['sum', 'mean', 'max'] if 'unit_price' in interactions.columns else ['sum', 'mean'],
        }).reset_index()
        
        user_stats.columns = ['client_id', 'total_quantity', 'avg_quantity', 'std_quantity', 
                             'n_purchases', 'total_spent', 'avg_price', 'max_price'] if 'unit_price' in interactions.columns else ['client_id', 'total_quantity', 'avg_quantity', 'std_quantity', 'n_purchases']
        
        user_stats['std_quantity'] = user_stats['std_quantity'].fillna(0)
        
        if 'max_price' not in user_stats.columns:
            user_stats['max_price'] = user_stats['avg_price']
        
        return user_stats

    def _compute_item_features(self, interactions: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
        item_stats = interactions.groupby('product_id').agg({
            'quantity': ['sum', 'mean', 'std', 'count'],
            'unit_price': ['mean', 'min', 'max'] if 'unit_price' in interactions.columns else ['mean'],
        }).reset_index()
        
        item_stats.columns = ['product_id', 'total_sold', 'avg_quantity', 'std_quantity', 
                             'n_buyers', 'avg_price', 'min_price', 'max_price'] if 'unit_price' in interactions.columns else ['product_id', 'total_sold', 'avg_quantity', 'std_quantity', 'n_buyers']
        
        item_stats['std_quantity'] = item_stats['std_quantity'].fillna(0)
        
        if 'min_price' not in item_stats.columns:
            item_stats['min_price'] = item_stats['avg_price']
        if 'max_price' not in item_stats.columns:
            item_stats['max_price'] = item_stats['avg_price']
        
        item_features = item_stats.merge(items, left_on='product_id', right_on='id', how='left')
        feature_cols = ['product_id', 'total_sold', 'avg_quantity', 'std_quantity', 'n_buyers', 'avg_price', 'min_price', 'max_price']
        if 'minimal_price' in item_features.columns:
            feature_cols.append('minimal_price')
        
        return item_features[feature_cols]

    def _prepare_training_data(
        self, 
        interactions: pd.DataFrame, 
        user_features: pd.DataFrame, 
        item_features: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        X_list = []
        y_list = []
        
        for _, row in interactions.iterrows():
            user_id = row['client_id']
            item_id = row['product_id']
            quantity = row['quantity']
            
            if user_id in self._user_features and item_id in self._item_features:
                user_feat = self._user_features[user_id]
                item_feat = self._item_features[item_id]
                
                if len(user_feat) == 8 and len(item_feat) >= 7:
                    user_feat = user_feat[:7]
                elif len(user_feat) == 4 and len(item_feat) >= 5:
                    item_feat = item_feat[:5]
                
                X_row = np.concatenate([user_feat, item_feat])
                X_list.append(X_row)
                y_list.append(quantity)
        
        return np.array(X_list), np.array(y_list)

    def predict_purchase_likelihood(self, user_id: int, item_id: int) -> float:
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")
        
        if user_id not in self._user_features or item_id not in self._item_features:
            return 0.0
        
        user_feat = self._user_features[user_id]
        item_feat = self._item_features[item_id]
        
        if len(user_feat) == 8 and len(item_feat) >= 7:
            user_feat = user_feat[:7]
        elif len(user_feat) == 4 and len(item_feat) >= 5:
            item_feat = item_feat[:5]
        
        X = np.concatenate([user_feat, item_feat]).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        prediction = self.model.predict(X_scaled)[0]
        
        return max(0.0, float(prediction))

    def recommend_repurchase(
        self,
        user_id: int,
        n_items: int = 10,
        items_to_exclude: Optional[List[int]] = None
    ) -> List[Tuple[int, str, float]]:
        if self._all_items is None or self._all_items.empty:
            return []
        
        scores = []
        for _, item_row in self._all_items.iterrows():
            item_id = int(item_row['id'])
            
            if items_to_exclude and item_id in items_to_exclude:
                continue
            
            try:
                score = self.predict_purchase_likelihood(user_id, item_id)
                item_name = item_row.get('name', '')
                scores.append((item_id, item_name, score))
            except Exception as e:
                logwarning(f"Error predicting for item {item_id}: {e}")
                continue
        
        scores.sort(key=lambda x: x[2], reverse=True)
        
        return scores[:n_items]

    def save_model(self, model_path: str) -> str:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'user_encoder': self.user_encoder,
            'item_encoder': self.item_encoder,
            'scaler': self.scaler,
            'user_features': self._user_features,
            'item_features': self._item_features,
            'all_items': self._all_items,
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        loginfo(f"Model saved to {model_path}")
        return model_path

    def load_model(self, model_path: str):
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.user_encoder = model_data['user_encoder']
        self.item_encoder = model_data['item_encoder']
        self.scaler = model_data['scaler']
        self._user_features = model_data['user_features']
        self._item_features = model_data['item_features']
        self._all_items = model_data['all_items']
        
        loginfo(f"Model loaded from {model_path}")
