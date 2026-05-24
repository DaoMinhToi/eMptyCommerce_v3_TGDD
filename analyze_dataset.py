import pandas as pd
import numpy as np

print("\n" + "="*80)
print("DATASET ANALYSIS FOR SCIENTIFIC PAPER")
print("="*80)

# ============ CLEAN_REVIEWS.CSV ============
print("\n📊 1. CLEAN_REVIEWS.CSV (Collaborative Filtering Data)")
print("-"*80)
df_reviews = pd.read_csv('eMptyCommerce/data/clean_reviews.csv')
print(f"Rows: {len(df_reviews)}")
print(f"Columns: {df_reviews.columns.tolist()}")
print(f"Unique Customers: {df_reviews['customer_id'].nunique()}")
print(f"Unique Products: {df_reviews['product_id'].nunique()}")
print(f"Rating Range: {df_reviews['rating'].min():.0f} - {df_reviews['rating'].max():.0f}")
print(f"Rating Mean: {df_reviews['rating'].mean():.2f}")
print(f"Rating Std Dev: {df_reviews['rating'].std():.2f}")

# Calculate sparsity
max_interactions = df_reviews['customer_id'].nunique() * df_reviews['product_id'].nunique()
actual_interactions = len(df_reviews)
sparsity = (1 - actual_interactions / max_interactions) * 100
print(f"Matrix Sparsity: {sparsity:.2f}%")

print(f"\nRating Distribution:")
print(df_reviews['rating'].value_counts().sort_index())

print(f"\nFirst 3 rows:")
print(df_reviews.head(3).to_string())

# ============ CLEAN_BOOK_DATA.CSV ============
print("\n\n📚 2. CLEAN_BOOK_DATA.CSV (Content-Based Data)")
print("-"*80)
df_books = pd.read_csv('eMptyCommerce/data/clean_book_data.csv')
print(f"Total Products: {len(df_books)}")
print(f"Columns: {df_books.columns.tolist()}")

print(f"\nCategories Count:")
if 'category' in df_books.columns:
    print(df_books['category'].value_counts().head(10).to_string())

print(f"\nSample tokenized_desc:")
print(f"Example 1: {df_books['tokenized_desc'].iloc[0][:150]}")
print(f"Example 2: {df_books['tokenized_desc'].iloc[1][:150]}")

# ============ BOOK_DATA.CSV (ORIGINAL) ============
print("\n\n📖 3. BOOK_DATA.CSV (Original/Full Data)")
print("-"*80)
df_book_orig = pd.read_csv('eMptyCommerce/data/book_data.csv')
print(f"Total Records: {len(df_book_orig)}")
print(f"Unique Products: {df_book_orig['product_id'].nunique()}")
print(f"Columns: {df_book_orig.columns.tolist()}")

if 'n_review' in df_book_orig.columns and 'avg_rating' in df_book_orig.columns:
    print(f"\nReview Stats:")
    print(f"  Min reviews: {df_book_orig['n_review'].min():.0f}")
    print(f"  Max reviews: {df_book_orig['n_review'].max():.0f}")
    print(f"  Mean reviews: {df_book_orig['n_review'].mean():.0f}")
    print(f"  Min avg_rating: {df_book_orig['avg_rating'].min():.2f}")
    print(f"  Max avg_rating: {df_book_orig['avg_rating'].max():.2f}")
    print(f"  Mean avg_rating: {df_book_orig['avg_rating'].mean():.2f}")

# ============ COMMENTS.CSV (ORIGINAL) ============
print("\n\n💬 4. COMMENTS.CSV (Original/Raw Data)")
print("-"*80)
try:
    df_comments = pd.read_csv('eMptyCommerce/data/comments.csv')
    print(f"Total Comments: {len(df_comments)}")
    print(f"Columns: {df_comments.columns.tolist()}")
    
    # Check which columns are required for the system
    required_cols = ['customer_id', 'product_id', 'rating']
    for col in required_cols:
        if col in df_comments.columns:
            null_count = df_comments[col].isna().sum()
            print(f"  {col}: {null_count} nulls ({null_count/len(df_comments)*100:.2f}%)")
except Exception as e:
    print(f"Could not read comments.csv: {e}")

print("\n" + "="*80)
