"""
Giao diện Streamlit cho Hệ thống Gợi ý Sản phẩm Hybrid
Minh họa Cold-Start Problem & Hybrid Recommendation System
"""

import streamlit as st

# ==================== CẤU HÌNH TRANG - PHẢI LÀ LỆNH ĐẦU TIÊN ====================
st.set_page_config(
    page_title="eMpTyCommerce - Gợi ý thông minh",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== IMPORTS ====================
import pandas as pd
import numpy as np
import os
import uuid
import plotly.graph_objects as go
import psutil
from recommender import HybridRecommender
from styles import apply_header_styles, render_header, render_footer
from ui_components import (
    render_search_bar, render_category_books_grid, render_hybrid_recommendations_grid,
    render_cosine_search_results_grid, render_customer_info_metrics, 
    render_search_result_container
)
from ai_chat_widget import render_simple_floating_button
from ai_utils import init_gemini_api
from db_utils import add_to_cart, init_database, get_or_create_cart, merge_cart
from cart_ui import render_cart_sidebar, render_shopping_cart_page


# ==================== CẤU HÌNH GEMINI API ====================
GEMINI_AVAILABLE = init_gemini_api()


# ==================== HÀM ĐO LƯỜNG RAM ====================
def get_current_ram_mb():
    """
    Tính toán lượng RAM tiến trình hiện tại đang chiếm dụng (đơn vị MB).
    Sử dụng thư viện psutil để lấy số liệu chính xác.
    """
    process = psutil.Process(os.getpid())
    ram_info = process.memory_info()
    ram_mb = ram_info.rss / (1024 * 1024)  # Chuyển từ bytes sang MB
    return ram_mb


# ==================== BIẾN TOÀN CỤC LƯU CHECKPOINT ====================
checkpoint_1_ram = None  # RAM tại Checkpoint 1 (Idle)
checkpoint_2_ram = None  # RAM tại Checkpoint 2 (Sau load data)
checkpoint_3_ram = None  # RAM tại Checkpoint 3 (Sau gọi hàm gợi ý)

# Lấy đường dẫn của thư mục app hiện tại
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')


# ==================== CẤU HÌNH HEADER & STYLES ====================
# Khởi tạo session_state cho tìm kiếm
if 'search_query' not in st.session_state:
    st.session_state.search_query = ''
if 'do_search' not in st.session_state:
    st.session_state.do_search = False
if 'last_input' not in st.session_state:
    st.session_state.last_input = ''
if 'search_source_book' not in st.session_state:
    st.session_state.search_source_book = None
if 'search_similar_books' not in st.session_state:
    st.session_state.search_similar_books = None
if 'search_error' not in st.session_state:
    st.session_state.search_error = None

# Đọc query params để giữ lựa chọn sau khi reload
query_params = st.query_params
saved_customer_type = query_params.get("customer_type")
saved_customer_id = query_params.get("customer_id")

# Khởi tạo session_state cho loại khách hàng
if 'customer_type' not in st.session_state:
    if saved_customer_type in ["👥 Khách hàng cũ", "🆕 Khách hàng mới (Cold-Start)"]:
        st.session_state.customer_type = saved_customer_type
    else:
        st.session_state.customer_type = "🆕 Khách hàng mới (Cold-Start)"

# ==================== KHỞI TẠO SESSION STATE CHO CHAT AI ====================
# Lịch sử cuộc trò chuyện với AI Trợ lý tư vấn sách
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Ghi nhận ID khách hàng hiện tại để detect khi người dùng thay đổi
if 'current_customer_id' not in st.session_state:
    if saved_customer_id and str(saved_customer_id).isdigit():
        st.session_state.current_customer_id = int(saved_customer_id)
    else:
        st.session_state.current_customer_id = None

# ==================== KHỞI TẠO SESSION STATE CHO SHOPPING CART ====================
# Khởi tạo session_id cho Cold-Start users
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Khởi tạo database
if 'db_initialized' not in st.session_state:
    init_database()
    st.session_state.db_initialized = True

# Khởi tạo cart_id dựa trên loại khách hàng
if 'cart_id' not in st.session_state:
    st.session_state.cart_id = get_or_create_cart(session_id=st.session_state.session_id)

# View mặc định cho giao diện
if 'view' not in st.session_state:
    st.session_state.view = "shopping"

if 'last_merged_customer_id' not in st.session_state:
    st.session_state.last_merged_customer_id = None

if 'cold_recommendations' not in st.session_state:
    st.session_state.cold_recommendations = None
if 'cold_reference_id' not in st.session_state:
    st.session_state.cold_reference_id = None


def handle_add_to_cart(product_id: int, title: str = ""):
    if st.session_state.customer_type == "🆕 Khách hàng mới (Cold-Start)":
        st.warning("🔒 Vui lòng chọn 'Khách hàng cũ' và đăng nhập bằng ID để thêm vào giỏ hàng.")
        return
    add_to_cart(st.session_state.cart_id, product_id, 1)
    if title:
        st.success(f"✅ Đã thêm '{title[:30]}...' vào giỏ hàng")
    else:
        st.success("✅ Đã thêm vào giỏ hàng")

# Cache gợi ý Warm-Start để không mất sau khi bấm nút khác
if 'warm_recommendations' not in st.session_state:
    st.session_state.warm_recommendations = None

# Lưu trạng thái Gemini API vào session_state
st.session_state.gemini_available = GEMINI_AVAILABLE

# Áp dụng CSS styles
apply_header_styles()

# Render search bar
render_search_bar(st.session_state)


# ==================== CHECKPOINT 1: ĐO RAM - TRẠNG THÁI IDLE BAN ĐẦU ====================
checkpoint_1_ram = get_current_ram_mb()
print(f"\n[ĐO RAM] ===== CHECKPOINT 1: TRẠNG THÁI IDLE BAN ĐẦU =====")
print(f"[ĐO RAM] Sau khi ứng dụng vừa khởi động: {checkpoint_1_ram:.2f} MB")
print(f"[ĐO RAM] =====================================================\n")


# ==================== CACHE RESOURCE ====================
# Khởi tạo HybridRecommender 1 lần duy nhất (tránh load lại mô hình)
@st.cache_resource
def load_recommender_model():
    """
    Load mô hình HybridRecommender một lần duy nhất.
    Streamlit sẽ cache kết quả để tránh phải huấn luyện lại model mỗi lần reload.
    """
    # Thay đổi thư mục làm việc để đảm bảo load dữ liệu đúng
    original_cwd = os.getcwd()
    os.chdir(APP_DIR)
    try:
        model = HybridRecommender()
    finally:
        os.chdir(original_cwd)
    return model


@st.cache_resource
def load_book_data():
    """
    Load dữ liệu sách từ clean_book_data.csv.
    Cache để tránh đọc file liên tục.
    """
    try:
        return pd.read_csv(os.path.join(DATA_DIR, 'clean_book_data.csv'))
    except FileNotFoundError:
        st.error(f"❌ Không tìm thấy file {os.path.join(DATA_DIR, 'clean_book_data.csv')}")
        return None


@st.cache_resource
def load_reviews_data():
    """
    Load dữ liệu đánh giá từ clean_reviews.csv.
    Cache để tránh đọc file liên tục.
    """
    try:
        return pd.read_csv(os.path.join(DATA_DIR, 'clean_reviews.csv'))
    except FileNotFoundError:
        st.error(f"❌ Không tìm thấy file {os.path.join(DATA_DIR, 'clean_reviews.csv')}")
        return None


@st.cache_data
def get_book_reviews_data(book_id: int) -> list[dict]:
    """
    Đọc dữ liệu comments từ comments.csv và lọc theo product_id (book_id).
    """
    try:
        comments_path = os.path.join(DATA_DIR, 'comments.csv')
        if not os.path.exists(comments_path):
            return []
        df_comments = pd.read_csv(comments_path)
        # Lọc các bình luận của book_id này
        df_book = df_comments[df_comments['product_id'] == book_id]
        
        # Chuyển đổi thành list[dict]
        reviews_list = []
        for _, row in df_book.iterrows():
            reviews_list.append({
                "ma_kh": str(row.get("customer_id", "Ẩn danh")),
                "so_sao": int(row.get("rating", 5)),
                "tieu_de": row.get("title") if pd.notna(row.get("title")) else None,
                "noi_dung": row.get("content") if pd.notna(row.get("content")) else None,
                "ngay": None  # File CSV comments không có cột ngày
            })
        return reviews_list
    except Exception as e:
        print(f"Lỗi khi đọc comments.csv: {e}")
        return []



@st.cache_data
def get_bestseller(top_n=10):
    """
    Load từ book_data.csv (có đủ n_review, avg_rating)
    Tính sách bán chạy nhất dựa trên Bayesian Average.
    
    Công thức:
    Score = (n_review / (n_review + m)) * avg_rating + (m / (n_review + m)) * C
    
    Trong đó:
    - n_review: Số lượt đánh giá
    - avg_rating: Điểm đánh giá trung bình
    - m: Số đánh giá tối thiểu (quantile 60%) để được xét
    - C: Điểm trung bình của tất cả sách
    
    Lợi ích: Tránh bias cho sách ít review nhưng toàn 5 sao
    """
    try:
        # Load từ book_data.csv (có cột n_review, avg_rating)
        df = pd.read_csv(os.path.join(DATA_DIR, 'book_data.csv'))
        
        # Xóa duplicate product_id, giữ lại 1 dòng mỗi sách
        df = df.drop_duplicates(subset='product_id')
        
        # Xóa dòng thiếu dữ liệu quan trọng
        df = df.dropna(subset=['n_review', 'avg_rating', 'title'])
        
        # Xác định số lượt đánh giá tối thiểu (quantile 60%)
        m = df['n_review'].quantile(0.6)
        
        # Điểm trung bình của toàn bộ sách
        C = df['avg_rating'].mean()
        
        # Tính Bayesian Average Score
        df['bestseller_score'] = (
            (df['n_review'] / (df['n_review'] + m)) * df['avg_rating'] +
            (m / (df['n_review'] + m)) * C
        )
        
        # Lọc sách có đủ lượt đánh giá
        popular = df[df['n_review'] >= m]
        
        # Lấy top N sách có score cao nhất
        return popular.nlargest(top_n, 'bestseller_score')
    
    except Exception as e:
        print(f"⚠️ Không thể tải danh sách sách bán chạy: {e}")
        return pd.DataFrame()


# ==================== KHỞI TẠO DỮ LIỆU ====================
with st.spinner("⏳ Đang tải mô hình và dữ liệu..."):
    recommender = load_recommender_model()
    book_data = load_book_data()
    reviews_data = load_reviews_data()

# Kiểm tra dữ liệu
if book_data is None or reviews_data is None:
    st.error("❌ Lỗi: Không thể tải dữ liệu. Vui lòng kiểm tra file trong thư mục data/")
    st.stop()

# Render header với số liệu thực tế
render_header(
    n_books=len(book_data),
    n_customers=reviews_data['customer_id'].nunique()
)


# ==================== CHECKPOINT 2: ĐO RAM - SAU KHI LOAD DỮ LIỆU & NẠP MÔ HÌNH ====================
checkpoint_2_ram = get_current_ram_mb()
checkpoint_2_increase = checkpoint_2_ram - checkpoint_1_ram
print(f"\n[ĐO RAM] ===== CHECKPOINT 2: SAU KHI LOAD DỮ LIỆU & NẠP MÔ HÌNH =====")
print(f"[ĐO RAM] Sau khi Load Model và Dữ liệu: {checkpoint_2_ram:.2f} MB")
print(f"[ĐO RAM] Tăng thêm so với Checkpoint 1: {checkpoint_2_increase:.2f} MB")
print(f"[ĐO RAM] ================================================================\n")

# Danh sách khách hàng duy nhất
unique_customers = sorted(reviews_data['customer_id'].unique().tolist())
customer_dict = {cid: f"Customer {cid}" for cid in unique_customers}

# Danh sách sách với product_id
book_dict = {row['product_id']: row['title'] for _, row in book_data.iterrows()}


# ==================== SIDEBAR - THANH ĐIỀU HƯỚNG ====================
with st.sidebar:
    # Compact HTML banner instead of st.title
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 12px 16px; border-radius: 8px; text-align: center; margin-bottom: 16px;">
        <h3 style="margin: 0; color: white; font-size: 18px;">🎯 eMpTyCommerce</h3>
        <p style="margin: 4px 0 0 0; color: #b0b0b0; font-size: 12px;">Hệ thống gợi ý thông minh</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Collapsed project info (Thesis + Student info)
    with st.expander("ℹ️ Thông tin dự án", expanded=False):
        st.caption("**Đề tài:** Nghiên cứu và xây dựng hệ thống gợi ý sản phẩm thương mại điện tử dựa trên mô hình lai (Hybrid) kết hợp đặc trưng nội dung và tương tác người dùng")
        st.caption("**Phương pháp:** Hybrid Model (Content-Based + Collaborative Filtering)")
        st.caption("**Mô hình:** TF-IDF + SVD")
        st.divider()
        st.caption("**Sinh viên:** Đào Minh Tới")
        st.caption("**Giáo viên hướng dẫn:** ThS. Bùi Thị Diễm Trinh")
    
    st.markdown("---")
    
    # Callback để reset thanh tìm kiếm khi thay đổi kịch bản
    def reset_search_on_customer_type_change():
        st.session_state.search_query = ''
        st.session_state.do_search = False
        st.session_state.last_input = ''
        st.session_state.search_source_book = None
        st.session_state.search_similar_books = None
        st.session_state.search_error = None
        # ==================== XÓA CHAT KHI ĐỔI KỊCH BẢN ====================
        st.session_state.messages = []
        st.session_state.current_customer_id = None
        st.session_state.warm_recommendations = None
        st.session_state["selected_book_for_reviews"] = None
        if "tab_category_select" in st.session_state:
            st.session_state["tab_category_select"] = "Tất cả"
    
    # Scenario selection - cleaner label
    st.markdown("**🎯 Chọn kịch bản**")
    customer_type = st.radio(
        "Loại khách hàng:",
        ["👥 Khách hàng cũ", "🆕 Khách hàng mới (Cold-Start)"],
        index=["👥 Khách hàng cũ", "🆕 Khách hàng mới (Cold-Start)"].index(
            st.session_state.customer_type
        ),
        key="customer_type_radio",
        on_change=reset_search_on_customer_type_change,
        label_visibility="collapsed"
    )
    
    st.session_state.customer_type = customer_type

    def sync_query_params():
        params = {"customer_type": st.session_state.customer_type}
        if st.session_state.customer_type == "👥 Khách hàng cũ" and st.session_state.current_customer_id is not None:
            params["customer_id"] = str(st.session_state.current_customer_id)
        st.query_params.clear()
        for key, value in params.items():
            st.query_params[key] = value
    
    if customer_type == "👥 Khách hàng cũ":
        # ==================== CALLBACK KHI ĐỔI CUSTOMER ID ====================
        def on_customer_change():
            new_customer_id = st.session_state.get("customer_selectbox")
            if new_customer_id != st.session_state.current_customer_id:
                st.session_state.messages = []
                st.session_state.current_customer_id = new_customer_id
                
                # Reset trạng thái tìm kiếm khi đổi ID Khách hàng
                st.session_state.search_query = ''
                st.session_state.do_search = False
                st.session_state.last_input = ''
                st.session_state.search_source_book = None
                st.session_state.search_similar_books = None
                st.session_state.search_error = None
                
                # Reset các bộ lọc và gợi ý của người dùng cũ
                st.session_state.warm_recommendations = None
                st.session_state["selected_book_for_reviews"] = None
                if "tab_category_select" in st.session_state:
                    st.session_state["tab_category_select"] = "Tất cả"
                
                if st.session_state.last_merged_customer_id != new_customer_id:
                    merge_cart(st.session_state.session_id, new_customer_id)
                    st.session_state.last_merged_customer_id = new_customer_id
                st.session_state.cart_id = get_or_create_cart(customer_id=new_customer_id)
            sync_query_params()
        
        # Xác định index mặc định để giữ phiên đăng nhập khi reload
        default_index = 0
        if st.session_state.get("current_customer_id") in unique_customers:
            default_index = unique_customers.index(st.session_state.current_customer_id)

        selected_customer = st.selectbox(
            "🔑 Đăng nhập với ID Khách hàng:",
            unique_customers,
            index=default_index,
            format_func=lambda x: customer_dict[x],
            key="customer_selectbox",
            on_change=on_customer_change
        )
        
        # Cập nhật current_customer_id
        st.session_state.current_customer_id = selected_customer
        if st.session_state.last_merged_customer_id != selected_customer:
            merge_cart(st.session_state.session_id, selected_customer)
            st.session_state.last_merged_customer_id = selected_customer
        st.session_state.cart_id = get_or_create_cart(customer_id=selected_customer)
    else:
        selected_customer = None
        st.session_state.current_customer_id = None
        st.session_state.cart_id = get_or_create_cart(session_id=st.session_state.session_id)

    sync_query_params()
    
    st.markdown("---")
    
    # Data statistics with cleaner layout
    st.caption("📊 Thống kê dữ liệu")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sách", len(book_data))
        st.metric("Đánh giá", len(reviews_data))
    with col2:
        st.metric("Khách hàng", reviews_data['customer_id'].nunique())
        st.metric("Trung bình", f"{reviews_data['rating'].mean():.2f}")
    
    st.markdown("---")
    
    # Model analysis section
    st.caption("🔬 Phân tích mô hình")
    if st.button("Xem so sánh hiệu năng 4 mô hình", use_container_width=True):
        with st.spinner("⏳ Đang tính toán RMSE và MAE cho các mô hình..."):
            try:
                # Import hàm so sánh mô hình
                from compare_models import create_comparison_table
                
                # Chuyển thư mục làm việc để đảm bảo load dữ liệu đúng
                original_cwd = os.getcwd()
                os.chdir(APP_DIR)
                
                try:
                    # Lấy bảng so sánh
                    df_compare, rmse_knn, mae_knn, rmse_cf, rmse_hybrid, mae_cf, mae_hybrid = create_comparison_table()
                    
                    # Hiển thị kết quả trong modal/expanded
                    st.session_state.show_comparison = True
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                st.error(f"❌ Lỗi khi tính toán: {str(e)}")
    
    # Implicit Feedback explanation expander
    with st.expander("📘 Implicit Feedback là gì?", expanded=False):
        st.caption(
            "Implicit Feedback là hành vi người dùng không trực tiếp cho điểm mà hệ thống "
            "tự quy đổi thành rating để huấn luyện mô hình."
        )
        
        st.markdown("""
<table style="width:100%;font-size:11px;border-collapse:collapse;">
  <thead>
    <tr style="background:#1a1a2e;color:white;">
      <th style="padding:6px 4px;text-align:left;">Hành vi</th>
      <th style="padding:6px 4px;text-align:center;">Rating</th>
      <th style="padding:6px 4px;text-align:left;">Ý nghĩa</th>
    </tr>
  </thead>
  <tbody>
    <tr style="border-bottom:1px solid #eee;">
      <td style="padding:6px 4px;">🛒 Mua hàng</td>
      <td style="padding:6px 4px;text-align:center;color:#f39c12;">★★★★★</td>
      <td style="padding:6px 4px;">Yêu thích</td>
    </tr>
    <tr style="border-bottom:1px solid #eee;">
      <td style="padding:6px 4px;">🛍️ Thêm giỏ</td>
      <td style="padding:6px 4px;text-align:center;color:#f39c12;">★★★</td>
      <td style="padding:6px 4px;">Quan tâm</td>
    </tr>
    <tr>
      <td style="padding:6px 4px;">👁️ Click xem</td>
      <td style="padding:6px 4px;text-align:center;color:#f39c12;">★</td>
      <td style="padding:6px 4px;">Tò mò</td>
    </tr>
  </tbody>
</table>
""", unsafe_allow_html=True)
        
        st.caption(
            "Dữ liệu thực tế từ Tiki thường thiếu rating rõ ràng. Hệ thống quy đổi "
            "hành vi ẩn thành điểm số để SVD có thể học được mô hình khuyến nghị."
        )


# ==================== SIDEBAR CART (COMPACT) ====================
render_cart_sidebar(st.session_state.cart_id)


# ==================== CART VIEW ====================
if st.session_state.view == "cart":
    render_shopping_cart_page(st.session_state.cart_id, book_data)
    render_footer()
    st.stop()


# ==================== CHECKOUT VIEW ====================
if st.session_state.view == "checkout":
    from cart_ui import render_checkout_page
    render_checkout_page(st.session_state.cart_id, book_data)
    render_footer()
    st.stop()



# ==================== MAIN CONTENT ====================
st.title("🎯 Hệ thống Gợi ý Sản phẩm Thương mại Điện tử")
st.markdown(
    "**Giải pháp:** Hybrid Model kết hợp Content-Based & Collaborative Filtering "
    "để xử lý Cold-Start Problem"
)
st.markdown("---")

# ========== KHỐI HIỂN THỊ ĐÁNH GIÁ CHI TIẾT KHI CLICK "XEM ĐÁNH GIÁ" ==========
reviews_placeholder = st.empty()

if st.session_state.get("selected_book_for_reviews") is not None:
    view_book_id = st.session_state["selected_book_for_reviews"]
    
    # Lấy thông tin sách
    matching_books = book_data[book_data['product_id'] == view_book_id]
    if not matching_books.empty:
        sel_book = matching_books.iloc[0]
        
        with reviews_placeholder.container():
            # Tự động cuộn lên đầu trang nếu cờ được bật
            if st.session_state.get("should_scroll_to_top", False):
                import streamlit.components.v1 as components
                components.html(
                    """
                    <script>
                        try {
                            const mainContainer = window.parent.document.querySelector('.main');
                            if (mainContainer) {
                                mainContainer.scrollTo({top: 0, behavior: 'smooth'});
                            } else {
                                window.parent.scrollTo({top: 0, behavior: 'smooth'});
                            }
                        } catch (e) {
                            console.error("Scroll error:", e);
                        }
                    </script>
                    """,
                    height=0,
                    width=0
                )
                st.session_state["should_scroll_to_top"] = False

            # Hộp chứa thông tin sách đang được xem đánh giá
            st.markdown(f"""
            <div style="background: rgba(245, 166, 35, 0.1); border: 2px solid #f5a623; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #f5a623; display: flex; align-items: center; gap: 8px;">
                    <span>📖 Chi tiết đánh giá sách</span>
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            col_img, col_info, col_close = st.columns([1, 4, 1])
            with col_img:
                if pd.notna(sel_book['cover_link']) and sel_book['cover_link'] != '':
                    st.image(sel_book['cover_link'], use_container_width=True)
                else:
                    st.image("https://picsum.photos/200/300?random=99", use_container_width=True)
            with col_info:
                st.markdown(f"### {sel_book['title']}")
                st.markdown(f"📂 **Thể loại:** {sel_book['category']}")
            with col_close:
                if st.button("✕ Đóng", key="close_selected_reviews", use_container_width=True):
                    st.session_state["selected_book_for_reviews"] = None
                    st.rerun()
                    
            st.markdown("---")
            # Gọi hàm hiển thị đánh giá
            from ui_components import show_book_reviews
            book_reviews = get_book_reviews_data(view_book_id)
            show_book_reviews(view_book_id, book_reviews)
            st.markdown("<hr style='border: 1.5px solid #f5a623; margin: 30px 0;'>", unsafe_allow_html=True)

# ========== HIỂN THỊ KẾT QUẢ TÌM KIẾM NGAY SAU HEADER ==========
search_result_container = st.container()

if st.session_state.get('do_search') and st.session_state.get('search_query'):
    final_query = st.session_state.search_query
    st.session_state.do_search = False

    # Ứng dụng cosine similarity từ model Đã tải
    from sklearn.metrics.pairwise import cosine_similarity
    
    def find_similar_books(query_title, top_n=5):
        """
        Tìm sách tương tự dựa trên TF-IDF từ recommender module.
        Đảm bảo kết quả consistent với Content-Based model.
        """
        book_df = recommender.book_data
        tfidf_matrix = recommender.tfidf_matrix
        
        query_lower = query_title.lower().strip()
        matches = book_df[book_df['title'].str.lower().str.contains(query_lower, na=False)]
        
        if matches.empty:
            return None, None, "Không tìm thấy sách có tên phù hợp. Thử nhập tên khác!"
        
        source_book = matches.iloc[0]
        source_idx = matches.index[0]
        source_vec = tfidf_matrix[source_idx]
        cos_scores = cosine_similarity(source_vec, tfidf_matrix).flatten()
        similar_indices = np.argsort(cos_scores)[::-1]
        similar_indices = [i for i in similar_indices if i != source_idx][:top_n]
        results = book_df.iloc[similar_indices].copy()
        results['cosine_score'] = cos_scores[similar_indices]
        return source_book, results, None
    
    with st.spinner(f"Đang tìm sách tương tự với '{final_query}'..."):
        source_book, similar_books, error = find_similar_books(final_query, top_n=5)
        st.session_state.search_source_book = source_book
        st.session_state.search_similar_books = similar_books
        st.session_state.search_error = error

# Render kết quả tìm kiếm nếu đã được lưu trong session_state
if st.session_state.get('search_similar_books') is not None or st.session_state.get('search_error') is not None:
    with search_result_container:
        error = st.session_state.search_error
        if error:
            st.warning(f"⚠️ {error}")
        else:
            source_book = st.session_state.search_source_book
            similar_books = st.session_state.search_similar_books
            
            st.success(f"✅ Tìm thấy sách: **{source_book['title']}**")
            st.markdown(f"📂 Danh mục: *{source_book.get('category','N/A')}*")
            st.markdown("##### 📚 5 sách có nội dung tương tự nhất:")
            cols = st.columns(5)
            for i, (_, book) in enumerate(similar_books.iterrows()):
                with cols[i]:
                    title    = str(book.get('title','N/A'))
                    category = str(book.get('category','N/A'))
                    score    = float(book.get('cosine_score', 0))
                    cover    = book.get('cover_link','')
                    product_id = book.get('product_id', book.get('id'))
                    short_title = (title[:40]+'...') if len(title)>40 else title
                    if pd.notna(cover) and str(cover).startswith('http'):
                        img_html = f'<img src="{cover}" style="width:100%;height:200px;object-fit:cover;border-radius:8px 8px 0 0;">'
                    else:
                        img_html = '<div style="width:100%;height:200px;background:#f0f0f0;border-radius:8px 8px 0 0;display:flex;align-items:center;justify-content:center;font-size:36px;">📚</div>'
                    st.markdown(f"""
                    <div style="border:1px solid #e0e0e0;border-radius:12px;overflow:hidden;
                                box-shadow:0 2px 8px rgba(0,0,0,0.08);background:white;
                                margin-bottom:8px;text-align:center;">
                        {img_html}
                        <div style="padding:10px;">
                            <div style="font-size:12px;font-weight:600;color:#1a1a2e;
                                        min-height:36px;line-height:1.4;margin-bottom:4px;">
                                {short_title}
                            </div>
                            <div style="font-size:11px;color:#6c757d;font-style:italic;
                                        margin-bottom:8px;">📂 {category[:25]}</div>
                            <div style="border-top:1px solid #f0f0f0;padding-top:8px;">
                                <div style="font-size:22px;font-weight:700;color:#6C63FF;">
                                    {score*100:.1f}%
                                </div>
                                <div style="font-size:10px;color:#999;">
                                    Độ tương đồng Cosine
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🛒 Thêm", key=f"search_cart_{i}_{product_id}", use_container_width=True):
                            handle_add_to_cart(product_id, title)
                    with col_btn2:
                        if st.button("💬 Review", key=f"search_rev_{i}_{product_id}", use_container_width=True):
                            st.session_state["selected_book_for_reviews"] = product_id
                            st.session_state["should_scroll_to_top"] = True
                            st.rerun()
            st.markdown("---")


# ============ HIỂN THỊ BẢNG SO SÁNH NẾU CÓ YÊU CẦU ============
if st.session_state.get("show_comparison", False):
    from compare_models import create_comparison_table
    
    original_cwd = os.getcwd()
    os.chdir(APP_DIR)
    
    try:
        # Tạo header với nút đóng
        col_title, col_close = st.columns([20, 1])
        with col_title:
            st.subheader("📊 So sánh hiệu năng các mô hình")
        with col_close:
            if st.button("✕", key="close_comparison_btn", help="Đóng bảng so sánh"):
                st.session_state.show_comparison = False
                st.rerun()
        
        df_compare, rmse_knn, mae_knn, rmse_cf, rmse_hybrid, mae_cf, mae_hybrid = create_comparison_table()
        
        st.dataframe(df_compare, hide_index=True, use_container_width=True)
        
        st.caption("💡 **Giải thích:**")
        st.caption("- **RMSE** thấp hơn = dự đoán chính xác hơn")
        st.caption("- **MAE** (Mean Absolute Error) = trung bình sai số tuyệt đối")
        st.caption("- **Content-Based** không có RMSE vì không dùng rating mà dùng similarity")
        st.caption("- **KNN Item-based** gợi ý dựa trên sản phẩm tương tự")
        st.caption("- **SVD** (Collaborative Filtering) gợi ý dựa trên người dùng tương tự")
        st.caption("- **Hybrid** kết hợp Content-Based (40%) + SVD (60%)")
        
        # Model comparison charts using Plotly
        col1, col2 = st.columns(2)
        
        # Left chart - RMSE Comparison
        with col1:
            models = ["Content-Based", "KNN", "SVD", "Hybrid"]
            rmse_values = [0, rmse_knn, rmse_cf, rmse_hybrid]
            rmse_colors = ["#95a5a6", "#3498db", "#2ecc71", "#e67e22"]
            
            fig_rmse = go.Figure(data=[
                go.Bar(
                    x=models,
                    y=rmse_values,
                    marker_color=rmse_colors,
                    text=[
                        "N/A",
                        f"{rmse_knn:.4f}",
                        f"🏆 {rmse_cf:.4f}",
                        f"✓ {rmse_hybrid:.4f}"
                    ],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>RMSE: %{y:.4f}<extra></extra>"
                )
            ])
            
            fig_rmse.update_layout(
                title="📊 So sánh RMSE (thấp hơn = tốt hơn)",
                xaxis_title="Mô hình",
                yaxis_title="RMSE",
                showlegend=False,
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
                height=400
            )
            
            st.plotly_chart(fig_rmse, use_container_width=True)
        
        # Right chart - MAE Comparison
        with col2:
            mae_values = [0, mae_knn, mae_cf, mae_hybrid]
            mae_colors = ["#95a5a6", "#3498db", "#2ecc71", "#e67e22"]
            
            fig_mae = go.Figure(data=[
                go.Bar(
                    x=models,
                    y=mae_values,
                    marker_color=mae_colors,
                    text=[
                        "N/A",
                        f"🏆 {mae_knn:.4f}",
                        f"{mae_cf:.4f}",
                        f"{mae_hybrid:.4f}"
                    ],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>MAE: %{y:.4f}<extra></extra>"
                )
            ])
            
            fig_mae.update_layout(
                title="📊 So sánh MAE (thấp hơn = tốt hơn)",
                xaxis_title="Mô hình",
                yaxis_title="MAE",
                showlegend=False,
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
                height=400
            )
            
            st.plotly_chart(fig_mae, use_container_width=True)
        
        # Explanation about Hybrid trade-off
        st.info(
            "💡 **Hybrid có RMSE cao hơn SVD nhưng là mô hình duy nhất giải quyết được Cold-Start Problem** — "
            "gợi ý cho người dùng mới chưa có lịch sử đánh giá. Đây là ưu tiên hàng đầu trong "
            "thực tế TMĐT Việt Nam với tỷ lệ người dùng mới cao."
        )
        
        st.markdown("---")
    
    finally:
        os.chdir(original_cwd)


# ============ KỊCH BẢN A: KHÁCH HÀNG MỚI (COLD-START) ============
if customer_type == "🆕 Khách hàng mới (Cold-Start)":
    st.header("🆕 Kịch bản: Khách hàng mới (Cold-Start)")
    
    # Thông báo
    st.info(
        "🔄 **Hệ thống nhận diện:** Đây là người dùng mới (chưa có lịch sử đánh giá)\n\n"
        "→ Tự động chuyển sang mô hình **Content-Based Filtering 100%**\n\n"
        "→ Gợi ý dựa trên **sách bạn đang quan tâm**"
    )
    
    # Chọn sách tham chiếu
    st.subheader("📖 Bước 1: Chọn cuốn sách bạn đang quan tâm")
    selected_book_id = st.selectbox(
        "Chọn quyển sách:",
        book_data['product_id'].tolist(),
        format_func=lambda x: book_dict.get(x, f"Sách {x}"),
        key="cold_start_book"
    )
    
    # Tự động reset nếu người dùng đổi sách tham chiếu ở Bước 1
    if st.session_state.get('cold_reference_id') is not None and st.session_state.cold_reference_id != selected_book_id:
        st.session_state.cold_recommendations = None
        st.session_state.cold_reference_id = None
    
    # Lấy thông tin sách được chọn
    selected_book = book_data[book_data['product_id'] == selected_book_id].iloc[0]
    
    st.subheader("📚 Sách bạn đang xem:")
    col1, col2, col3 = st.columns([2, 3, 5])
    
    with col1:
        # Hiển thị hình ảnh bìa sách
        if pd.notna(selected_book['cover_link']) and selected_book['cover_link'] != '':
            st.image(selected_book['cover_link'], use_container_width=True)
        else:
            st.image("https://picsum.photos/200/300?random=1", use_container_width=True)
    
    with col2:
        st.write(f"**Tên sách:** {selected_book['title']}")
        st.write(f"**Thể loại:** {selected_book['category']}")
    
    with col3:
        st.write("")  # Khoảng trống

    # Hiển thị đánh giá và bình luận của sách đang xem khi người dùng click expander
    with st.expander("💬 Xem đánh giá từ khách hàng của sách này", expanded=False):
        from ui_components import show_book_reviews
        book_reviews = get_book_reviews_data(selected_book_id)
        show_book_reviews(selected_book_id, book_reviews)
    st.markdown("---")
    
    # Nút lấy gợi ý
    if st.button("🔍 Lấy gợi ý sách tương tự", key="btn_cold_start"):
        with st.spinner("⏳ Đang tính toán gợi ý dựa trên Content-Based Filtering..."):
            try:
                recommendations = recommender.get_content_based_recommendations(
                    selected_book_id,
                    top_n=10
                )
                
                # ==================== CHECKPOINT 3: ĐO RAM - SAU GỌI HÀM DỰ ĐOÁN/GỢI Ý ====================
                checkpoint_3_ram = get_current_ram_mb()
                checkpoint_3_increase = checkpoint_3_ram - checkpoint_2_ram
                print(f"\n[ĐO RAM] ===== CHECKPOINT 3: SAU KHI GỌI HÀM DỰ ĐOÁN/GỢI Ý (Content-Based) =====")
                print(f"[ĐO RAM] Sau khi tính toán TF-IDF và Cosine Similarity: {checkpoint_3_ram:.2f} MB")
                print(f"[ĐO RAM] Tăng thêm so với Checkpoint 2: {checkpoint_3_increase:.2f} MB")
                print(f"[ĐO RAM] Tổng tăng từ lúc khởi động: {checkpoint_3_ram - checkpoint_1_ram:.2f} MB")
                print(f"[ĐO RAM] ============================================================================\n")
                
                st.session_state.cold_recommendations = recommendations
                st.session_state.cold_reference_id = selected_book_id
                
            except Exception as e:
                st.error(f"❌ Chi tiết lỗi: {repr(e)}")
    
    # Hiển thị gợi ý nếu đã có trong session_state
    if st.session_state.get('cold_recommendations') is not None:
        recommendations = st.session_state.cold_recommendations
        if recommendations.empty:
            st.warning("⚠️ Không tìm thấy sách tương tự")
        else:
            st.success(f"✅ Tìm thấy {len(recommendations)} cuốn sách tương tự!")
            
            # CSS custom cho card sách
            st.markdown("""
            <style>
            .book-card {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                height: 100%;
                text-align: center;
            }
            .book-card img {
                border-radius: 8px;
                width: 100%;
                object-fit: cover;
                height: 200px;
            }
            .book-title {
                font-size: 13px;
                font-weight: 600;
                color: #1a1a2e;
                margin-top: 10px;
                margin-bottom: 4px;
                line-height: 1.4;
                min-height: 36px;
            }
            .book-category {
                font-size: 11px;
                color: #6c757d;
                font-style: italic;
                margin-bottom: 6px;
            }
            .book-score {
                font-size: 22px;
                font-weight: 700;
                color: #4CAF50;
                margin: 6px 0;
            }
            .book-score-label {
                font-size: 10px;
                color: #999;
                margin-top: -4px;
            }
            .divider-card {
                border-top: 1px solid #f0f0f0;
                margin: 8px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.subheader("📚 Bước 2: Sách được gợi ý dựa trên nội dung tương tự")
            st.caption(f"Tìm thấy {len(recommendations)} sách có nội dung tương tự · Mô hình: Content-Based (TF-IDF + Cosine Similarity)")
            
            # Hiển thị 5 card mỗi hàng
            COLS_PER_ROW = 5
            rec_list = recommendations.reset_index(drop=True)
            
            for row_start in range(0, len(rec_list), COLS_PER_ROW):
                row_data = rec_list.iloc[row_start:row_start+COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                for i, (_, book) in enumerate(row_data.iterrows()):
                    with cols[i]:
                        # Lấy thông tin
                        title    = str(book.get('title', 'N/A'))
                        category = str(book.get('category', 'N/A'))
                        score    = book.get('similarity_score', book.get('score', 0))
                        cover    = book.get('cover_link', '')
                        product_id = book.get('product_id', book.get('id'))
                        short_title = (title[:45] + '...') if len(title) > 45 else title
                    
                        # Ảnh bìa
                        if pd.notna(cover) and str(cover).startswith('http'):
                            img_html = f'<img src="{cover}" style="width:100%;height:180px;object-fit:cover;border-radius:8px;">'
                        else:
                            img_html = '<div style="width:100%;height:180px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:40px;">📚</div>'
                    
                        # Tính score
                        try:
                            score_val = f"{float(score)*100:.1f}%"
                        except:
                            score_val = "N/A"
                    
                        # Render card
                        st.markdown(f"""
                        <div class="book-card">
                            {img_html}
                            <div class="book-title">{short_title}</div>
                            <div class="book-category">📂 {str(category)[:30]}</div>
                            <div class="divider-card"></div>
                            <div class="book-score">{score_val}</div>
                            <div class="book-score-label">Độ tương đồng</div>
                        </div>
                        """, unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🛒 Thêm", key=f"cold_rec_cart_{i}_{product_id}", use_container_width=True):
                                handle_add_to_cart(product_id, title)
                        with col_btn2:
                            if st.button("💬 Review", key=f"cold_rec_rev_{i}_{product_id}", use_container_width=True):
                                st.session_state["selected_book_for_reviews"] = product_id
                                st.session_state["should_scroll_to_top"] = True
                                st.rerun()
            
            with st.spinner("⏳ Đang tìm sách thường được mua cùng nhau..."):
                try:
                    frequently_bought = recommender.get_frequently_bought_together(
                        selected_book_id,
                        top_n=5
                    )
                    
                    if frequently_bought.empty:
                        st.info("ℹ️ Chưa đủ dữ liệu để xác định sách thường được mua cùng với cuốn sách này. "
                               "Hãy thử chọn cuốn sách phổ biến hơn!")
                    else:
                        st.success(f"✅ Tìm thấy {len(frequently_bought)} cuốn sách thường được mua cùng!")
                        
                        # Hiển thị thẻ sản phẩm (5 cột một hàng)
                        cols = st.columns(5)
                        for idx, (_, item) in enumerate(frequently_bought.iterrows()):
                            with cols[idx % 5]:
                                # Hình ảnh
                                if pd.notna(item['cover_link']) and item['cover_link'] != '':
                                    st.image(item['cover_link'], use_container_width=True)
                                else:
                                    st.image(f"https://picsum.photos/200/300?random={idx+100}", use_container_width=True)
                                
                                # Thông tin
                                st.write(f"**{item['title'][:20]}...**")
                                st.write(f"*{item['category'][:15]}*")
                
                except Exception as e:
                    st.info(f"ℹ️ Không thể tải dữ liệu 'Thường được mua cùng': {str(e)}")
    
    # ========== SECTION: SẢN PHẨM BÁN CHẠY NHẤT ==========
    st.markdown("---")
    st.subheader("🔥 Sách bán chạy nhất trên Tiki")
    st.caption("Gợi ý dành cho bạn dựa trên lượt đánh giá cao nhất từ cộng đồng")
    
    try:
        # Lấy top 10 sách bán chạy nhất (dùng Bayesian Average)
        bestsellers = get_bestseller(top_n=10)
        
        if bestsellers.empty:
            st.info("ℹ️ Không có dữ liệu sách bán chạy")
        else:
            st.success(f"✅ Tìm thấy {len(bestsellers)} cuốn sách bán chạy nhất!")
            
            # CSS custom cho card sách (nếu chưa được thêm)
            st.markdown("""
            <style>
            .book-card {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 12px;
                margin-bottom: 16px;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                height: 100%;
                text-align: center;
            }
            .book-card img {
                border-radius: 8px;
                width: 100%;
                object-fit: cover;
                height: 200px;
            }
            .book-title {
                font-size: 13px;
                font-weight: 600;
                color: #1a1a2e;
                margin-top: 10px;
                margin-bottom: 4px;
                line-height: 1.4;
                min-height: 36px;
            }
            .book-category {
                font-size: 11px;
                color: #6c757d;
                font-style: italic;
                margin-bottom: 6px;
            }
            .book-score {
                font-size: 22px;
                font-weight: 700;
                color: #FF9800;
                margin: 6px 0;
            }
            .book-score-label {
                font-size: 10px;
                color: #999;
                margin-top: -4px;
            }
            .book-stats {
                font-size: 11px;
                color: #666;
                line-height: 1.5;
                margin: 4px 0;
            }
            .divider-card {
                border-top: 1px solid #f0f0f0;
                margin: 8px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.caption(f"Top {len(bestsellers)} sách có lượt đánh giá cao nhất · Sắp xếp bằng Bayesian Average")
            
            # Hiển thị 5 card mỗi hàng
            COLS_PER_ROW = 5
            best_list = bestsellers.reset_index(drop=True)
            
            for row_start in range(0, len(best_list), COLS_PER_ROW):
                row_data = best_list.iloc[row_start:row_start+COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)
                for i, (_, book) in enumerate(row_data.iterrows()):
                    with cols[i]:
                        # Lấy thông tin
                        title    = str(book.get('title', 'N/A'))
                        category = str(book.get('category', 'N/A'))
                        n_review = int(book.get('n_review', 0))
                        avg_rat  = float(book.get('avg_rating', 0))
                        cover    = book.get('cover_link', '')
                        product_id = book.get('product_id', book.get('id'))
                        short_title = (title[:45] + '...') if len(title) > 45 else title
                        
                        # Ảnh bìa
                        if pd.notna(cover) and str(cover).startswith('http'):
                            img_html = f'<img src="{cover}" style="width:100%;height:180px;object-fit:cover;border-radius:8px;">'
                        else:
                            img_html = '<div style="width:100%;height:180px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:40px;">📚</div>'
                        
                        # Render card
                        st.markdown(f"""
                        <div class="book-card">
                            {img_html}
                            <div class="book-title">{short_title}</div>
                            <div class="book-category">📂 {str(category)[:30]}</div>
                            <div class="divider-card"></div>
                            <div class="book-score">⭐ {avg_rat:.1f}</div>
                            <div class="book-score-label">{n_review:,} đánh giá</div>
                        </div>
                        """, unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🛒 Thêm", key=f"best_cart_{i}_{product_id}", use_container_width=True):
                                handle_add_to_cart(product_id, title)
                        with col_btn2:
                            if st.button("💬 Review", key=f"best_rev_{i}_{product_id}", use_container_width=True):
                                st.session_state["selected_book_for_reviews"] = product_id
                                st.session_state["should_scroll_to_top"] = True
                                st.rerun()
    
    except Exception as e:
        st.warning(f"⚠️ Không thể tải danh sách sách bán chạy: {str(e)}")


# ============ KỊCH BẢN B: KHÁCH HÀNG CŨ (WARM-START) ============
else:
    st.header("👥 Kịch bản: Khách hàng cũ (Warm-Start)")
    
    # Thông báo ngắn gọn
    st.info(
        f"✅ **Khách hàng {selected_customer}** có lịch sử đánh giá | "
        "**Mô hình Hybrid:** 60% SVD + 40% Content-Based"
    )
    
    # Tạo TABS cho 4 chức năng chính
    tab1, tab2, tab3, tab4 = st.tabs(["🛍️ Danh mục sách", "🎯 Gợi ý cho bạn", "📋 Lịch sử đánh giá", "💬 Đánh giá sách"])
    
    # ============ TAB 1: DANH MỤC SÁCH ============
    with tab1:
        st.subheader("🛍️ Duyệt theo Danh mục")
        
        try:
            book_df_full = pd.read_csv(os.path.join(DATA_DIR, 'book_data.csv'))
            
            # Chỉ giữ category xuất hiện >= 5 lần (loại bỏ tên sách bị nhầm thành category)
            cat_counts = book_df_full['category'].value_counts()
            valid_categories = cat_counts[cat_counts >= 5].index.tolist()
            all_categories = ['Tất cả'] + sorted(valid_categories)
        except:
            all_categories = ['Tất cả']
        
        # Selectbox để chọn danh mục
        selected_cat = st.selectbox(
            "Chọn danh mục:",
            options=all_categories,
            key="tab_category_select"
        )
        
        if selected_cat != 'Tất cả':
            try:
                filtered_books = book_df_full[
                    book_df_full['category'] == selected_cat
                ].drop_duplicates(subset='product_id', keep='first').head(10)
                
                if not filtered_books.empty:
                    render_category_books_grid(filtered_books, DATA_DIR, cols_per_row=5)
            except Exception as e:
                st.warning(f"⚠️ Lỗi khi tải dữ liệu danh mục: {str(e)}")
        else:
            st.info("💡 Chọn một danh mục để xem sách")
    
    # ============ TAB 2: GỢI Ý CHO BẠN ============
    with tab2:
        st.subheader("🎯 Sách được gợi ý cho bạn")
        
        # Thông tin khách hàng
        customer_reviews = reviews_data[reviews_data['customer_id'] == selected_customer]
        rated_books = customer_reviews['product_id'].tolist()
        avg_rating = customer_reviews['rating'].mean()
        
        render_customer_info_metrics(len(rated_books), avg_rating)
        
        # Nút lấy gợi ý
        if st.button("🔍 Tính toán gợi ý Hybrid", key="btn_warm_start", use_container_width=True):
            with st.spinner("⏳ Đang tính toán..."):
                try:
                    recommendations = recommender.get_hybrid_recommendations(
                        selected_customer,
                        product_id_viewed=None,
                        top_n=10,
                        content_weight=0.4,
                        collab_weight=0.6
                    )
                    
                    # ==================== CHECKPOINT 3: ĐO RAM - SAU GỌI HÀM DỰ ĐOÁN/GỢI Ý ====================
                    checkpoint_3_ram = get_current_ram_mb()
                    checkpoint_3_increase = checkpoint_3_ram - checkpoint_2_ram
                    print(f"\n[ĐO RAM] ===== CHECKPOINT 3: SAU KHI GỌI HÀM DỰ ĐOÁN/GỢI Ý (Hybrid SVD + Content-Based) =====")
                    print(f"[ĐO RAM] Sau khi tính toán SVD và Content-Based (40% + 60%): {checkpoint_3_ram:.2f} MB")
                    print(f"[ĐO RAM] Tăng thêm so với Checkpoint 2: {checkpoint_3_increase:.2f} MB")
                    print(f"[ĐO RAM] Tổng tăng từ lúc khởi động: {checkpoint_3_ram - checkpoint_1_ram:.2f} MB")
                    print(f"[ĐO RAM] =======================================================================================\n")
                    
                    st.session_state.warm_recommendations = recommendations
                
                except Exception as e:
                    st.error(f"❌ Lỗi: {repr(e)}")
        
        if st.session_state.warm_recommendations is None:
            st.info("💡 Bấm nút để tính toán gợi ý dựa trên lịch sử đánh giá của bạn")
        else:
            if st.session_state.warm_recommendations.empty:
                st.warning("⚠️ Không có gợi ý - Bạn đã đánh giá tất cả sách")
            else:
                st.success(f"✅ Tìm thấy {len(st.session_state.warm_recommendations)} sách phù hợp!")
                render_hybrid_recommendations_grid(st.session_state.warm_recommendations, cols_per_row=5)
    
    # ============ TAB 3: LỊCH SỬ ĐÁNH GIÁ ============
    with tab3:
        st.subheader("📋 Lịch sử đánh giá của bạn")
        
        customer_reviews = reviews_data[reviews_data['customer_id'] == selected_customer]
        customer_reviews_display = customer_reviews.copy()
        customer_reviews_display['product_title'] = customer_reviews_display['product_id'].map(book_dict)
        customer_reviews_display = customer_reviews_display[['product_id', 'product_title', 'rating']]
        customer_reviews_display.columns = ['ID Sách', 'Tên Sách', 'Đánh giá']
        
        st.caption(f"📊 Tổng cộng: {len(customer_reviews_display)} sách đã đánh giá")
        st.dataframe(customer_reviews_display, use_container_width=True, hide_index=True)

    # ============ TAB 4: ĐÁNH GIÁ SÁCH ============
    with tab4:
        st.subheader("💬 Đánh giá & bình luận của sách")
        
        selected_review_book_id = st.selectbox(
            "Chọn quyển sách để xem đánh giá:",
            options=book_data['product_id'].tolist(),
            format_func=lambda x: book_dict.get(x, f"Sách {x}"),
            key="warm_review_book_select"
        )
        
        sel_book = book_data[book_data['product_id'] == selected_review_book_id].iloc[0]
        
        col_img, col_info = st.columns([1, 4])
        with col_img:
            if pd.notna(sel_book['cover_link']) and sel_book['cover_link'] != '':
                st.image(sel_book['cover_link'], use_container_width=True)
            else:
                st.image("https://picsum.photos/200/300?random=2", use_container_width=True)
        with col_info:
            st.markdown(f"#### {sel_book['title']}")
            st.markdown(f"📂 **Thể loại:** {sel_book['category']}")
            
        st.markdown("---")
        
        from ui_components import show_book_reviews
        book_reviews = get_book_reviews_data(selected_review_book_id)
        show_book_reviews(selected_review_book_id, book_reviews)



# ==================== FLOATING CHAT WIDGET - TRỢ LỰC AI TƯ VẤN SÁCH ====================
# Chỉ hiển thị khi Gemini API sẵn có
if GEMINI_AVAILABLE:
    render_simple_floating_button()


# ==================== FOOTER ====================
render_footer()
