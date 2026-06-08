"""
Module quản lý Database SQLite cho Hệ thống Giỏ hàng
Xử lý cả Cold-Start (khách vãng lai) và Warm-Start (khách đã đăng nhập)

Bảng chính:
- Carts: Quản lý giỏ hàng (với customer_id hoặc session_id)
- Cart_Items: Chi tiết sản phẩm trong giỏ hàng

Tính năng:
- Tạo/lấy giỏ hàng theo customer_id hoặc session_id
- Thêm/xóa sản phẩm vào giỏ
- Hợp nhất giỏ hàng khi người dùng mới đăng nhập
- Truy vấn thông tin giỏ hàng với chi tiết sản phẩm
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
import pandas as pd
from typing import Optional, List, Dict, Tuple


# ==================== CẤU HÌNH DATABASE ====================
DB_FILENAME = 'emptycm_store.db'
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, DB_FILENAME)


# ==================== HÀM TIỆN ÍCH ====================
@contextmanager
def get_db_connection():
    """
    Context manager để kết nối SQLite một cách an toàn.
    Tự động commit khi thành công, rollback khi có lỗi.
    
    Sử dụng:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Trả về dòng dữ liệu dạng dictionary
    conn.execute("PRAGMA foreign_keys = ON")  # Bật ràng buộc Foreign Key
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """
    Khởi tạo Database: Tạo các bảng Carts, Cart_Items, Orders và Order_Items nếu chưa tồn tại.
    
    Bảng Carts:
    - cart_id: Khóa chính, tự động tăng
    - customer_id: Khóa ngoài tới khách hàng (nullable cho khách vãng lai)
    - session_id: ID phiên cho khách vãng lai (nullable, unique)
    - created_at: Thời gian tạo giỏ hàng
    - updated_at: Thời gian cập nhật lần cuối
    - is_active: Trạng thái giỏ hàng (1 = hoạt động, 0 = bị xóa)
    
    Bảng Cart_Items:
    - cart_item_id: Khóa chính, tự động tăng
    - cart_id: Khóa ngoài tới bảng Carts
    - product_id: ID sản phẩm
    - quantity: Số lượng sản phẩm
    - added_at: Thời gian thêm vào giỏ
    - updated_at: Thời gian cập nhật lần cuối
    
    Bảng Orders:
    - order_id: Khóa chính (dạng chuỗi ngẫu nhiên VD: 'EMPTY_xxxxxx')
    - customer_id: ID khách hàng (nếu đăng nhập)
    - session_id: ID phiên (nếu khách vãng lai)
    - total_amount: Tổng tiền đơn hàng
    - payment_method: Phương thức thanh toán ('COD' hoặc 'BANK_TRANSFER')
    - payment_status: Trạng thái thanh toán ('Pending', 'Paid', 'Failed')
    - created_at: Thời gian tạo đơn hàng
    
    Bảng Order_Items:
    - id: Khóa chính
    - order_id: Khóa ngoại đến bảng Orders
    - product_id: ID sản phẩm
    - quantity: Số lượng
    - price: Giá sản phẩm tại thời điểm mua
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Bảng Carts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Carts (
                    cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NULLABLE,
                    session_id TEXT NULLABLE UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Bảng Cart_Items
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Cart_Items (
                    cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cart_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cart_id) REFERENCES Carts(cart_id) ON DELETE CASCADE,
                    UNIQUE(cart_id, product_id)
                )
            ''')
            
            # Bảng Orders
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Orders (
                    order_id TEXT PRIMARY KEY,
                    customer_id INTEGER,
                    session_id TEXT,
                    total_amount INTEGER,
                    payment_method TEXT,
                    payment_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Bảng Order_Items
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Order_Items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE
                )
            ''')
            
            print(f"✓ Database khởi tạo thành công: {DB_PATH}")
            
    except Exception as e:
        print(f"❌ Lỗi khởi tạo database: {e}")
        raise e



# ==================== CÁC HÀM QUẢN LÝ GIỎ HÀNG ====================

def get_or_create_cart(customer_id: Optional[int] = None, session_id: Optional[str] = None) -> int:
    """
    Lấy giỏ hàng hiện tại hoặc tạo mới.
    
    Logic:
    1. Nếu customer_id được cung cấp:
       - Tìm giỏ hàng chính thức của khách hàng
       - Nếu không tồn tại, tạo mới
    2. Nếu không có customer_id nhưng có session_id (khách vãng lai):
       - Tìm giỏ hàng dựa trên session_id
       - Nếu không tồn tại, tạo mới
    3. Ưu tiên: customer_id > session_id
    
    Args:
        customer_id: ID khách hàng (None nếu là khách vãng lai)
        session_id: ID phiên (dùng cho khách vãng lai)
    
    Returns:
        cart_id: ID của giỏ hàng
    
    Raises:
        ValueError: Nếu không cung cấp customer_id hoặc session_id
    """
    if customer_id is None and session_id is None:
        raise ValueError("Phải cung cấp customer_id hoặc session_id")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Tìm giỏ hàng hiện tại
            if customer_id is not None:
                cursor.execute('''
                    SELECT cart_id FROM Carts 
                    WHERE customer_id = ? AND is_active = 1
                    ORDER BY updated_at DESC LIMIT 1
                ''', (customer_id,))
                result = cursor.fetchone()
            else:
                cursor.execute('''
                    SELECT cart_id FROM Carts 
                    WHERE session_id = ? AND is_active = 1
                    ORDER BY updated_at DESC LIMIT 1
                ''', (session_id,))
                result = cursor.fetchone()

            if result:
                cart_id = result[0]
                # Cập nhật updated_at
                cursor.execute('''
                    UPDATE Carts SET updated_at = CURRENT_TIMESTAMP
                    WHERE cart_id = ?
                ''', (cart_id,))
                return cart_id

            # Nếu là session_id và có cart cũ bị inactive -> kích hoạt lại
            if customer_id is None:
                cursor.execute('''
                    SELECT cart_id FROM Carts 
                    WHERE session_id = ?
                    ORDER BY updated_at DESC LIMIT 1
                ''', (session_id,))
                inactive_result = cursor.fetchone()

                if inactive_result:
                    cart_id = inactive_result[0]
                    cursor.execute('''
                        UPDATE Carts
                        SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE cart_id = ?
                    ''', (cart_id,))
                    return cart_id
            
            # Tạo giỏ hàng mới
            cursor.execute('''
                INSERT INTO Carts (customer_id, session_id, created_at, updated_at, is_active)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
            ''', (customer_id, session_id))
            
            cart_id = cursor.lastrowid
            print(f"✓ Tạo giỏ hàng mới: cart_id={cart_id}, customer_id={customer_id}, session_id={session_id}")
            return cart_id
            
    except Exception as e:
        print(f"❌ Lỗi lấy/tạo giỏ hàng: {e}")
        raise e


def add_to_cart(cart_id: int, product_id: int, quantity: int = 1) -> bool:
    """
    Thêm sản phẩm vào giỏ hàng.
    
    Logic:
    1. Nếu sản phẩm đã tồn tại trong giỏ:
       - Cộng dồn quantity (UPDATE)
    2. Nếu sản phẩm chưa tồn tại:
       - Tạo bản ghi mới (INSERT)
    
    Args:
        cart_id: ID của giỏ hàng
        product_id: ID của sản phẩm
        quantity: Số lượng muốn thêm (mặc định: 1)
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    if quantity <= 0:
        print(f"⚠️ Số lượng không hợp lệ: {quantity}")
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra sản phẩm đã tồn tại trong giỏ hay chưa
            cursor.execute('''
                SELECT cart_item_id, quantity FROM Cart_Items
                WHERE cart_id = ? AND product_id = ?
            ''', (cart_id, product_id))
            
            result = cursor.fetchone()
            
            if result:
                # Sản phẩm đã tồn tại -> Cộng dồn quantity
                cart_item_id, existing_qty = result[0], result[1]
                new_qty = existing_qty + quantity
                cursor.execute('''
                    UPDATE Cart_Items
                    SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE cart_item_id = ?
                ''', (new_qty, cart_item_id))
                print(f"✓ Cập nhật sản phẩm trong giỏ: product_id={product_id}, quantity={existing_qty}→{new_qty}")
            else:
                # Sản phẩm chưa tồn tại -> Thêm mới
                cursor.execute('''
                    INSERT INTO Cart_Items (cart_id, product_id, quantity, added_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (cart_id, product_id, quantity))
                print(f"✓ Thêm sản phẩm vào giỏ: product_id={product_id}, quantity={quantity}")
            
            # Cập nhật updated_at của giỏ hàng
            cursor.execute('''
                UPDATE Carts SET updated_at = CURRENT_TIMESTAMP
                WHERE cart_id = ?
            ''', (cart_id,))
            
            return True
            
    except Exception as e:
        print(f"❌ Lỗi thêm sản phẩm vào giỏ: {e}")
        return False


def get_cart_items(cart_id: int) -> pd.DataFrame:
    """
    Truy xuất danh sách sản phẩm trong giỏ hàng.
    
    Kết nối với dữ liệu sách từ CSV (sử dụng book_data.csv) để lấy tên, giá (current_price), và ảnh bìa.
    
    Returns:
        DataFrame với các cột:
        - cart_item_id: ID mục trong giỏ
        - product_id: ID sản phẩm
        - title: Tên sách
        - category: Thể loại
        - cover_link: Link ảnh bìa
        - current_price: Giá tiền (số nguyên)
        - quantity: Số lượng
        - added_at: Thời gian thêm vào
        - updated_at: Thời gian cập nhật
    """
    try:
        with get_db_connection() as conn:
            # Truy vấn từ database
            cursor = conn.cursor()
            cursor.execute('''
                SELECT cart_item_id, product_id, quantity, added_at, updated_at
                FROM Cart_Items
                WHERE cart_id = ?
                ORDER BY added_at DESC
            ''', (cart_id,))
            
            items = cursor.fetchall()
            
            if not items:
                return pd.DataFrame()
            
            # Chuyển thành DataFrame
            df = pd.DataFrame([dict(item) for item in items])
            
            # Load dữ liệu sách từ CSV (sử dụng book_data.csv để lấy giá current_price)
            book_data_path = os.path.join(APP_DIR, 'data', 'book_data.csv')
            if os.path.exists(book_data_path):
                book_data = pd.read_csv(book_data_path)
                book_data = book_data.drop_duplicates(subset=['product_id'], keep='first')
                # Chuyển đổi current_price thành kiểu số nguyên nếu cần (mặc định 50000 nếu NaN)
                book_data['current_price'] = book_data['current_price'].fillna(50000).astype(int)
                # Join với dữ liệu sách để lấy title, category, cover_link, current_price
                df = df.merge(
                    book_data[['product_id', 'title', 'category', 'cover_link', 'current_price']],
                    on='product_id',
                    how='left'
                )
            else:
                # Nếu không có book_data.csv, thử lấy clean_book_data.csv và gán giá mặc định
                clean_path = os.path.join(APP_DIR, 'data', 'clean_book_data.csv')
                if os.path.exists(clean_path):
                    book_data = pd.read_csv(clean_path)
                    book_data = book_data.drop_duplicates(subset=['product_id'], keep='first')
                    book_data['current_price'] = 50000
                    df = df.merge(
                        book_data[['product_id', 'title', 'category', 'cover_link', 'current_price']],
                        on='product_id',
                        how='left'
                    )
            
            return df
            
    except Exception as e:
        print(f"❌ Lỗi lấy danh sách sản phẩm trong giỏ: {e}")
        return pd.DataFrame()



def merge_cart(session_id: str, customer_id: int) -> bool:
    """
    Hàm CỰC KỲ QUAN TRỌNG: Hợp nhất giỏ hàng khách vãng lai vào giỏ hàng chính thức.
    
    Xảy ra khi:
    - Khách hàng Cold-Start (khách vãng lai) đăng nhập/đăng ký thành khách hàng cũ
    - Chuyển tất cả sản phẩm từ session-based cart sang customer-based cart
    
    Logic:
    1. Tìm giỏ hàng tạm thời (session_id)
    2. Tạo/lấy giỏ hàng chính thức (customer_id)
    3. Chuyển tất cả Cart_Items từ giỏ tạm sang giỏ chính
       - Nếu sản phẩm đã tồn tại trong giỏ chính: Cộng dồn quantity
       - Nếu sản phẩm chưa tồn tại: Copy toàn bộ
    4. Xóa giỏ hàng tạm thời
    
    Args:
        session_id: ID phiên của khách vãng lai
        customer_id: ID khách hàng sau khi đăng nhập
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Bước 1: Tìm giỏ hàng tạm thời
            cursor.execute('''
                SELECT cart_id FROM Carts
                WHERE session_id = ? AND is_active = 1
            ''', (session_id,))
            
            temp_cart = cursor.fetchone()
            if not temp_cart:
                print(f"⚠️ Không tìm thấy giỏ hàng tạm thời với session_id: {session_id}")
                return False
            
            temp_cart_id = temp_cart[0]
            
            # Bước 2: Tạo/lấy giỏ hàng chính thức
            cursor.execute('''
                SELECT cart_id FROM Carts
                WHERE customer_id = ? AND is_active = 1
            ''', (customer_id,))
            
            main_cart = cursor.fetchone()
            if main_cart:
                main_cart_id = main_cart[0]
            else:
                # Tạo giỏ hàng mới
                cursor.execute('''
                    INSERT INTO Carts (customer_id, session_id, created_at, updated_at, is_active)
                    VALUES (?, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (customer_id,))
                main_cart_id = cursor.lastrowid
                print(f"✓ Tạo giỏ hàng chính thức mới: cart_id={main_cart_id}, customer_id={customer_id}")
            
            # Bước 3: Lấy danh sách sản phẩm từ giỏ tạm
            cursor.execute('''
                SELECT product_id, quantity FROM Cart_Items
                WHERE cart_id = ?
            ''', (temp_cart_id,))
            
            temp_items = cursor.fetchall()
            
            # Chuyển sản phẩm
            merged_count = 0
            for product_id, quantity in temp_items:
                # Kiểm tra sản phẩm đã tồn tại trong giỏ chính
                cursor.execute('''
                    SELECT quantity FROM Cart_Items
                    WHERE cart_id = ? AND product_id = ?
                ''', (main_cart_id, product_id))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Cộng dồn quantity
                    existing_qty = existing[0]
                    new_qty = existing_qty + quantity
                    cursor.execute('''
                        UPDATE Cart_Items
                        SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE cart_id = ? AND product_id = ?
                    ''', (new_qty, main_cart_id, product_id))
                    print(f"  → Cộng dồn quantity: product_id={product_id}, {existing_qty}+{quantity}={new_qty}")
                else:
                    # Chèn vào giỏ chính
                    cursor.execute('''
                        INSERT INTO Cart_Items (cart_id, product_id, quantity, added_at, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (main_cart_id, product_id, quantity))
                    print(f"  → Copy sản phẩm: product_id={product_id}, quantity={quantity}")
                
                merged_count += 1
            
            # Bước 4: Xóa giỏ hàng tạm (soft delete)
            cursor.execute('''
                UPDATE Carts SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE cart_id = ?
            ''', (temp_cart_id,))
            
            print(f"✓ Hợp nhất giỏ hàng thành công: {merged_count} sản phẩm từ session_id → customer_id={customer_id}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi hợp nhất giỏ hàng: {e}")
        return False


def update_quantity(cart_item_id: int, new_quantity: int) -> bool:
    """
    Cập nhật số lượng sản phẩm trong giỏ hàng.
    
    Args:
        cart_item_id: ID của mục trong giỏ hàng
        new_quantity: Số lượng mới (nếu <= 0, sản phẩm sẽ bị xóa)
    
    Returns:
        bool: True nếu thành công
    """
    if new_quantity <= 0:
        # Xóa sản phẩm nếu quantity <= 0
        return remove_from_cart(cart_item_id)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE Cart_Items
                SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cart_item_id = ?
            ''', (new_quantity, cart_item_id))
            print(f"✓ Cập nhật quantity: cart_item_id={cart_item_id}, quantity={new_quantity}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi cập nhật số lượng: {e}")
        return False


def remove_from_cart(cart_item_id: int) -> bool:
    """
    Xóa một sản phẩm khỏi giỏ hàng.
    
    Args:
        cart_item_id: ID của mục trong giỏ hàng
    
    Returns:
        bool: True nếu thành công
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM Cart_Items
                WHERE cart_item_id = ?
            ''', (cart_item_id,))
            print(f"✓ Xóa sản phẩm khỏi giỏ: cart_item_id={cart_item_id}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi xóa sản phẩm: {e}")
        return False


def clear_cart(cart_id: int) -> bool:
    """
    Xóa tất cả sản phẩm trong giỏ hàng.
    
    Args:
        cart_id: ID của giỏ hàng
    
    Returns:
        bool: True nếu thành công
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM Cart_Items
                WHERE cart_id = ?
            ''', (cart_id,))
            
            cursor.execute('''
                UPDATE Carts SET updated_at = CURRENT_TIMESTAMP
                WHERE cart_id = ?
            ''', (cart_id,))
            
            print(f"✓ Xóa tất cả sản phẩm trong giỏ: cart_id={cart_id}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi xóa tất cả sản phẩm: {e}")
        return False


def delete_cart(cart_id: int) -> bool:
    """
    Xóa giỏ hàng (soft delete: đánh dấu is_active=0).
    
    Args:
        cart_id: ID của giỏ hàng
    
    Returns:
        bool: True nếu thành công
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE Carts SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE cart_id = ?
            ''', (cart_id,))
            print(f"✓ Xóa giỏ hàng: cart_id={cart_id}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi xóa giỏ hàng: {e}")
        return False


def get_cart_summary(cart_id: int) -> Dict:
    """
    Lấy thông tin tóm tắt về giỏ hàng.
    
    Returns:
        Dict với các thông tin:
        - total_items: Tổng số sản phẩm khác nhau
        - total_quantity: Tổng số lượng sản phẩm
        - items_detail: Danh sách chi tiết sản phẩm
    """
    try:
        df = get_cart_items(cart_id)
        
        if df.empty:
            return {
                'total_items': 0,
                'total_quantity': 0,
                'items_detail': []
            }
        
        return {
            'total_items': len(df),
            'total_quantity': int(df['quantity'].sum()),
            'items_detail': df.to_dict('records')
        }
        
    except Exception as e:
        print(f"❌ Lỗi lấy thông tin tóm tắt giỏ hàng: {e}")
        return {
            'total_items': 0,
            'total_quantity': 0,
            'items_detail': []
        }


# ==================== KHỞI TẠO DATABASE KHI IMPORT ====================
# Tự động khởi tạo database nếu chưa tồn tại
if not os.path.exists(DB_PATH):
    print(f"📦 Database chưa tồn tại, đang tạo tại: {DB_PATH}")
    init_database()


# ==================== CẤU HÌNH ĐƠN HÀNG VÀ THANH TOÁN (SEPAY / VIETQR) ====================

def generate_order_id() -> str:
    """
    Sinh ngẫu nhiên mã đơn hàng dạng EMPTY_xxxxxx (ví dụ: EMPTY_A8F9D3).
    """
    import random
    import string
    # Sử dụng ký tự hoa và chữ số để tạo mã ngẫu nhiên 6 ký tự
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"EMPTY_{suffix}"


def is_order_exists(order_id: str) -> bool:
    """
    Kiểm tra xem đơn hàng đã tồn tại trong database chưa.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM Orders WHERE order_id = ?", (order_id,))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"❌ Lỗi kiểm tra đơn hàng tồn tại: {e}")
        return False


def create_order(customer_id: Optional[int], session_id: Optional[str], total_amount: int, payment_method: str, payment_status: str, items: List[Dict], order_id: Optional[str] = None) -> Optional[str]:
    """
    Tạo đơn hàng mới trong database và thêm các mặt hàng trong đơn hàng.
    
    Args:
        customer_id: ID khách hàng (nếu có)
        session_id: ID phiên khách hàng (nếu có)
        total_amount: Tổng tiền đơn hàng
        payment_method: 'COD' hoặc 'BANK_TRANSFER'
        payment_status: 'Pending', 'Paid', 'Failed'
        items: Danh sách dict, mỗi dict chứa {'product_id': int, 'quantity': int, 'price': int}
        order_id: Mã đơn hàng tùy chọn (nếu đã sinh sẵn ở UI)
        
    Returns:
        order_id: Mã đơn hàng được sinh ra, hoặc None nếu thất bại
    """
    try:
        if order_id is not None:
            if is_order_exists(order_id):
                return order_id
        else:
            # Sinh mã đơn hàng duy nhất
            for _ in range(10):
                temp_id = generate_order_id()
                if not is_order_exists(temp_id):
                    order_id = temp_id
                    break
            
            if order_id is None:
                raise ValueError("Không thể tạo mã đơn hàng duy nhất.")
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Thêm vào bảng Orders
            cursor.execute('''
                INSERT INTO Orders (order_id, customer_id, session_id, total_amount, payment_method, payment_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, customer_id, session_id, total_amount, payment_method, payment_status))
            
            # Thêm vào bảng Order_Items
            for item in items:
                cursor.execute('''
                    INSERT INTO Order_Items (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, item['product_id'], item['quantity'], item['current_price']))
                
        print(f"✓ Đã tạo đơn hàng thành công: order_id={order_id}, total={total_amount}đ")
        return order_id
    except Exception as e:
        print(f"❌ Lỗi tạo đơn hàng trong database: {e}")
        return None


def update_order_payment_status(order_id: str, payment_status: str) -> bool:
    """
    Cập nhật trạng thái thanh toán của đơn hàng.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE Orders
                SET payment_status = ?
                WHERE order_id = ?
            ''', (payment_status, order_id))
            return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Lỗi cập nhật trạng thái thanh toán đơn hàng {order_id}: {e}")
        return False


def generate_vietqr(bank_id: str, account_no: str, amount: int, order_id: str) -> str:
    """
    Tạo link ảnh mã QR VietQR miễn phí qua dịch vụ vietqr.io.
    """
    bank_id = str(bank_id).strip()
    account_no = str(account_no).strip()
    order_id = str(order_id).strip()
    
    # Template: 'compact' có kèm thông tin chuyển khoản bên dưới mã QR
    url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact.png?amount={amount}&addInfo={order_id}"
    return url


def verify_sepay_transaction(order_id: str, expected_amount: int) -> bool:
    """
    Quét lịch sử giao dịch qua SePay API để xác nhận chuyển khoản ngân hàng tự động.
    """
    import requests
    import streamlit as st
    
    try:
        # Lấy API Key từ Streamlit secrets
        sepay_api_key = st.secrets.get("SEPAY_API_KEY")
        if not sepay_api_key or sepay_api_key == "your_sepay_api_key_here":
            print("⚠️ Chưa cấu hình SEPAY_API_KEY trong .streamlit/secrets.toml")
            return False
            
        url = "https://my.sepay.vn/userapi/transactions/list"
        headers = {
            "Authorization": f"Bearer {sepay_api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Lỗi gọi API SePay: HTTP {response.status_code} - {response.text}")
            return False
            
        data = response.json()
        transactions = data.get("transactions", [])
        if not transactions and "data" in data:
            transactions = data.get("data", [])
            
        if not isinstance(transactions, list):
            print("❌ Định dạng phản hồi SePay không hợp lệ (không phải danh sách)")
            return False
            
        for tx in transactions:
            content = tx.get("transaction_content", "") or tx.get("content", "") or ""
            # Làm sạch chuỗi để so sánh (loại bỏ ký tự đặc biệt như dấu gạch dưới, khoảng trắng do ngân hàng lọc bỏ)
            clean_order_id = "".join(c for c in order_id if c.isalnum()).lower()
            clean_content = "".join(c for c in content if c.isalnum()).lower()
            
            # Kiểm tra xem mã đơn hàng có xuất hiện trong nội dung chuyển khoản không
            if clean_order_id in clean_content:
                # Tìm số tiền giao dịch
                tx_amount = 0
                for field in ["amount", "amount_in", "amountIn"]:
                    if field in tx:
                        try:
                            tx_amount = int(float(tx[field]))
                            break
                        except (ValueError, TypeError):
                            continue
                
                # Kiểm tra số tiền chuyển khoản tối thiểu
                if tx_amount >= expected_amount:
                    print(f"✓ Tìm thấy giao dịch hợp lệ: order_id={order_id}, số tiền={tx_amount}đ")
                    return True
                    
        print(f"⚠️ Chưa tìm thấy giao dịch chuyển khoản cho đơn hàng {order_id}")
        return False
    except Exception as e:
        print(f"❌ Lỗi kiểm tra giao dịch SePay: {e}")
        return False


def get_customer_orders(customer_id: Optional[int] = None, session_id: Optional[str] = None) -> List[Dict]:
    """
    Truy xuất lịch sử mua hàng của một khách hàng (hoặc theo session_id).
    Kết quả trả về danh sách các đơn hàng, mỗi đơn hàng chứa thông tin chi tiết các sản phẩm đã mua.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if customer_id is not None:
                cursor.execute('''
                    SELECT order_id, total_amount, payment_method, payment_status, created_at
                    FROM Orders
                    WHERE customer_id = ?
                    ORDER BY created_at DESC
                ''', (customer_id,))
            elif session_id is not None:
                cursor.execute('''
                    SELECT order_id, total_amount, payment_method, payment_status, created_at
                    FROM Orders
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                ''', (session_id,))
            else:
                return []
                
            orders = cursor.fetchall()
            
            result = []
            
            # Load book data to get title, category, cover_link
            book_data_path = os.path.join(APP_DIR, 'data', 'book_data.csv')
            book_df = pd.DataFrame()
            if os.path.exists(book_data_path):
                book_df = pd.read_csv(book_data_path)
                book_df = book_df.drop_duplicates(subset=['product_id'], keep='first')
            else:
                clean_path = os.path.join(APP_DIR, 'data', 'clean_book_data.csv')
                if os.path.exists(clean_path):
                    book_df = pd.read_csv(clean_path)
                    book_df = book_df.drop_duplicates(subset=['product_id'], keep='first')
            
            for order in orders:
                order_dict = dict(order)
                
                # Lấy chi tiết sản phẩm cho từng đơn hàng
                cursor.execute('''
                    SELECT oi.product_id, oi.quantity, oi.price
                    FROM Order_Items oi
                    WHERE oi.order_id = ?
                ''', (order_dict['order_id'],))
                
                items = cursor.fetchall()
                items_list = []
                
                for item in items:
                    item_dict = dict(item)
                    # Gán title, category mặc định
                    item_dict['title'] = f"Sản phẩm #{item_dict['product_id']}"
                    item_dict['category'] = "Khác"
                    item_dict['cover_link'] = ""
                    
                    if not book_df.empty:
                        matched = book_df[book_df['product_id'] == item_dict['product_id']]
                        if not matched.empty:
                            row = matched.iloc[0]
                            item_dict['title'] = str(row.get('title', item_dict['title']))
                            item_dict['category'] = str(row.get('category', item_dict['category']))
                            item_dict['cover_link'] = str(row.get('cover_link', ''))
                            
                    items_list.append(item_dict)
                    
                order_dict['items'] = items_list
                result.append(order_dict)
                
            return result
    except Exception as e:
        print(f"❌ Lỗi truy xuất lịch sử mua hàng: {e}")
        return []


