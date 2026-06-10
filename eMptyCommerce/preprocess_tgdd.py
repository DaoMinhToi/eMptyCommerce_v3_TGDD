#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kịch bản tiền xử lý dữ liệu Thế Giới Di Động (preprocess_tgdd.py)
Chuẩn bị dữ liệu để nạp trực tiếp vào hệ thống gợi ý Hybrid Recommender hiện tại.
Đầu ra:
1. data/clean_reviews.csv: customer_id, product_id, rating
2. data/clean_book_data.csv: product_id, title, category, cover_link, tokenized_desc
3. data/book_data.csv: product_id, title, category, cover_link, current_price, n_review, avg_rating (Đồng bộ ứng dụng UI)
"""

import os
import re
import pandas as pd
import numpy as np
from pyvi import ViTokenizer

def clean_and_tokenize(text):
    """
    Làm sạch và tách từ tiếng Việt cho dòng văn bản sử dụng PyVi.
    """
    if pd.isna(text) or text == "":
        return ""
    
    text = str(text)
    # Chuyển sang chữ thường
    text = text.lower()
    # Loại bỏ các mã HTML nếu có (ví dụ các thẻ <span> hoặc <a> trong specs)
    text = re.sub(r'<[^>]*>', '', text)
    # Xóa dấu câu cơ bản
    text = re.sub(r'[^\w\s]', ' ', text)
    # Xóa khoảng trắng dư thừa
    text = re.sub(r'\s+', ' ', text).strip()
    
    if text:
        try:
            text = ViTokenizer.tokenize(text)
        except Exception as e:
            pass
    return text

def preprocess_reviews():
    """
    Tiền xử lý file data/reviews.csv -> data/clean_reviews.csv
    """
    print("\n" + "=" * 80)
    print("PHẦN 1: TIỀN XỬ LÝ ĐÁNH GIÁ (REVIEWS) -> COLLABORATIVE FILTERING")
    print("=" * 80)
    
    input_path = 'data/reviews.csv'
    output_path = 'data/clean_reviews.csv'
    
    if not os.path.exists(input_path):
        print(f"❌ Lỗi: Không tìm thấy file {input_path}!")
        return None, None, None
        
    print(f"📂 Đang đọc dữ liệu từ {input_path}...")
    df_raw = pd.read_csv(input_path)
    print(f"✓ Đọc thành công: {len(df_raw)} dòng đánh giá.")
    
    # 1. Loại bỏ các dòng trống ở các cột quan trọng
    df = df_raw.dropna(subset=['user_id', 'product_id', 'rating']).copy()
    df['product_id'] = df['product_id'].astype(str).str.strip()
    df['user_id'] = df['user_id'].astype(str).str.strip()
    
    # 2. Ép kiểu rating về số
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df = df.dropna(subset=['rating'])
    
    # 3. Chuẩn hóa tên cột để khớp với Recommender (user_id -> customer_id)
    df = df.rename(columns={'user_id': 'customer_id'})
    
    # 4. Loại bỏ trùng lặp để tránh nhiễu
    df_clean = df[['customer_id', 'product_id', 'rating']].copy()
    df_clean = df_clean.drop_duplicates(subset=['customer_id', 'product_id'], keep='first')
    
    df_clean.to_csv(output_path, index=False)
    print(f"✓ Đã lọc trùng lặp và lưu {len(df_clean)} đánh giá sạch vào: {output_path}")
    
    products_in_reviews = set(df_clean['product_id'].unique())
    return df_clean, products_in_reviews, df_raw

def preprocess_products(products_in_reviews, df_reviews_raw):
    """
    Tiền xử lý file data/products.csv -> clean_book_data.csv & book_data.csv
    """
    print("\n\n" + "=" * 80)
    print("PHẦN 2: TIỀN XỬ LÝ SẢN PHẨM (PRODUCTS) -> CONTENT-BASED + NLP")
    print("=" * 80)
    
    input_path = 'data/products.csv'
    clean_book_path = 'data/clean_book_data.csv'
    book_data_path = 'data/book_data.csv'
    
    if not os.path.exists(input_path):
        print(f"❌ Lỗi: Không tìm thấy file {input_path}!")
        return None
        
    print(f"📂 Đang đọc dữ liệu từ {input_path}...")
    df = pd.read_csv(input_path)
    print(f"✓ Đọc thành công: {len(df)} dòng sản phẩm.")
    
    # Chuẩn hóa cột product_id
    df['product_id'] = df['product_id'].astype(str).str.strip()
    
    # 1. Tính toán n_review và avg_rating từ file reviews gốc
    print("📊 Đang tính toán thống kê đánh giá (số lượng và trung bình sao)...")
    df_reviews_raw['product_id'] = df_reviews_raw['product_id'].astype(str).str.strip()
    df_reviews_raw['rating'] = pd.to_numeric(df_reviews_raw['rating'], errors='coerce')
    
    reviews_grouped = df_reviews_raw.groupby('product_id').agg(
        n_review=('rating', 'count'),
        avg_rating=('rating', 'mean')
    ).reset_index()
    
    # Merge thông số review vào sản phẩm
    df = df.merge(reviews_grouped, on='product_id', how='left')
    df['n_review'] = df['n_review'].fillna(0).astype(int)
    df['avg_rating'] = df['avg_rating'].fillna(0.0).round(2)
    
    # 2. Xử lý giá trị NaN/Rỗng
    df['title'] = df['title'].fillna('')
    df['brand'] = df['brand'].fillna('')
    df['category'] = df['category'].fillna('')
    df['description'] = df['description'].fillna('')
    df['specs'] = df['specs'].fillna('')
    df['image_url'] = df['image_url'].fillna('')
    df['price'] = df['price'].fillna(0).astype(int)
    
    # 3. Tạo cột mô tả tổng hợp (Title + Brand + Category + Description + Specs) để tăng độ chính xác TF-IDF
    print("📝 Đang tổng hợp nội dung văn bản đặc trưng sản phẩm...")
    df['combined_text'] = (
        df['title'] + ' ' +
        df['brand'] + ' ' +
        df['category'] + ' ' +
        df['description'] + ' ' +
        df['specs']
    )
    
    # 4. Tách từ tiếng Việt bằng PyVi cho clean_book_data.csv
    print("🔤 Đang chạy tách từ Tiếng Việt (ViTokenizer.tokenize) cho đặc trưng nội dung...")
    df['tokenized_desc'] = df['combined_text'].apply(clean_and_tokenize)
    print("✓ Tách từ thành công!")
    
    # 5. Lưu ra file data/book_data.csv (Đồng bộ UI / Giá tiền / Ảnh)
    # Khớp tên cột: image_url -> cover_link, price -> current_price
    df_renamed = df.rename(columns={'image_url': 'cover_link', 'price': 'current_price'})
    
    df_book_data = df_renamed[['product_id', 'title', 'category', 'cover_link', 'current_price', 'n_review', 'avg_rating']].copy()
    # Chỉ giữ lại sản phẩm có đánh giá trong clean_reviews.csv để tránh phân rã mô hình
    df_book_data_filtered = df_book_data[df_book_data['product_id'].isin(products_in_reviews)]
    df_book_data_filtered.to_csv(book_data_path, index=False)
    print(f"✓ Đã lưu {len(df_book_data_filtered)} sản phẩm đầy đủ vào: {book_data_path}")
    
    # 6. Lưu ra file data/clean_book_data.csv (Dùng cho Content-Based TF-IDF)
    df_clean_books = df_renamed[['product_id', 'title', 'category', 'cover_link', 'tokenized_desc']].copy()
    df_clean_books_filtered = df_clean_books[df_clean_books['product_id'].isin(products_in_reviews)]
    df_clean_books_filtered.to_csv(clean_book_path, index=False)
    print(f"✓ Đã lưu {len(df_clean_books_filtered)} sản phẩm NLP sạch vào: {clean_book_path}")
    
    return df_book_data_filtered

def print_summary(df_reviews, df_products):
    """In ra tóm tắt báo cáo xử lý dữ liệu"""
    print("\n" + "=" * 80)
    print("📊 BÁO CÁO TIỀN XỬ LÝ DỮ LIỆU THẾ GIỚI DI ĐỘNG")
    print("=" * 80)
    print(f"✅ DỮ LIỆU ĐÁNH GIÁ (clean_reviews.csv):")
    print(f"   - Tổng số dòng đánh giá: {len(df_reviews)}")
    print(f"   - Số khách hàng (customer_id) duy nhất: {df_reviews['customer_id'].nunique()}")
    print(f"   - Số sản phẩm (product_id) duy nhất: {df_reviews['product_id'].nunique()}")
    print(f"   - Điểm đánh giá trung bình: {df_reviews['rating'].mean():.2f} / 5.0")
    
    print(f"\n✅ DỮ LIỆU SẢN PHẨM (book_data.csv & clean_book_data.csv):")
    print(f"   - Tổng số sản phẩm đặc trưng: {len(df_products)}")
    print(f"   - Các danh mục sản phẩm cào được: {list(df_products['category'].unique())}")
    
    print("\n" + "=" * 80)
    print("🚀 TIỀN XỬ LÝ HOÀN TẤT - DỮ LIỆU ĐÃ SẴN SÀNG CHO HỆ THỐNG GỢI Ý HYBRID!")
    print("=" * 80)

def main():
    print("🔄 Bắt đầu quy trình xử lý dữ liệu Thế Giới Di Động...")
    df_reviews, products_in_reviews, df_reviews_raw = preprocess_reviews()
    if df_reviews is None:
        return
        
    df_products = preprocess_products(products_in_reviews, df_reviews_raw)
    if df_products is None:
        return
        
    print_summary(df_reviews, df_products)

if __name__ == '__main__':
    main()
