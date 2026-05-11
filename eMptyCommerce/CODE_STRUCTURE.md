# 📁 Cấu trúc Project eMpTyCommerce - Tách biệt Giao diện & Chức năng

## 📚 Hướng dẫn Tổ chức Code

Dự án đã được tách biệt thành **3 file chính** để dễ maintain và phát triển:

```
eMptyCommerce/
├── app.py                    # ⚙️ File CHÍNH - Chứa logic chức năng
├── styles.py                 # 🎨 CSS & HTML - Tất cả giao diện
├── ui_components.py          # 🧩 UI Functions - Các hàm render component
├── recommender.py            # 🤖 Mô hình gợi ý (không thay đổi)
├── preprocess.py             # 📊 Xử lý dữ liệu (không thay đổi)
├── compare_models.py         # 📈 So sánh mô hình (không thay đổi)
├── mock_implicit_data.py     # 🔄 Tạo dữ liệu (không thay đổi)
├── requirements.txt
└── data/
    ├── book_data.csv
    ├── clean_book_data.csv
    ├── clean_reviews.csv
    └── comments.csv
```

---

## 🎯 Mô tả từng File

### 1️⃣ **`app.py`** - Logic Chức Năng Chính

Chứa:

- ✅ Cấu hình Streamlit & paths
- ✅ Khởi tạo session state & data loading
- ✅ Sidebar navigation
- ✅ Các kịch bản (Cold-Start & Warm-Start)
- ✅ Gọi các hàm từ `styles.py` & `ui_components.py`

**Không chứa:**

- ❌ CSS/HTML (đã chuyển sang `styles.py`)
- ❌ Hàm render component (đã chuyển sang `ui_components.py`)

---

### 2️⃣ **`styles.py`** - Tất cả Giao Diện

Chứa **5 hàm chính:**

#### 1. `apply_header_styles()`

- Áp dụng CSS global cho header & layout
- Ẩn toolbar/header mặc định

#### 2. `render_header()`

- HTML header bar cố định (logo, badge, stats)
- Gradient nền: `#1a1a2e → #16213e → #0f3460`

#### 3. `render_category_bar()`

- Category bar cuộn ngang dưới header
- 15 danh mục với emojis

#### 4. `render_book_card()`

- Card sách với giá & rating
- Dùng cho danh mục & bestseller

#### 5. `render_book_card_hybrid()`

- Card sách cho gợi ý Hybrid/Cosine
- Hiển thị score thay vì giá

#### 6. `render_footer()`

- Footer thông tin project

---

### 3️⃣ **`ui_components.py`** - Các Hàm Render Component

Chứa **6 hàm render:**

#### 1. `render_search_bar(session_state)`

- Thanh tìm kiếm dưới header
- Lưu vào session_state

#### 2. `render_category_books_grid(books_df, DATA_DIR, cols_per_row=5)`

- Hiển thị grid sách từ danh mục
- Gọi `render_book_card()` từ styles

#### 3. `render_hybrid_recommendations_grid(recommendations_df, cols_per_row=5)`

- Hiển thị grid gợi ý Hybrid
- Gọi `render_book_card_hybrid()` từ styles

#### 4. `render_cosine_search_results_grid(similar_books_df, cols_per_row=5)`

- Hiển thị grid kết quả tìm kiếm Cosine
- Gọi `render_book_card_hybrid()` từ styles

#### 5. `render_customer_info_metrics(rated_books_count, avg_rating)`

- Hiển thị 3 metrics thông tin khách hàng
- Dùng `st.metric()`

#### 6. `render_search_result_container(final_query, ...)`

- Render container kết quả tìm kiếm ngay sau header

---

## 🔄 Cách Import & Dùng

### Trong `app.py`:

```python
from styles import apply_header_styles, render_header, render_category_bar, render_footer
from ui_components import render_search_bar, render_category_books_grid, ...

# Sử dụng
apply_header_styles()
render_header()
render_category_bar()
render_search_bar(st.session_state)
render_category_books_grid(filtered_books, DATA_DIR)
```

---

## 📝 Lợi Ích Của Cách Tổ Chức Này

| Lợi ích                      | Mô tả                                                  |
| ---------------------------- | ------------------------------------------------------ |
| 🧹 **Clean Code**            | `app.py` chỉ chứa logic chính, dễ đọc                  |
| 🎨 **Dễ Thay Đổi Giao Diện** | Sửa CSS trong `styles.py` không ảnh hưởng logic        |
| 🔄 **Tái Sử Dụng**           | Dùng các hàm từ `ui_components.py` ở nhiều nơi         |
| 🐛 **Debug Dễ Hơn**          | Lỗi UI → check `styles.py`, lỗi logic → check `app.py` |
| 📚 **Collaborate Tốt**       | Một người làm UI, một người làm logic                  |
| 🚀 **Scale Dễ Hơn**          | Thêm feature mới mà không vướng code cũ                |

---

## 🎯 Cách Thêm Feature Mới

### Ví dụ: Thêm Card Style Mới

1. **Thêm hàm vào `styles.py`:**

```python
def render_book_card_premium(title, category, cover, price, badge):
    # Render card với badge phí hạng
    return html_str
```

2. **Thêm hàm render vào `ui_components.py`:**

```python
def render_premium_books_grid(books_df):
    # Gọi render_book_card_premium()
    pass
```

3. **Dùng trong `app.py`:**

```python
from ui_components import render_premium_books_grid
render_premium_books_grid(books_df)
```

---

## ✅ Chức Năng Vẫn Giữ Nguyên

- ✅ Header + Category Bar
- ✅ Search & Cosine Similarity
- ✅ Cold-Start & Warm-Start
- ✅ TABS (Danh mục | Gợi ý | Lịch sử)
- ✅ Hybrid Recommendations
- ✅ Footer
- **100% Không thay đổi chức năng** ✨

---

## 🚀 Chạy App

```bash
cd eMptyCommerce
streamlit run app.py
```

Giao diện sẽ hoạt động **đúng như trước**, nhưng code giờ **organize tốt hơn!** 🎉
