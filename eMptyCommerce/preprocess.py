"""
Preprocess data - Tiền xử lý dữ liệu comments và book_data
Chuẩn bị dữ liệu cho hệ thống gợi ý Hybrid (Collaborative Filtering + Content-Based)

Phần 1: Xử lý comments.csv -> clean_reviews.csv (cho Collaborative Filtering)
Phần 2: Xử lý book_data.csv -> clean_book_data.csv (cho Content-Based + NLP)
"""

import pandas as pd
import numpy as np
import re
from pyvi import ViTokenizer
import os


def clean_and_tokenize(text):
    """
    Làm sạch và tách từ Tiếng Việt cho dòng text.
    
    Các bước xử lý:
    1. Chuyển thành chữ thường
    2. Xóa các dấu câu cơ bản (giữ lại chữ, số, khoảng trắng)
    3. Xóa khoảng trắng dư thừa
    4. Sử dụng ViTokenizer từ pyvi để tách từ Tiếng Việt
       (ví dụ: "điện thoại" -> "điện_thoại")
    
    Args:
        text (str): Dòng văn bản cần xử lý
    
    Returns:
        str: Văn bản đã được làm sạch và tách từ
    """
    # Kiểm tra nếu text là NaN hoặc None
    if pd.isna(text) or text == "":
        return ""
    
    text = str(text)
    
    # Chuyển sang chữ thường
    text = text.lower()
    
    # Xóa dấu câu cơ bản (giữ lại chữ, số, và khoảng trắng)
    text = re.sub(r'[^\w\s]', '', text)
    
    # Xóa khoảng trắng dư thừa
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Sử dụng ViTokenizer để tách từ Tiếng Việt
    if text:  # Chỉ tokenize nếu có nội dung
        try:
            text = ViTokenizer.tokenize(text)
        except Exception as e:
            print(f"   ⚠️  Lỗi tokenize: {e}")
            pass
    
    return text


def preprocess_comments():
    """
    PHẦN 1: Xử lý file comments.csv
    
    Các bước:
    1. Đọc comments.csv
    2. Xóa NaN ở customer_id, product_id, rating
    3. Ép kiểu rating về số
    4. Giảm độ thưa: giữ customer >= 3 đánh giá, product >= 5 đánh giá
    5. Lưu ra clean_reviews.csv (3 cột: customer_id, product_id, rating)
    """
    
    print("\n" + "=" * 80)
    print("PHẦN 1: XỬ LÝ COMMENTS.CSV - COLLABORATIVE FILTERING")
    print("=" * 80)
    
    # Bước 1: Đọc file
    print("\n📂 Bước 1: Đọc file data/comments.csv...")
    try:
        df_comments = pd.read_csv('data/comments.csv')
        print("✓ Đọc file thành công!")
        print(f"   - Kích thước: {df_comments.shape[0]} dòng × {df_comments.shape[1]} cột")
        print(f"   - Các cột: {list(df_comments.columns)}")
    except FileNotFoundError:
        print("❌ Lỗi: File data/comments.csv không tìm thấy!")
        return None
    
    dòng_ban_đầu = len(df_comments)
    
    # Bước 2: Xóa NaN
    print("\n🧹 Bước 2: Xóa dòng bị rỗng (NaN)...")
    print(f"   Dòng trước: {len(df_comments)}")
    
    # Xóa NaN ở 3 cột chính
    df_comments = df_comments.dropna(subset=['customer_id', 'product_id', 'rating'])
    
    # Loại bỏ đánh giá ảo từ FPT Shop (user u_01e8cc1e - Cao Thi My Duyen)
    df_comments = df_comments[df_comments['customer_id'] != 'u_01e8cc1e']
    
    print(f"   Dòng sau: {len(df_comments)}")
    print(f"   ✓ Đã xóa {dòng_ban_đầu - len(df_comments)} dòng rỗng")
    
    # Bước 3: Ép kiểu rating
    print("\n🔢 Bước 3: Ép kiểu cột 'rating' về số...")
    try:
        df_comments['rating'] = pd.to_numeric(df_comments['rating'], errors='coerce')
        df_comments = df_comments.dropna(subset=['rating'])
        print("✓ Ép kiểu thành công!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return None
    
    # Bước 4: Giảm độ thưa ma trận (Sparsity Reduction)
    print("\n📉 Bước 4: Giảm độ thưa ma trận (Sparsity Reduction)...")
    dòng_trước_lọc = len(df_comments)
    
    # Lọc customer có >= 3 đánh giá
    customer_counts = df_comments['customer_id'].value_counts()
    customers_to_keep = customer_counts[customer_counts >= 3].index
    df_comments = df_comments[df_comments['customer_id'].isin(customers_to_keep)]
    print(f"   ✓ Lọc customers: giữ lại {len(customers_to_keep)} customers (có >= 3 đánh giá)")
    
    # Lọc product có >= 5 đánh giá
    product_counts = df_comments['product_id'].value_counts()
    products_to_keep = product_counts[product_counts >= 5].index
    df_comments = df_comments[df_comments['product_id'].isin(products_to_keep)]
    print(f"   ✓ Lọc products: giữ lại {len(products_to_keep)} products (có >= 5 đánh giá)")
    
    dòng_sau_lọc = len(df_comments)
    tỷ_lệ = (dòng_sau_lọc / dòng_trước_lọc * 100) if dòng_trước_lọc > 0 else 0
    
    print(f"   📊 Dòng trước: {dòng_trước_lọc} | Dòng sau: {dòng_sau_lọc}")
    print(f"   📉 Tỷ lệ dữ liệu còn lại: {tỷ_lệ:.2f}%")
    
    # Bước 5: Chọn và lưu 3 cột
    print("\n💾 Bước 5: Lưu kết quả...")
    df_reviews = df_comments[['customer_id', 'product_id', 'rating']].copy()
    
    if not os.path.exists('data'):
        os.makedirs('data')
    
    output_path = 'data/clean_reviews.csv'
    df_reviews.to_csv(output_path, index=False)
    print(f"   ✓ Đã lưu vào: {output_path}")
    print(f"   📊 Kích thước cuối cùng: {df_reviews.shape[0]} dòng × {df_reviews.shape[1]} cột")
    
    # Lưu danh sách product để dùng ở phần 2
    products_in_reviews = set(df_reviews['product_id'].unique())
    
    return df_reviews, products_in_reviews


def preprocess_books(products_in_reviews):
    """
    PHẦN 2: Xử lý file book_data.csv
    
    Các bước:
    1. Đọc book_data.csv
    2. Chỉ giữ product có trong clean_reviews
    3. Fill NaN cho title, authors, category
    4. Gom 3 cột thành description
    5. Tokenize description
    6. Lưu ra clean_book_data.csv
    """
    
    print("\n\n" + "=" * 80)
    print("PHẦN 2: XỬ LÝ BOOK_DATA.CSV - CONTENT-BASED + NLP")
    print("=" * 80)
    
    # Bước 1: Đọc file
    print("\n📂 Bước 1: Đọc file data/book_data.csv...")
    try:
        df_books = pd.read_csv('data/book_data.csv')
        print("✓ Đọc file thành công!")
        print(f"   - Kích thước: {df_books.shape[0]} dòng × {df_books.shape[1]} cột")
        print(f"   - Các cột: {list(df_books.columns)}")
    except FileNotFoundError:
        print("❌ Lỗi: File data/book_data.csv không tìm thấy!")
        return
    
    dòng_ban_đầu = len(df_books)
    
    # Bước 2: Chỉ giữ product có trong clean_reviews
    print("\n🔗 Bước 2: Lọc sản phẩm có trong clean_reviews.csv...")
    print(f"   Dòng trước: {len(df_books)}")
    df_books = df_books[df_books['product_id'].isin(products_in_reviews)]
    print(f"   Dòng sau: {len(df_books)}")
    print(f"   ✓ Giữ lại {len(df_books)} sản phẩm có trong dữ liệu đánh giá")
    
    # Bước 3: Fill NaN
    print("\n🛠️  Bước 3: Xử lý giá trị rỗng (fillna)...")
    df_books['title'] = df_books['title'].fillna('')
    df_books['authors'] = df_books['authors'].fillna('')
    df_books['category'] = df_books['category'].fillna('')
    print("✓ Đã fill NaN bằng chuỗi rỗng ('')")
    
    # Bước 4: Gom description
    print("\n📝 Bước 4: Gom nội dung 3 cột thành 'description'...")
    df_books['description'] = (
        df_books['title'] + ' ' + 
        df_books['authors'] + ' ' + 
        df_books['category']
    )
    # Xóa khoảng trắng dư thừa
    df_books['description'] = df_books['description'].str.replace(r'\s+', ' ', regex=True).str.strip()
    print("✓ Tạo cột 'description' thành công!")
    print(f"   📝 Ví dụ: {df_books['description'].iloc[0][:100]}...")
    
    # Bước 5: Tokenize description
    print("\n🔤 Bước 5: Tokenize Tiếng Việt cho cột 'description'...")
    print("   ⏳ Đang xử lý (quá trình này mất một chút thời gian)...")
    
    df_books['tokenized_desc'] = df_books['description'].apply(clean_and_tokenize)
    
    print("✓ Hoàn tất tokenization!")
    print(f"   📝 Ví dụ tokenized: {df_books['tokenized_desc'].iloc[0][:100]}...")
    
    # Bước 6: Chọn cột và lưu
    print("\n💾 Bước 6: Lưu kết quả...")
    df_clean_books = df_books[['product_id', 'title', 'category', 'cover_link', 'tokenized_desc']].copy()
    
    if not os.path.exists('data'):
        os.makedirs('data')
    
    output_path = 'data/clean_book_data.csv'
    df_clean_books.to_csv(output_path, index=False)
    print(f"   ✓ Đã lưu vào: {output_path}")
    print(f"   📊 Kích thước cuối cùng: {df_clean_books.shape[0]} dòng × {df_clean_books.shape[1]} cột")
    
    return df_clean_books


def print_summary(df_reviews, df_books):
    """
    In ra báo cáo tóm lược sau khi tiền xử lý
    """
    print("\n\n" + "=" * 80)
    print("📊 BÁO CÁO TÓM LƯỢC")
    print("=" * 80)
    
    print("\n✅ PHẦN 1: DỮ LIỆU COLLABORATIVE FILTERING")
    print(f"   - Số dòng dữ liệu: {len(df_reviews)}")
    print(f"   - Số customers duy nhất: {df_reviews['customer_id'].nunique()}")
    print(f"   - Số products duy nhất: {df_reviews['product_id'].nunique()}")
    print(f"   - Mức đánh giá trung bình: {df_reviews['rating'].mean():.2f}")
    print(f"   - Khoảng đánh giá: {df_reviews['rating'].min():.0f} - {df_reviews['rating'].max():.0f}")
    print(f"   📁 File: data/clean_reviews.csv")
    
    print("\n✅ PHẦN 2: DỮ LIỆU CONTENT-BASED + NLP")
    print(f"   - Số sản phẩm: {len(df_books)}")
    print(f"   - Số cột: {len(df_books.columns)}")
    print(f"   - Các cột: {list(df_books.columns)}")
    print(f"   📁 File: data/clean_book_data.csv")
    
    print("\n" + "=" * 80)
    print("✅ TIỀN XỬ LÝ HOÀN TẤT!")
    print("=" * 80)
    print("\n💡 Dữ liệu đã sẵn sàng cho hệ thống gợi ý Hybrid:")
    print("   - clean_reviews.csv: Cho Collaborative Filtering")
    print("   - clean_book_data.csv: Cho Content-Based Filtering + NLP")


def main():
    """
    Hàm main - chạy toàn bộ quy trình tiền xử lý
    """
    print("\n" + "=" * 80)
    print("🔄 TIỀN XỬ LÝ DỮ LIỆU - HỆ THỐNG GỢI Ý SẢN PHẨM HYBRID")
    print("=" * 80)
    
    # Phần 1: Xử lý comments
    result_1 = preprocess_comments()
    if result_1 is None:
        return
    
    df_reviews, products_in_reviews = result_1
    
    # Phần 2: Xử lý books
    df_books = preprocess_books(products_in_reviews)
    if df_books is None:
        return
    
    # Báo cáo tóm lược
    print_summary(df_reviews, df_books)


if __name__ == "__main__":
    main()
