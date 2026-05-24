import pandas as pd
import os

# Kiểm tra các file CSV tồn tại
files_to_check = [
    'eMptyCommerce/data/clean_book_data.csv',
    'eMptyCommerce/data/clean_reviews.csv',
    'eMptyCommerce/data/book_data.csv'
]

print('=== KIỂM TRA CÁC FILE ===\n')
for f in files_to_check:
    exists = os.path.exists(f)
    status = 'OK' if exists else 'KHONG CO'
    print(f'{f}: {status}')
    if exists:
        df = pd.read_csv(f)
        print(f'  - Kich thuoc: {df.shape[0]} dong, {df.shape[1]} cot')
        print(f'  - Cot: {list(df.columns)}\n')

# ========== CÂU HỎI 1: Tìm "Cây Cam Ngọt" ==========
print('\n' + '='*60)
print('CÂU HỎI 1: Tìm product_id của "Cây Cam Ngọt Của Tôi"')
print('='*60)

df_books = pd.read_csv('eMptyCommerce/data/clean_book_data.csv')
# Tìm kiếm không phân biệt hoa thường, chứa "Cây Cam Ngọt"
mask = df_books['title'].str.contains('Cây Cam Ngọt', case=False, na=False)
results = df_books[mask][['product_id', 'title']]

print(f'\nSố dòng tìm được: {len(results)}')
print('\nChi tiết:')
for idx, row in results.iterrows():
    print(f"  - product_id: {row['product_id']}")
    print(f"    title: {row['title']}\n")

# ========== CÂU HỎI 2: Customer_id có nhiều rating nhất ==========
print('\n' + '='*60)
print('CÂU HỎI 2: Tìm customer_id có nhiều rating nhất')
print('='*60)

df_reviews = pd.read_csv('eMptyCommerce/data/clean_reviews.csv')
customer_counts = df_reviews['customer_id'].value_counts()
top_customer_id = customer_counts.index[0]
top_customer_count = customer_counts.iloc[0]

customer_data = df_reviews[df_reviews['customer_id'] == top_customer_id]
avg_rating = customer_data['rating'].mean()

print(f'\ncustomer_id: {top_customer_id}')
print(f'Số sản phẩm đã rate: {top_customer_count}')
print(f'Rating trung bình: {avg_rating:.4f}')
print(f'Chi tiết rating: min={customer_data["rating"].min()}, max={customer_data["rating"].max()}')

# ========== CÂU HỎI 3: Kiểm tra customer_id = 22051463 ==========
print('\n' + '='*60)
print('CÂU HỎI 3: Kiểm tra customer_id = 22051463')
print('='*60)

check_customer = 22051463
exists_check = check_customer in df_reviews['customer_id'].values

if exists_check:
    customer_data_check = df_reviews[df_reviews['customer_id'] == check_customer]
    count_check = len(customer_data_check)
    avg_rating_check = customer_data_check['rating'].mean()
    print(f'\nTồn tại: Có')
    print(f'Số sản phẩm đã rate: {count_check}')
    print(f'Rating trung bình: {avg_rating_check:.4f}')
else:
    print(f'\nTồn tại: Không')
    print(f'Đề xuất thay bằng top 5 customer_id có nhiều rating:')
    for i, (cid, count) in enumerate(customer_counts.head(5).items(), 1):
        print(f'  {i}. customer_id {cid}: {count} ratings')

# ========== CÂU HỎI 4: Thống kê dataset ==========
print('\n' + '='*60)
print('CÂU HỎI 4: Thống kê dataset')
print('='*60)

print(f'\nclean_reviews.csv:')
print(f'  - Tổng số dòng: {len(df_reviews)}')
print(f'  - customer_id: min={df_reviews["customer_id"].min()}, max={df_reviews["customer_id"].max()}')
print(f'  - product_id: min={df_reviews["product_id"].min()}, max={df_reviews["product_id"].max()}')
print(f'  - rating: min={df_reviews["rating"].min()}, max={df_reviews["rating"].max()}')

print(f'\nclean_book_data.csv:')
print(f'  - Tổng số dòng: {len(df_books)}')
print(f'  - product_id: min={df_books["product_id"].min()}, max={df_books["product_id"].max()}')

# Cộng dồn thêm thông tin từ book_data.csv
df_book_full = pd.read_csv('eMptyCommerce/data/book_data.csv')
print(f'\nbook_data.csv:')
print(f'  - Tổng số dòng: {len(df_book_full)}')
print(f'  - product_id: min={df_book_full["product_id"].min()}, max={df_book_full["product_id"].max()}')
