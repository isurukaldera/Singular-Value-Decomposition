# -*- coding: utf-8 -*-
"""SVD

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1oUoP8MAt9GIbZese7DIPwBYxr_hyzbLf
"""

import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_squared_error, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from math import sqrt

CHUNK_SIZE = 20000
N_COMPONENTS = 10
RANDOM_STATE = 42

def load_dataset(file_path):

    chunks = []
    for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE):
        chunks.append(chunk)
    return pd.concat(chunks)

def create_user_movie_matrix(df):

    return df.pivot_table(index='userId', columns='movieId', values='rating', fill_value=0)

def preprocess_splits(train_df, test_df):

    train_matrix = create_user_movie_matrix(train_df)
    test_matrix = create_user_movie_matrix(test_df)

    common_users = train_matrix.index.intersection(test_matrix.index)
    common_movies = train_matrix.columns.intersection(test_matrix.columns)

    return (
        train_matrix.loc[common_users, common_movies],
        test_matrix.loc[common_users, common_movies]
    )

def normalize_predictions(reconstructed, ratings):

    min_rating, max_rating = ratings['rating'].min(), ratings['rating'].max()
    return (reconstructed - reconstructed.min()) / (reconstructed.max() - reconstructed.min()) * (max_rating - min_rating) + min_rating

def train_svd(matrix):

    svd = TruncatedSVD(n_components=N_COMPONENTS, random_state=RANDOM_STATE)
    U = svd.fit_transform(matrix)
    Sigma = svd.singular_values_
    VT = svd.components_
    return U, Sigma, VT

def reconstruct_matrix(U, Sigma, VT, ratings):

    reconstructed = np.dot(U, np.dot(np.diag(Sigma), VT))
    return normalize_predictions(reconstructed, ratings)

def evaluate_predictions(true_matrix, pred_matrix):

    mask = np.array(true_matrix).flatten() != 0
    true_flat = np.array(true_matrix).flatten()[mask]
    pred_flat = pred_matrix.flatten()[mask]

    rmse = sqrt(mean_squared_error(true_flat, pred_flat))

    threshold = 3.5
    true_binary = (true_flat >= threshold).astype(int)
    pred_binary = (pred_flat >= threshold).astype(int)

    precision = precision_score(true_binary, pred_binary, zero_division=0, average='weighted')
    recall = recall_score(true_binary, pred_binary, zero_division=0, average='weighted')
    f1 = f1_score(true_binary, pred_binary, zero_division=0, average='weighted')

    return rmse, precision, recall, f1

def recommend_movies(user_id, pred_matrix, user_mapper, movie_mapper, top_n=5):

    if user_id not in user_mapper:
        return []

    user_idx = user_mapper.get_loc(user_id)
    user_ratings = pred_matrix[user_idx]

    unrated_mask = np.array(pred_matrix[user_idx]) == 0
    unrated_movie_indices = np.where(unrated_mask)[0]

    recommendations = []
    for idx in unrated_movie_indices:
        movie_id = movie_mapper[idx]
        recommendations.append((movie_id, user_ratings[idx]))

    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:top_n]

def main():

    ratings = load_dataset('ml-latest-small/ratings.csv')

    train_random, test_random = train_test_split(ratings, test_size=0.2, random_state=RANDOM_STATE)
    ratings_sorted = ratings.sort_values('timestamp')
    cutoff = ratings_sorted['timestamp'].quantile(0.8)
    train_temporal = ratings_sorted[ratings_sorted['timestamp'] <= cutoff]
    test_temporal = ratings_sorted[ratings_sorted['timestamp'] > cutoff]


    for split_type, train_df, test_df in [('Random', train_random, test_random), ('Temporal', train_temporal, test_temporal)]:
        print(f"\nEvaluating {split_type} Split")


        train_matrix, test_matrix = preprocess_splits(train_df, test_df)

        U, Sigma, VT = train_svd(train_matrix)

        pred_matrix = reconstruct_matrix(U, Sigma, VT, train_df)


        rmse, precision, recall, f1 = evaluate_predictions(test_matrix, pred_matrix)
        print(f"{split_type} Split RMSE: {rmse:.4f}")
        print(f"{split_type} Split Precision: {precision:.4f}")
        print(f"{split_type} Split Recall: {recall:.4f}")
        print(f"{split_type} Split F1-Score: {f1:.4f}")

        user_id = 2
        user_mapper = train_matrix.index
        movie_mapper = train_matrix.columns

        recommendations = recommend_movies(user_id, pred_matrix, user_mapper, movie_mapper)
        print(f"\nTop recommendations for user {user_id}:")
        for movie_id, rating in recommendations:
            print(f"Movie ID: {movie_id}, Predicted Rating: {rating:.2f}")

        print(f"\nOriginal ratings for user {user_id}:")
        print(train_df[train_df['userId'] == user_id][['movieId', 'rating']].head())

if __name__ == "__main__":
    main()

