"""
Module để load dữ liệu sách và lấy hình ảnh bìa
"""

import pandas as pd
import os
from functools import lru_cache

# Đường dẫn đến dữ liệu sách
BOOK_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "clean_book_data.csv")


@lru_cache(maxsize=1)
def load_book_data():
    """
    Load dữ liệu sách từ CSV.
    Cache để tránh load lại nhiều lần.
    """
    try:
        df = pd.read_csv(BOOK_DATA_PATH)
        # Loại bỏ duplicate
        df = df.drop_duplicates(subset=['title'])
        return df
    except Exception as e:
        print(f"❌ Lỗi load dữ liệu sách: {e}")
        return None


def get_book_image(title):
    """
    Lấy URL hình ảnh của cuốn sách theo tên.
    
    Args:
        title: Tên cuốn sách
        
    Returns:
        URL hình ảnh hoặc None nếu không tìm thấy
    """
    try:
        df = load_book_data()
        if df is None:
            return None
        
        # Tìm sách có tiêu đề giống nhất (case-insensitive)
        mask = df['title'].str.lower().str.contains(title.lower(), na=False)
        matches = df[mask]
        
        if len(matches) > 0:
            cover_link = matches.iloc[0]['cover_link']
            # Kiểm tra URL hợp lệ
            if pd.notna(cover_link) and cover_link.startswith('http'):
                return cover_link
        
        return None
    except Exception as e:
        print(f"⚠️ Lỗi lấy ảnh sách '{title}': {e}")
        return None


def search_books_by_category(category, limit=5):
    """
    Tìm kiếm sách theo thể loại.
    
    Args:
        category: Thể loại sách
        limit: Số lượng kết quả tối đa
        
    Returns:
        DataFrame với sách tìm được
    """
    try:
        df = load_book_data()
        if df is None:
            return None
        
        matches = df[df['category'].str.lower() == category.lower()]
        return matches.head(limit)
    except Exception as e:
        print(f"⚠️ Lỗi tìm kiếm theo thể loại: {e}")
        return None


def get_popular_books(limit=10):
    """
    Lấy danh sách sách phổ biến (có cover_link).
    
    Args:
        limit: Số lượng kết quả tối đa
        
    Returns:
        DataFrame với sách có hình ảnh
    """
    try:
        df = load_book_data()
        if df is None:
            return None
        
        # Lọc sách có cover_link
        df_with_images = df[df['cover_link'].notna() & (df['cover_link'].str.len() > 0)]
        return df_with_images.head(limit)
    except Exception as e:
        print(f"⚠️ Lỗi lấy sách phổ biến: {e}")
        return None
