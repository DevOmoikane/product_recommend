import numpy as np
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from scipy.sparse import csr_matrix
from app.model_base import ModelBase
from ml_library.utils.log import *
from implicit.recommender_base import RecommenderBase


class Recommender(ModelBase):
    def __init__(self, model_path: Optional[str] = None, uri: Optional[str] = None, config_path: Optional[str] = None):
        super().__init__(uri=uri, config_path=config_path)
        if model_path:
            self.load_model(model_path)

    def recommend(
        self,
        user_id: int,
        n_items: int = 10,
        filter_already_liked_items: bool = True,
        items_to_exclude: Optional[List[int]] = None,
        user_col: Optional[str] = None,
        item_col: Optional[str] = None,
        rating_col: Optional[str] = None,
        interactions_query: Optional[str] = None,
        items_query: Optional[str] = None,
        users_query: Optional[str] = None
    ) -> List[Tuple[int, float]]:
        if self.model is None:
            loginfo("No model loaded. Trying to load default model from config.")
            model_type = self._config.get("models.default", "als")
            model_path = self._config.get(f"persistence.default_model", "./models/model.pkl")
            if model_path:
                loginfo(f"Loading default model from {model_path}")
                self.load_model(model_path)
            else:
                raiselog(ValueError("No model loaded. No default model path found in config. Please load a model or check your config."))

        if user_id not in self._user_mapping:
            raiselog(ValueError(f"User {user_id} not found in training data"))
        
        self.load_data(interactions_query, items_query, users_query)
        self.build_matrix(user_col or self._user_cols, item_col or self._item_cols, rating_col or self._rating_cols)

        user_idx = self._user_mapping[user_id]
        
        if self._matrix is not None or self._weighted_matrix is not None:
            loginfo(f"Using original user-item matrix for recommendations")
            loginfo(f"Original matrix shape: {self._matrix.shape}, nnz: {self._matrix.nnz}")
            loginfo(f"Weighted matrix shape: {self._weighted_matrix.shape if self._weighted_matrix is not None else 'N/A'}, nnz: {self._weighted_matrix.nnz if self._weighted_matrix is not None else 'N/A'}")
            matrix = self._weighted_matrix if self._weighted_matrix is not None else self._matrix
            # user_items = self._matrix.getrow(user_idx).astype(np.float32)
            user_items = matrix.tocsr().astype(np.float32, copy=False).getrow(user_idx)
        else:
            if self.model is not None:
                loginfo(f"Using model's user_items for recommendations")
                user_items = self.model.user_items.astype(np.float32).getrow(user_idx)
        
        loginfo(f"user_items shape: {user_items.shape}, nnz: {user_items.nnz}")
        if user_items is None or user_items.shape[0] != 1:
            raiselog(ValueError("User-item matrix is not available for recommendations"))

        try:
            item_ids, scores = self.model.recommend(
                int(user_idx),
                user_items,
                N=n_items,
                filter_already_liked_items=filter_already_liked_items,
            )
            loginfo(f"Recommendation results: {len(item_ids)} items")
            logobject(list(zip(item_ids, scores)), message="Recommended item indices and scores")
        except Exception as e:
            raiselog(ValueError(f"Error during recommendation: {e}"))

        if self._items_df is None or self._items_df.empty:
            self.load_data(interactions_query, items_query, users_query)

        logobject(self._items_df, message="Items dataframe head for recommendation")

        # logobject(self._item_mapping, message="Item mapping for recommendation")
        # logobject(self._reverse_item_mapping, message="Reverse item mapping for recommendation")
        item_ids = np.append(item_ids, 0)
        scores = np.append(scores, 0.0)

        results = []
        for item_idx, score in zip(item_ids, scores):
            original_item_id = int(item_idx)#int(self._reverse_item_mapping.get(item_idx, -1))
            if original_item_id == -1:
                logwarning(f"Item index {item_idx} not found in reverse item mapping")
                continue
            item = self._items_df.loc[self._items_df['id'] == np.int64(original_item_id)]
            # assign to item only one row of item
            item = item.iloc[0] if not item.empty else None
            loginfo(f"Found item for index {item_idx}:{original_item_id}:{np.int64(original_item_id)}: {item}")
            if item is None:
                continue
            original_item_name = item.get("name", None)
            if original_item_id is not None:
                results.append((original_item_id, original_item_name, float(score)))

        if items_to_exclude:
            exclude_indices = {self._item_mapping.get(i) for i in items_to_exclude if i in self._item_mapping}
            results = [(i, n, s) for i, n, s in results if i not in exclude_indices]

        return results[:n_items]

    def recommend_repurchase(
        self,
        user_id: int,
        n_items: int = 10,
        items_to_exclude: Optional[List[int]] = None,
    ) -> List[Tuple[int, float]]:
        return self.recommend(
            user_id=user_id,
            n_items=n_items,
            filter_already_liked_items=False,
            items_to_exclude=items_to_exclude,
        )

    def recommend_new_item(
        self,
        user_id: int,
        n_items: int = 10,
        items_to_exclude: Optional[List[int]] = None,
    ) -> List[Tuple[int, float]]:
        return self.recommend(
            user_id=user_id,
            n_items=n_items,
            filter_already_liked_items=True,
            items_to_exclude=items_to_exclude,
        )

    def get_similar_items(
        self,
        item_id: int,
        n_items: int = 10,
    ) -> List[Tuple[int, float]]:
        if self.model is None:
            raiselog(ValueError("No model loaded. Call load_model() or train first."))

        if item_id not in self._item_mapping:
            raiselog(ValueError(f"Item {item_id} not found in training data"))

        item_idx = self._item_mapping[item_id]

        if hasattr(self.model, "similar_items"):
            similar_item_ids, scores = self.model.similar_items(item_idx, N=n_items + 1)
        else:
            raiselog(ValueError(f"Model {self._model_type} does not support similar items"))

        results = []
        for sim_item_idx, score in zip(similar_item_ids, scores):
            original_item_id = self._reverse_item_mapping.get(sim_item_idx)
            if original_item_id is not None and original_item_id != item_id:
                results.append((original_item_id, float(score)))

        return results[:n_items]

    def get_user_recommendations(
        self,
        n_users: int = 10,
        n_items: int = 10,
    ) -> Dict[int, List[Tuple[int, float]]]:
        if self.model is None:
            raiselog(ValueError("No model loaded. Call load_model() or train first."))

        results = {}
        for user_id in list(self._reverse_user_mapping.keys())[:n_users]:
            try:
                recommendations = self.recommend(user_id, n_items=n_items)
                results[user_id] = recommendations
            except ValueError:
                continue

        return results
