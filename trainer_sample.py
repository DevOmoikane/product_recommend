import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# TODO:
from implicit.nearest_neighbours import bm25_weight
from implicit.als import AlternatingLeastSquares

# surprise works with only ratings
from surprise import Dataset, Reader, KNNBasic, SVD, accuracy
from surprise.model_selection import train_test_split

import logging
from pprint import pprint

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
# get logging from implicit and mute it
logging.getLogger("implicit").setLevel(logging.ERROR)


engine = create_engine('postgresql://postgres:arkus123@172.17.0.1:5432/testdata')
#df = pd.read_csv('data.csv')
QUERY_ORDER_BY_CLIENT = '''SELECT doi.quantity, doi.unit_price, c.name as client, c.id as client_id, p.name as product, p.id as product_id, p.minimal_price, p.usd_cost, p.mnx_cost_no_iva, p.sales_no_taxes, p.sales_with_taxes
FROM delivery_orders as dlvo
JOIN delivery_order_items as doi on doi.delivery_order_id = dlvo.id
JOIN clients as c on c.id = dlvo.client_id
JOIN products as p on p.id = doi.product_id;'''

original_df = pd.read_sql_query(QUERY_ORDER_BY_CLIENT, engine)

columns = ['quantity', 'unit_price', 'client', 'client_id', 'product', 'product_id', 'minimal_price', 'usd_cost', 'mnx_cost_no_iva', 'sales_no_taxes', 'sales_with_taxes']
data_columns = ['unit_price', 'client_id', 'product_id', 'minimal_price']
target_column = 'quantity'

import pickle
def save_model(model, filename):
    with open(filename, 'wb') as f:
        pickle.dump(model, f)

def load_model(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

# remove nulls or non numeric rows from the df
df = original_df[data_columns + [target_column]].dropna(axis='index')

user_cat = df['client_id'].astype('category')
item_cat = df['product_id'].astype('category')

# train a model using the implicit library
from implicit.als import AlternatingLeastSquares

# create a sparse matrix of user-item interactions
from scipy.sparse import coo_matrix

# use the original data
# rows = df['client_id'].astype(int)
# cols = df['product_id'].astype(int)
# data = df['quantity'].astype(float)

# use a remap of the sequential indices
df['user_idx'] = user_cat.cat.codes.astype(np.int32)
df['item_idx'] = item_cat.cat.codes.astype(np.int32)

rows = df['user_idx'].to_numpy()
cols = df['item_idx'].to_numpy()
data = df['quantity'].astype(np.float32).to_numpy()

pprint(df.head())

# create the sparse matrix
user_item_matrix = coo_matrix((data, (rows, cols))).tocsr()

# apply bm25 weighting to the user-item matrix
# weighted_matrix = bm25_weight(user_item_matrix, K1=100, B=0.8)
weighted_matrix = bm25_weight(user_item_matrix, K1=100, B=0.8).tocsr()

# train the ALS model
model = AlternatingLeastSquares(factors=50, regularization=0.01, iterations=20)
model.fit(weighted_matrix)

print("user_factors:", model.user_factors.shape, "item_factors:", model.item_factors.shape)

user_id_map = dict(enumerate(user_cat.cat.categories))      # idx -> real user_id
item_id_map = dict(enumerate(item_cat.cat.categories))      # idx -> real item_id

user_to_idx = {v: k for k, v in user_id_map.items()}        # real user_id -> idx
item_to_idx = {v: k for k, v in item_id_map.items()}

# make recommendations for a user, using the mapped user id
real_user_id = 4
if real_user_id not in user_to_idx:
    raise ValueError(f"User {real_user_id} not present in training data")

user_idx = int(user_to_idx[real_user_id])

print(f"Shape of weighted user-item matrix: {weighted_matrix.shape}")
print(f"Type of user_idx = {type(user_idx)}, user_idx = {user_idx}")
print(f"Non-zero entries for user {real_user_id}: {weighted_matrix[user_idx].nnz}")
print(f"type(user_idx) = {type(user_idx)}, user_idx = {user_idx}")
print("isinstance(user_idx, int):", isinstance(user_idx, int))
print("np.isscalar(user_idx):", np.isscalar(user_idx))
print(f"model.user_factors.shape = {model.user_factors.shape}")
print(f"model.item_factors.shape = {model.item_factors.shape}")

assert weighted_matrix.shape[0] == model.user_factors.shape[0], \
    f"Rows in user_items ({weighted_matrix.shape[0]}) must equal model.user_factors ({model.user_factors.shape[0]})"

if weighted_matrix[user_idx].nnz == 0:
    raise ValueError(f"User {real_user_id} has no interactions in the training data")

# Ensure CSR float32 (you already did this above)
user_items_csr = weighted_matrix.tocsr().astype(np.float32, copy=False)

# Your version: recommend_all returns only ids (num_users x N)
all_ids = model.recommend_all(
    user_items_csr,
    N=10,
    filter_already_liked_items=True
)

product_ids = model.recommend(
    user_idx,
    user_items_csr.getrow(user_idx),
    N=10,
    filter_already_liked_items=True
)

# all_ids is a 2D array: (num_users, N)
print("recommend_all ids shape:", all_ids.shape)

# Extract recommendations for the specific user
top_items = all_ids[user_idx]  # shape (N,)

# Optionally compute scores manually (dot product user_factors · item_factors.T)
# This gives comparable ranking scores (not exactly the same as internal topk but fine)
uvec = model.user_factors[user_idx]                      # shape (factors,)
ivecs = model.item_factors[top_items]                    # shape (N, factors)
top_scores = ivecs @ uvec                                # shape (N,)

# Decode back to original item ids
decoded = [(int(item_id_map[i]), float(s)) for i, s in zip(top_items, top_scores)]
print("Recommended items:")
pprint(decoded)

# using the recommended items indices, get the original product ids and names and print them
recommended_products = []
for item_idx, score in zip(top_items, top_scores):
    original_item_id = item_id_map[item_idx]
    product_info = original_df[original_df['product_id'] == original_item_id][['product', 'product_id']].iloc[0]
    recommended_products.append((product_info['product'], product_info['product_id'], score))
print("Recommended products (name, id, score):")
pprint(recommended_products)

print("Products for user_id =", real_user_id)
decoded = [(int(item_id_map[i]), float(s)) for i, s in zip(product_ids[0], product_ids[1])]
print("Recommended items:")
pprint(decoded)

recommended_products = []
for item_idx, score in zip(product_ids[0], product_ids[1]):
    original_item_id = item_id_map[item_idx]
    product_info = original_df[original_df['product_id'] == original_item_id][['product', 'product_id']].iloc[0]
    recommended_products.append((product_info['product'], product_info['product_id'], score))
print("Recommended products (name, id, score):")
pprint(recommended_products)

# recomend similar items
# item_id = item_to_idx[111]  # example item ID
# similar_items = model.similar_items(item_id, N=10)
# print(similar_items)

# make batch recommendations for several products
# item_ids = [111, 61, 62]  # example item IDs
# batch_recommendations = model.recommend_batch(item_ids, user_item_matrix, N=10)
# print(batch_recommendations)
