import os
os.chdir('eMptyCommerce')

import pandas as pd
import numpy as np
from surprise import SVD, Dataset, Reader, accuracy, KNNWithMeans
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings("ignore")

print("="*80)
print("EVALUATING MODELS FOR SCIENTIFIC PAPER")
print("="*80)

# Load data
print("\nLoading data...")
df = pd.read_csv('data/clean_reviews.csv')
print(f"  Dataset size: {len(df)} ratings")

# Split data
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
print(f"  Train: {len(train_df)}, Test: {len(test_df)}")

# Get SVD and Hybrid results
print("\n📊 Evaluating Collaborative Filtering (SVD)...")
reader = Reader(rating_scale=(1, 5))
train_data = Dataset.load_from_df(
    train_df[['customer_id', 'product_id', 'rating']], reader)
trainset = train_data.build_full_trainset()

svd = SVD(n_factors=50, n_epochs=40, lr_all=0.005, reg_all=0.02, random_state=42)
svd.fit(trainset)

item_avg = train_df.groupby('product_id')['rating'].mean().to_dict()
global_avg = train_df['rating'].mean()

cf_preds, hybrid_preds, actuals = [], [], []
for _, row in test_df.iterrows():
    cf = svd.predict(row['customer_id'], row['product_id']).est
    cb = item_avg.get(row['product_id'], global_avg)
    hybrid = 0.6 * cf + 0.4 * cb
    cf_preds.append(cf)
    hybrid_preds.append(hybrid)
    actuals.append(row['rating'])

actuals = np.array(actuals)
rmse_cf = np.sqrt(np.mean((actuals - np.array(cf_preds))**2))
rmse_hybrid = np.sqrt(np.mean((actuals - np.array(hybrid_preds))**2))
mae_cf = np.mean(np.abs(actuals - np.array(cf_preds)))
mae_hybrid = np.mean(np.abs(actuals - np.array(hybrid_preds)))

print(f"  CF (SVD) RMSE: {rmse_cf:.4f}")
print(f"  CF (SVD) MAE: {mae_cf:.4f}")
print(f"  Hybrid RMSE: {rmse_hybrid:.4f}")
print(f"  Hybrid MAE: {mae_hybrid:.4f}")

# Get KNN results
print("\n📊 Evaluating Item-based KNN...")
test_data = Dataset.load_from_df(
    test_df[['customer_id', 'product_id', 'rating']], reader)
testset = test_data.build_full_trainset().build_testset()

sim_options = {'name': 'cosine', 'user_based': False, 'min_support': 2}
knn = KNNWithMeans(k=20, sim_options=sim_options, verbose=False)
knn.fit(trainset)

predictions = knn.test(testset)
rmse_knn = accuracy.rmse(predictions, verbose=False)
mae_knn = accuracy.mae(predictions, verbose=False)

print(f"  KNN RMSE: {rmse_knn:.4f}")
print(f"  KNN MAE: {mae_knn:.4f}")

# Summary
print("\n" + "="*80)
print("EVALUATION RESULTS SUMMARY")
print("="*80)
print(f"\nModel Comparison Table:")
print(f"{'Model':<30} {'RMSE':<15} {'MAE':<15}")
print("-"*60)
print(f"{'Content-Based (TF-IDF)':<30} {'N/A':<15} {'N/A':<15}")
print(f"{'Item-based KNN':<30} {rmse_knn:<15.4f} {mae_knn:<15.4f}")
print(f"{'Collaborative Filtering (SVD)':<30} {rmse_cf:<15.4f} {mae_cf:<15.4f}")
print(f"{'Hybrid Model (α=0.4, β=0.6)':<30} {rmse_hybrid:<15.4f} {mae_hybrid:<15.4f}")

print(f"\nAnalysis:")
print(f"  - Hybrid improves over CF: {((rmse_cf - rmse_hybrid) / rmse_cf * 100):.2f}% RMSE reduction")
print(f"  - KNN vs CF: KNN RMSE is {'better' if rmse_knn < rmse_cf else 'worse'} by {abs(rmse_knn - rmse_cf):.4f}")
print("="*80)
