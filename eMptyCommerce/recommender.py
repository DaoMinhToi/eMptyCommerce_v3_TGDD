"""
Module chứa logic core cho hệ thống gợi ý sản phẩm Hybrid
Kết hợp Content-Based Filtering (TF-IDF) + Collaborative Filtering (SVD)

Xử lý 2 trường hợp chính:
1. Cold-Start Problem: Khách hàng mới (chưa có lịch sử) -> Dùng Content-Based 100%
2. Warm-Start: Khách hàng cũ -> Kết hợp SVD (60%) + Content-Based (40%)
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise import SVD, Dataset, Reader, KNNBasic, KNNWithMeans
import warnings
import os

warnings.filterwarnings("ignore")

# Định nghĩa thư mục dữ liệu tuyệt đối
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, 'data')


class HybridRecommender:
    """
    Lớp HybridRecommender - Hệ thống gợi ý sản phẩm Hybrid (Hybrid Recommendation System)
    
    Kết hợp hai phương pháp chính:
    1. Content-Based Filtering: Gợi ý dựa trên độ tương đồng nội dung (mô tả sản phẩm)
    2. Collaborative Filtering (SVD): Gợi ý dựa trên hành vi người dùng tương tự
    
    Xử lý Cold-Start Problem:
    - Khách hàng mới không có lịch sử -> Sử dụng Content-Based 100%
    - Khách hàng cũ -> Kết hợp cả 2 phương pháp
    """
    
    def __init__(self):
        """
        Khởi tạo HybridRecommender.
        
        Các bước:
        1. Đọc file data/clean_book_data.csv (thông tin sách)
        2. Đọc file data/clean_reviews.csv (đánh giá của khách hàng)
        3. Khởi tạo các biến để lưu mô hình
        4. Tự động huấn luyện Content-Based và Collaborative mô hình
        """
        # Đọc dữ liệu từ file
        self.book_data = None
        self.reviews_data = None
        
        # Biến lưu mô hình
        self.tfidf_vectorizer = None  # TF-IDF vectorizer
        self.tfidf_matrix = None  # Ma trận TF-IDF của các sản phẩm
        self.cosine_sim_matrix = None  # Ma trận độ tương đồng Cosine
        self.svd_model = None  # Mô hình SVD cho Collaborative Filtering
        self.knn_model = None  # Mô hình KNN cho Item-based Collaborative Filtering
        self.reader = None  # Reader để load dữ liệu cho Surprise
        self.trainset = None  # Trainset cho Surprise
        
        # Từ điển để ánh xạ product_id/customer_id với index
        self.product_id_to_idx = {}
        self.idx_to_product_id = {}
        self.customer_id_to_idx = {}
        self.idx_to_customer_id = {}
        
        # Tập khách hàng đã đánh giá (dùng kiểm tra Cold-Start)
        self.known_customers = set()
        self.known_products = set()
        
        print(" Khởi tạo HybridRecommender...")
        
        # Bước 1: Đọc dữ liệu
        self._load_data()
        
        # Bước 2: Huấn luyện mô hình (nếu dữ liệu có sẵn)
        if self.book_data is not None and self.reviews_data is not None:
            print(" Huấn luyện mô hình...")
            self.train_content_based()
            self.train_collaborative()
            print(" Khởi tạo hoàn tất!\n")
    
    def _load_data(self):
        """
        Đọc dữ liệu từ các file CSV.
        
        Đọc:
        - data/clean_book_data.csv: Chứa product_id, title, category, cover_link, tokenized_desc
        - data/clean_reviews.csv: Chứa customer_id, product_id, rating
        """
        try:
            # Đọc dữ liệu sách
            book_path = os.path.join(DATA_DIR, 'clean_book_data.csv')
            if os.path.exists(book_path):
                self.book_data = pd.read_csv(book_path).reset_index(drop=True)
                self.known_products = set(self.book_data['product_id'].unique())
                print(f"    Đọc {len(self.book_data)} sản phẩm từ {book_path}")
            else:
                print(f"     {book_path} không tìm thấy!")
            
            # Đọc dữ liệu đánh giá
            reviews_path = os.path.join(DATA_DIR, 'clean_reviews.csv')
            if os.path.exists(reviews_path):
                self.reviews_data = pd.read_csv(reviews_path)
                self.reviews_data['is_recent'] = 0
                self.known_customers = set(self.reviews_data['customer_id'].unique())
                print(f"    Đọc {len(self.reviews_data)} đánh giá từ {reviews_path}")
            else:
                print(f"     {reviews_path} không tìm thấy!")
                
        except Exception as e:
            print(f"    Lỗi đọc dữ liệu: {e}")
    
    def train_content_based(self):
        """
        Huấn luyện mô hình Content-Based Filtering.
        
        Các bước:
        1. Sử dụng TF-IDF (Term Frequency - Inverse Document Frequency) để chuyển đổi
           các mô tả sản phẩm (tokenized_desc) thành vector số
        2. Tính ma trận độ tương đồng giữa các sản phẩm bằng Cosine Similarity
           (từ 0 đến 1, vì TF-IDF không có giá trị âm — cao hơn = tương đồng hơn)
        3. Lưu lại vectorizer và ma trận để dùng sau
        
        Công thức Cosine Similarity: cos(θ) = (A·B) / (||A|| * ||B||)
        """
        if self.book_data is None or 'tokenized_desc' not in self.book_data.columns:
            print("     Không thể huấn luyện Content-Based: dữ liệu thiếu")
            return
        
        try:
            # Bước 1: Fit TF-IDF Vectorizer
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=3000,  # Giới hạn 3000 từ quan trọng nhất (cân bằng tốc độ và độ chính xác)
                ngram_range=(1, 2),  # Sử dụng unigram và bigram
                min_df=2,  # Từ phải xuất hiện ít nhất 2 lần
                max_df=0.8,  # Từ không xuất hiện quá 80% document
                stop_words=None  # Không bỏ stopwords (vì text đã được xử lý)
            )
            
            # Bước 2: Transform mô tả sản phẩm thành TF-IDF matrix
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(
                self.book_data['tokenized_desc'].fillna('')
            )
            
            # Bước 3: Tính ma trận Cosine Similarity
            self.cosine_sim_matrix = cosine_similarity(self.tfidf_matrix)
            
            # Bước 4: Tạo ánh xạ product_id <-> index
            self.product_id_to_idx = {
                pid: idx for idx, pid in enumerate(self.book_data['product_id'])
            }
            self.idx_to_product_id = {
                idx: pid for pid, idx in self.product_id_to_idx.items()
            }
            
            print(f"    Content-Based Filtering huấn luyện thành công!")
            print(f"     - TF-IDF matrix shape: {self.tfidf_matrix.shape}")
            print(f"     - Cosine similarity matrix shape: {self.cosine_sim_matrix.shape}")
            
        except Exception as e:
            print(f"    Lỗi huấn luyện Content-Based: {e}")
    
    def train_collaborative(self):
        """
        Huấn luyện mô hình Collaborative Filtering (CF).
        
        Các bước:
        1. Sử dụng thư viện Surprise (Python library cho Recommender Systems)
        2. Định nghĩa Rating Scale (từ min đến max của rating)
        3. Load dữ liệu (customer_id, product_id, rating) vào Dataset
        4. Huấn luyện mô hình SVD (Singular Value Decomposition):
           - SVD phân tích ma trận ratings thành 3 ma trận U, Σ, V^T
           - Mục đích: Tìm latent factors (yếu tố ẩn) giải thích hành vi người dùng
           - Công dụng: Dự đoán rating của (customer, product) chưa được đánh giá
        
        Lợi ích Collaborative Filtering:
        - Phát hiện pattern giữa người dùng "tương tự" 
        - Có thể gợi ý sản phẩm mới không có nội dung mô tả
        """
        if self.reviews_data is None:
            print("     Không thể huấn luyện Collaborative Filtering: dữ liệu thiếu")
            return
        
        try:
            # Bước 1: Định nghĩa Rating Scale
            rating_min = self.reviews_data['rating'].min()
            rating_max = self.reviews_data['rating'].max()
            
            # Lưu rating scale để dùng trong get_hybrid_recommendations()
            self.rating_min = rating_min
            self.rating_max = rating_max
            
            self.reader = Reader(rating_scale=(rating_min, rating_max))
            
            # Bước 2: Load dữ liệu
            dataset = Dataset.load_from_df(
                self.reviews_data[['customer_id', 'product_id', 'rating']],
                reader=self.reader
            )
            
            # Bước 3: Tạo trainset từ toàn bộ dữ liệu
            self.trainset = dataset.build_full_trainset()
            
            # Bước 4: Huấn luyện SVD
            self.svd_model = SVD(
                n_factors=50,  # Số latent factors
                n_epochs=40,  # Số epoch huấn luyện
                lr_all=0.005,  # Learning rate
                reg_all=0.02,  # Regularization parameter
                random_state=42
            )
            self.svd_model.fit(self.trainset)
            
            # Bước 5: Tạo ánh xạ customer_id <-> inner_id (của Surprise)
            self.customer_id_to_idx = {
                cid: iid for iid, cid in enumerate(self.trainset.all_users())
            }
            
            # Bước 6: Huấn luyện mô hình Item-based KNN
            # KNN Item-based: Tìm các sản phẩm tương tự dựa trên hành vi người dùng
            # user_based=False => Item-based (tương tự sản phẩm)
            # user_based=True => User-based (tương tự người dùng)
            # min_support: Yêu cầu ít nhất 2 người cùng đánh giá 2 item thì mới tính similarity
            sim_options = {
                'name': 'cosine', 
                'user_based': False, 
                'min_support': 2
            }
            self.knn_model = KNNWithMeans(k=20, sim_options=sim_options, verbose=False)
            self.knn_model.fit(self.trainset)
            
            print(f"    Collaborative Filtering huấn luyện thành công!")
            print(f"     - Số customers: {self.trainset.n_users}")
            print(f"     - Số products: {self.trainset.n_items}")
            print(f"     - Số ratings: {self.trainset.n_ratings}")
            print(f"     - Rating scale: {rating_min} - {rating_max}")
            print(f"    Item-based KNN huấn luyện thành công!")
            
        except Exception as e:
            print(f"    Lỗi huấn luyện Collaborative Filtering: {e}")
    
    def get_content_based_recommendations(self, product_id, top_n=10):
        """
        Lấy danh sách sản phẩm tương tự dựa trên Content-Based Filtering.
        
        Các bước:
        1. Tìm index (số thứ tự dòng) của product_id trong book_data DataFrame
        2. Lấy mảng điểm tương đồng cosine của sản phẩm này với tất cả sản phẩm khác
        3. Sắp xếp theo độ tương đồng giảm dần
        4. Lấy top_n sản phẩm giống nhất (bỏ qua cuốn đầu tiên vì nó chính là cuốn đang xem)
        5. Dùng .iloc để lấy data dựa trên số thứ tự dòng
        
        Args:
            product_id (int): ID của sản phẩm tham chiếu
            top_n (int): Số lượng sản phẩm gợi ý (mặc định: 10)
        
        Returns:
            DataFrame: Dataframe gồm sách tương tự + cột 'similarity_score'
        """
        try:
            # Bước 1: Tìm index (số thứ tự dòng) của cuốn sách có product_id tương ứng
            idx = self.book_data[self.book_data['product_id'] == product_id].index[0]
        except IndexError:
            # Nếu không tìm thấy sách -> trả về DataFrame rỗng
            return pd.DataFrame()
        
        # Bước 2: Lấy mảng điểm tương đồng cosine của sách này với tất cả sách khác
        sim_scores = list(enumerate(self.cosine_sim_matrix[idx]))
        
        # Bước 3: Sắp xếp theo điểm tương đồng giảm dần
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Bước 4: Lấy top_n cuốn sách giống nhất (bỏ qua cuốn đầu tiên vì nó chính là cuốn đang xem)
        sim_scores = sim_scores[1:top_n+1]
        
        # Bước 5: Lấy ra index của các cuốn sách đó
        book_indices = [i[0] for i in sim_scores]
        scores = [i[1] for i in sim_scores]
        
        # Bước 6: Dùng .iloc để lấy data dựa trên số thứ tự dòng
        result_df = self.book_data.iloc[book_indices].copy()
        result_df['similarity_score'] = scores
        
        return result_df
    
    def get_hybrid_recommendations(self, customer_id, product_id_viewed=None, top_n=10,
                                  content_weight=0.4, collab_weight=0.6):
        """
        LẤY DANH SÁCH GỢI Ý HYBRID - HÀM CHÍNH CỦA HỆ THỐNG
        
        Xử lý 2 trường hợp chính:
        
        TRƯỜNG HỢP 1: COLD-START PROBLEM (Khách hàng mới)
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        - customer_id không tồn tại trong tập train (chưa đánh giá sản phẩm nào)
        - Giải pháp: Sử dụng Content-Based 100%
          * Nếu có product_id_viewed: Lấy sản phẩm tương tự
          * Nếu không: Trả về top sản phẩm phổ biến nhất (dựa n_review)
        
        TRƯỜNG HỢP 2: WARM-START (Khách hàng cũ)
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        - customer_id đã có lịch sử đánh giá
        - Giải pháp: Kết hợp cả 2 phương pháp
          * Dùng SVD dự đoán rating khách cho các sản phẩm chưa đánh giá
          * Tính Content-Based similarity dựa trên sản phẩm khách yêu thích (rating cao)
          * Kết hợp: Score_Hybrid = collab_weight * SVD_Score + content_weight * Content_Score
          * Chỉ gợi ý sản phẩm chưa đánh giá (loại những sản phẩm đã xem)
        
        Args:
            customer_id (int): ID của khách hàng
            product_id_viewed (int, optional): ID sản phẩm đang xem (dùng cho Cold-Start)
            top_n (int): Số lượng sản phẩm gợi ý (mặc định: 10)
            content_weight (float): Trọng số Content-Based trong hybrid (0-1)
            collab_weight (float): Trọng số Collaborative trong hybrid (0-1)
        
        Returns:
            DataFrame: Dataframe chứa top N sản phẩm gợi ý
                      [product_id, title, category, cover_link, hybrid_score]
        """
        # Kiểm tra trường hợp
        is_cold_start = customer_id not in self.known_customers
        
        # ============ TRƯỜNG HỢP 1: COLD-START ============
        if is_cold_start:
            print(f" Cold-Start Problem: Khách hàng {customer_id} là người dùng mới")
            print(f"   → Dùng Content-Based 100% để gợi ý")
            
            # Nếu khách đang xem 1 sản phẩm cụ thể
            if product_id_viewed is not None and product_id_viewed in self.known_products:
                print(f"   → Gợi ý dựa trên sản phẩm đang xem: {product_id_viewed}")
                return self.get_content_based_recommendations(product_id_viewed, top_n)
            
            # Nếu không có sản phẩm tham chiếu -> Thử lấy sản phẩm trong giỏ hàng (nếu có) trước khi fallback về phổ biến nhất
            else:
                try:
                    import streamlit as st
                    if hasattr(st, 'session_state') and 'cart_id' in st.session_state:
                        from db_utils import get_cart_items
                        cart_items = get_cart_items(st.session_state.cart_id)
                        if not cart_items.empty:
                            # Lọc các cuốn sách có trong danh mục sản phẩm hợp lệ của hệ thống
                            valid_items = cart_items[cart_items['product_id'].isin(self.known_products)]
                            if not valid_items.empty:
                                last_cart_product_id = int(valid_items.iloc[0]['product_id'])
                                print(f"   → Gợi ý cho người dùng mới dựa trên sản phẩm trong giỏ hàng: {last_cart_product_id}")
                                recs = self.get_content_based_recommendations(last_cart_product_id, top_n)
                                if not recs.empty:
                                    recs['popularity_score'] = recs['similarity_score']
                                    return recs[['product_id', 'title', 'category', 'cover_link', 'popularity_score']]
                except Exception as cart_err:
                    print(f"     Lỗi kiểm tra giỏ hàng cho người dùng mới: {cart_err}")
                
                print(f"   → Không có sản phẩm tham chiếu hoặc giỏ hàng trống → Trả về sản phẩm phổ biến nhất")
                try:
                    # Load book_data.csv (chứa n_review và avg_rating)
                    book_data_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), 
                        'data', 'book_data.csv'
                    )
                    book_data_full = pd.read_csv(book_data_path)
                    
                    # Xử lý dữ liệu - deduplicate with keep='first'
                    book_data_full = book_data_full.drop_duplicates(subset='product_id', keep='first')
                    book_data_full = book_data_full.dropna(subset=['n_review', 'avg_rating'])
                    
                    # Tính Bayesian Average Score
                    m = book_data_full['n_review'].quantile(0.6)
                    C = book_data_full['avg_rating'].mean()
                    book_data_full['popularity_score'] = (
                        (book_data_full['n_review'] / (book_data_full['n_review'] + m)) * 
                        book_data_full['avg_rating'] + 
                        (m / (book_data_full['n_review'] + m)) * C
                    )
                    
                    # Lọc: chỉ giữ sản phẩm có n_review >= m
                    book_data_full = book_data_full[book_data_full['n_review'] >= m]
                    
                    # Deduplicate self.book_data before merge (local copy, not modifying self)
                    clean_book_data = self.book_data.drop_duplicates(subset='product_id', keep='first')
                    
                    # Merge với self.book_data để lấy cover_link từ clean_book_data
                    merged = book_data_full.merge(
                        clean_book_data[['product_id', 'cover_link']], 
                        on='product_id', 
                        how='left',
                        suffixes=('', '_clean')
                    )
                    
                    # Sử dụng cover_link từ clean_book_data nếu có, nếu không thì dùng từ book_data
                    merged['cover_link'] = merged['cover_link_clean'].fillna(merged['cover_link'])
                    
                    # Final safety dedup after merge to prevent any remaining duplicates
                    merged = merged.drop_duplicates(subset='product_id', keep='first')
                    
            # Sắp xếp theo popularity_score giảm dần, lấy top_n
                    popular_products = merged.nlargest(top_n, 'popularity_score')[
                        ['product_id', 'title', 'category', 'cover_link', 'popularity_score']
                    ].copy()
                    
                    return popular_products
                
                except Exception as e:
                    print(f"     Lỗi khi tính popularity: {str(e)}")
                    # Fallback: trả về top_n sản phẩm đầu tiên từ clean_book_data
                    fallback = self.book_data.head(top_n).copy()
                    fallback['popularity_score'] = 0
                    return fallback[['product_id', 'title', 'category', 'cover_link', 'popularity_score']]
        
        # ============ TRƯỜNG HỢP 2: WARM-START ============
        else:
            print(f" Warm-Start: Khách hàng {customer_id} có lịch sử đánh giá")
            
            # 1. Xác định các sản phẩm thuộc ngữ cảnh phiên làm việc hiện tại (Giỏ hàng & Sách đang xem)
            session_context_pids = set()
            try:
                import streamlit as st
                if hasattr(st, 'session_state'):
                    # Lấy sản phẩm trong giỏ hàng hiện tại
                    if 'cart_id' in st.session_state:
                        from db_utils import get_cart_items
                        cart_items = get_cart_items(st.session_state.cart_id)
                        if not cart_items.empty:
                            session_context_pids.update(cart_items['product_id'].dropna().astype(int).tolist())
                    
                    # Lấy sản phẩm đang xem chi tiết
                    viewed_id = st.session_state.get("selected_book_for_reviews")
                    if viewed_id is not None:
                        session_context_pids.add(int(viewed_id))
            except Exception as e:
                print(f"     Lỗi lấy session context pids: {e}")
                
            if product_id_viewed is not None:
                session_context_pids.add(int(product_id_viewed))

            # 2. Lấy 3 tương tác gần đây nhất có ID khác nhau từ SQLite (để biết họ vừa quan tâm cuốn nào)
            latest_unique_pids = []
            if customer_id is not None:
                try:
                    import sqlite3
                    from db_utils import DB_PATH
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT product_id, MAX(timestamp) as max_ts
                        FROM User_Interactions 
                        WHERE customer_id = ? 
                        GROUP BY product_id
                        ORDER BY max_ts DESC 
                        LIMIT 3
                    ''', (customer_id,))
                    rows = cursor.fetchall()
                    conn.close()
                    for r in rows:
                        latest_unique_pids.append(int(r[0]))
                except Exception as db_err:
                    print(f"     Lỗi lấy tương tác mới nhất từ SQLite: {db_err}")

            # 3. Tự động thay đổi trọng số nếu phát hiện ngữ cảnh phiên hoặc tương tác gần đây (Demo Mode)
            if session_context_pids or latest_unique_pids:
                print("   → Phát hiện hành động/tương tác mới của người dùng trong phiên này")
                print("   → Điều chỉnh trọng số: 80% Content-Based + 20% Collaborative Filtering")
                content_weight = 0.8
                collab_weight = 0.2
            
            print(f"   → Kết hợp SVD ({collab_weight*100:.0f}%) + Content-Based ({content_weight*100:.0f}%)")
            
            # Lấy sản phẩm khách đã đánh giá
            customer_rated = set(
                self.reviews_data[self.reviews_data['customer_id'] == customer_id]['product_id']
            )
            
            # Lấy sản phẩm khách chưa đánh giá
            all_products = set(self.book_data['product_id'].unique())
            unrated_products = list(all_products - customer_rated)
            
            if not unrated_products:
                print("     Khách đã đánh giá toàn bộ sản phẩm!")
                return pd.DataFrame()
            
            # Tính SVD scores cho các sản phẩm chưa đánh giá
            svd_scores = {}
            for product_id in unrated_products:
                try:
                    pred = self.svd_model.predict(customer_id, product_id)
                    svd_scores[product_id] = pred.est  # estimated rating
                except:
                    svd_scores[product_id] = 0  # Nếu predict fails

            # Tính Content-Based scores
            # Sử dụng tất cả tương tác (VIEW=1.0, ADD_TO_CART=3.0, PURCHASE=5.0) làm trọng số tính trung bình similarity.
            interacted_reviews = self.reviews_data[
                (self.reviews_data['customer_id'] == customer_id) &
                (self.reviews_data['rating'] > 0)
            ].copy()
            
            # Các từ khóa nhận diện bộ truyện (Series Keywords) để kích hoạt Series Boost đặc biệt
            SERIES_KEYWORDS = {'doraemon', 'conan', 'one piece', 'harry potter', 'sherlock', 'dragon ball', 'ehon', 'shin'}
            
            def get_series_bonus(title1, title2):
                t1 = str(title1).lower()
                t2 = str(title2).lower()
                for kw in SERIES_KEYWORDS:
                    if kw in t1 and kw in t2:
                        return 1.0
                return 0.0

            # Tạo mapping product_id -> title để lookup nhanh
            pid_to_title = dict(zip(self.book_data['product_id'], self.book_data['title']))

            content_scores = {}
            for product_id in unrated_products:
                if interacted_reviews.empty or product_id not in self.product_id_to_idx:
                    content_scores[product_id] = 0
                else:
                    weighted_sims = []
                    weights = []
                    for _, row in interacted_reviews.iterrows():
                        ref_pid = int(row['product_id'])
                        ref_rating = float(row['rating'])
                        
                        # Phân cấp bội số trọng số theo thứ tự thời gian gần nhất (SQLite) và giỏ hàng hoạt động
                        multiplier = 1.0
                        if ref_pid in session_context_pids:
                            multiplier = 30.0
                        elif ref_pid in latest_unique_pids:
                            idx = latest_unique_pids.index(ref_pid)
                            if idx == 0:
                                multiplier = 100.0  # Tương tác gần nhất tuyệt đối (vừa mua/xem/đánh giá xong)
                            elif idx == 1:
                                multiplier = 10.0   # Tương tác gần nhì
                            else:
                                multiplier = 5.0    # Tương tác gần ba
                        
                        effective_weight = ref_rating * multiplier
                        
                        if ref_pid in self.product_id_to_idx:
                            ref_idx = self.product_id_to_idx[ref_pid]
                            prod_idx = self.product_id_to_idx[product_id]
                            sim = self.cosine_sim_matrix[ref_idx][prod_idx]
                            
                            # CỘNG THÊM SERIES BONUS NẾU CÙNG BỘ TRUYỆN
                            ref_title = pid_to_title.get(ref_pid, "")
                            prod_title = pid_to_title.get(product_id, "")
                            sim += get_series_bonus(ref_title, prod_title)
                            
                            # Giới hạn sim tối đa là 1.0
                            sim = min(1.0, sim)
                            
                            weighted_sims.append(sim * effective_weight)
                            weights.append(effective_weight)
                    
                    content_scores[product_id] = (sum(weighted_sims) / sum(weights)) if weights else 0
            
            # Kết hợp scores
            hybrid_scores = {}
            for product_id in unrated_products:
                # Normalize scores về [0, 1] dựa trên rating scale được detect
                rating_range = self.rating_max - self.rating_min
                normalized_svd = (svd_scores[product_id] - self.rating_min) / rating_range if rating_range > 0 else 0
                normalized_svd = max(0, min(1, normalized_svd))  # Clip to [0, 1]
                normalized_content = max(0.0, min(1.0, content_scores[product_id]))  # Clip content similarity to [0, 1]
                
                # Tính hybrid score
                hybrid_scores[product_id] = (
                    collab_weight * normalized_svd +
                    content_weight * normalized_content
                )
            
            # Sắp xếp và lấy top N
            sorted_products = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
            
            recommendations = []
            for product_id, score in sorted_products:
                product_info = self.book_data[self.book_data['product_id'] == product_id].iloc[0]
                recommendations.append({
                    'product_id': product_id,
                    'title': product_info['title'],
                    'category': product_info['category'],
                    'cover_link': product_info['cover_link'],
                    'hybrid_score': score,
                    'svd_score': svd_scores[product_id],
                    'content_score': content_scores[product_id]
                })
            
            return pd.DataFrame(recommendations)
    
    def get_frequently_bought_together(self, product_id, top_n=5):
        """
        Tìm các sản phẩm hay được mua cùng nhau (Frequently Bought Together)
        sử dụng Item-based KNN Collaborative Filtering.
        
        Ý tưởng:
        - Dùng mô hình KNN tìm k sản phẩm gần nhất với sản phẩm tham chiếu
        - "Gần nhất" được định nghĩa bằng cosine similarity trong không gian đánh giá
        - Nếu nhiều người đánh giá sản phẩm A và sản phẩm B giống nhau,
          thì A và B là những sản phẩm hay được mua cùng nhau
        
        Args:
            product_id (int): ID sản phẩm tham chiếu
            top_n (int): Số lượng sản phẩm liên quan (mặc định: 5)
        
        Returns:
            DataFrame: Dataframe chứa các sản phẩm hay được mua cùng
                      Hoặc DataFrame rỗng nếu sản phẩm không có trong tập train
        
        Ví dụ:
        - Nếu người dùng xem cuốn "Python Programming"
        - Hàm sẽ trả về những cuốn sách khác mà những người 
          mua "Python Programming" cũng thường mua
        """
        try:
            # Bước 1: Chuyển đổi product_id thành inner_id (mã số nội bộ của Surprise)
            inner_product_id = self.knn_model.trainset.to_inner_iid(product_id)
            
            # Bước 2: Tìm k sản phẩm gần nhất (hàng xóm gần nhất)
            neighbor_inner_ids = self.knn_model.get_neighbors(inner_product_id, k=top_n)
            
            # Bước 3: Chuyển đổi ngược lại thành product_id gốc
            neighbor_product_ids = [
                self.knn_model.trainset.to_raw_iid(inner_id) for inner_id in neighbor_inner_ids
            ]
            
            # Bước 4: Lấy thông tin chi tiết từ book_data
            frequently_bought = self.book_data[
                self.book_data['product_id'].isin(neighbor_product_ids)
            ].copy()
            
            # Bước 5: Loại bỏ cuốn sách người dùng đang xem (tránh gợi ý lại sách đang xem)
            frequently_bought = frequently_bought[
                frequently_bought['product_id'] != product_id
            ].reset_index(drop=True)
            
            # Bước 6: Loại bỏ các cuốn sách bị trùng tên (keep='first' để giữ bản ghi đầu tiên)
            frequently_bought = frequently_bought.drop_duplicates(
                subset=['title'], 
                keep='first'
            ).reset_index(drop=True)
            
            # Bước 7: Thêm cột similarity score
            similarity_scores = []
            for prod_id in frequently_bought['product_id']:
                inner_neighbor_id = self.knn_model.trainset.to_inner_iid(prod_id)
                # Tính cosine similarity (dựa trên hàng xóm gần nhất)
                sim = self.knn_model.sim[inner_product_id][inner_neighbor_id]
                similarity_scores.append(sim)
            
            frequently_bought['knn_similarity_score'] = similarity_scores
            
            # Bước 8: Sắp xếp theo similarity score giảm dần
            frequently_bought = frequently_bought.sort_values(
                'knn_similarity_score', ascending=False
            ).reset_index(drop=True)
            
            # Bước 9: Lấy đúng top_n cuốn sách sau khi đã lọc trùng
            frequently_bought = frequently_bought.head(top_n)
            
            return frequently_bought
            
        except ValueError as e:
            # Bắt lỗi nếu product_id không có trong tập train
            print(f"  Lỗi: Sản phẩm {product_id} không tồn tại trong tập dữ liệu huấn luyện")
            print(f"   Chi tiết: {e}")
            return pd.DataFrame()  # Trả về DataFrame rỗng

    def update_and_retrain(self):
        """
        Tự động nạp dữ liệu tương tác người dùng mới từ SQLite và huấn luyện lại Collaborative Filtering.
        """
        try:
            # 1. Đọc dữ liệu lịch sử gốc từ CSV
            reviews_path = os.path.join(DATA_DIR, 'clean_reviews.csv')
            if os.path.exists(reviews_path):
                base_reviews = pd.read_csv(reviews_path)
            else:
                base_reviews = pd.DataFrame(columns=['customer_id', 'product_id', 'rating'])
                
            # 2. Truy xuất tương tác mới từ SQLite
            from db_utils import get_all_user_interactions
            new_interactions = get_all_user_interactions()
            
            if not new_interactions.empty:
                # Gộp hai tập dữ liệu
                # Thiết lập độ ưu tiên để giữ lại tương tác chất lượng nhất: REVIEW > PURCHASE > ADD_TO_CART > VIEW
                priority_map = {
                    'REVIEW': 4,
                    'PURCHASE': 3,
                    'ADD_TO_CART': 2,
                    'VIEW': 1
                }
                new_interactions['priority'] = new_interactions['interaction_type'].map(priority_map).fillna(0)
                new_interactions['is_recent'] = 1
                
                base_reviews_copy = base_reviews.copy()
                base_reviews_copy['priority'] = 4
                base_reviews_copy['is_recent'] = 0
                
                combined = pd.concat([base_reviews_copy, new_interactions[['customer_id', 'product_id', 'rating', 'priority', 'is_recent']]], ignore_index=True)
                
                # Sắp xếp theo priority giảm dần, sau đó theo rating giảm dần
                combined = combined.sort_values(
                    by=['priority', 'rating'], 
                    ascending=[False, False]
                )
                # Loại bỏ trùng lặp và giữ lại dòng đầu tiên (tương tác có độ ưu tiên cao nhất)
                combined = combined.drop_duplicates(subset=['customer_id', 'product_id'], keep='first')
                self.reviews_data = combined[['customer_id', 'product_id', 'rating', 'is_recent']].reset_index(drop=True)
            else:
                self.reviews_data = base_reviews.copy()
                self.reviews_data['is_recent'] = 0
                
            # Cập nhật danh sách khách hàng đã biết
            self.known_customers = set(self.reviews_data['customer_id'].unique())
            
            # 3. Huấn luyện lại Collaborative Filtering (SVD & KNN)
            print("🚀 [Dynamic Retraining] Đang tự động huấn luyện lại Collaborative Filtering...")
            self.train_collaborative()
            print("✓ [Dynamic Retraining] Huấn luyện lại hoàn tất thành công!")
            return True
        except Exception as e:
            print(f"❌ [Dynamic Retraining] Lỗi khi tự động huấn luyện lại: {e}")
            return False


class KNNRecommender:
    """
    Item-based KNN Collaborative Filtering - Thuật toán gợi ý dựa trên sản phẩm tương tự
    
    Ý tưởng chính:
    - Xác định mức độ tương đồng giữa các sản phẩm dựa trên hành vi của người dùng
    - Nếu 2 sản phẩm được đánh giá tương tự bởi nhiều người dùng
    - Thì 2 sản phẩm đó được coi là "tương tự" với nhau
    - Dùng để gợi ý sản phẩm tương tự cho người dùng
    
    Ưu điểm:
    - Không yêu cầu đặc điểm nội dung (chỉ cần rating)
    - Có thể phát hiện được mối quan hệ phức tạp giữa sản phẩm
    - Stable: Kết quả không thay đổi khi thêm người dùng mới
    
    Nhược điểm:
    - Yêu cầu đủ dữ liệu đánh giá (sparse data problem)
    - Khó áp dụng với sản phẩm mới (new item problem)
    """
    
    def __init__(self, db_path='data/clean_reviews.csv'):
        """
        Khởi tạo KNN Recommender.
        
        Args:
            db_path (str): Đường dẫn tới file CSV chứa dữ liệu đánh giá
                         Cần có cột: customer_id, product_id, rating
        """
        self.db_path = db_path
        self.model = None
        self.trainset = None
        self.reader = None
    
    def train(self):
        """
        Huấn luyện mô hình Item-based KNN.
        
        Các bước:
        1. Đọc file dữ liệu đánh giá từ CSV
        2. Định nghĩa Rating Scale (từ min đến max)
        3. Load dữ liệu vào Surprise Dataset
        4. Tạo trainset từ toàn bộ dữ liệu
        5. Tạo mô hình KNNWithMeans với:
           - k=20: Xét 20 sản phẩm hàng xóm gần nhất
           - sim_options={'name': 'cosine', 'user_based': False}:
             * cosine: Sử dụng cosine similarity
             * user_based=False: Item-based (không phải user-based)
        6. Huấn luyện mô hình
        
        Returns:
            self: Trả về chính object này để dùng method chaining
        """
        try:
            # Bước 1: Đọc dữ liệu
            df = pd.read_csv(self.db_path)
            
            # Bước 2: Xác định Rating Scale
            rating_min = df['rating'].min()
            rating_max = df['rating'].max()
            self.reader = Reader(rating_scale=(rating_min, rating_max))
            
            # Bước 3: Load dữ liệu vào Surprise
            data = Dataset.load_from_df(
                df[['customer_id', 'product_id', 'rating']], 
                reader=self.reader
            )
            
            # Bước 4: Tạo trainset
            self.trainset = data.build_full_trainset()
            
            # Bước 5: Cấu hình Item-based KNN với cosine similarity
            sim_options = {
                'name': 'cosine',  # Sử dụng cosine similarity
                'user_based': False,  # Item-based (không phải user-based)
                'min_support': 2  # Ít nhất 2 người cùng đánh giá mới tính similarity
            }
            
            # Bước 6: Tạo và huấn luyện mô hình
            self.model = KNNWithMeans(k=20, sim_options=sim_options, verbose=False)
            self.model.fit(self.trainset)
            
            print(" Item-based KNN huấn luyện thành công!")
            print(f"  - Số customers: {self.trainset.n_users}")
            print(f"  - Số products: {self.trainset.n_items}")
            print(f"  - Số ratings: {self.trainset.n_ratings}")
            print(f"  - Rating scale: {rating_min} - {rating_max}")
            
            return self
            
        except Exception as e:
            print(f" Lỗi khi huấn luyện KNN: {e}")
            return self
    
    def get_recommendations(self, customer_id, n=10):
        """
        Lấy danh sách gợi ý TOP-N sản phẩm cho một khách hàng.
        
        Quy trình:
        1. Tìm tất cả sản phẩm khách hàng chưa đánh giá (chưa xem)
        2. Dự đoán rating của khách cho từng sản phẩm chưa xem bằng KNN
           (Dựa trên rating của các sản phẩm tương tự)
        3. Sắp xếp theo rating dự đoán giảm dần
        4. Lấy top-N sản phẩm có rating dự đoán cao nhất
        
        Args:
            customer_id (int): ID khách hàng cần gợi ý
            n (int): Số lượng sản phẩm gợi ý (mặc định: 10)
        
        Returns:
            list: Danh sách tuple (product_id, estimated_rating)
                  Ví dụ: [(101, 4.5), (102, 4.3), ...]
        """
        if self.model is None:
            print(" Mô hình chưa được huấn luyện. Đang huấn luyện...")
            self.train()
        
        # Bước 1: Đọc dữ liệu
        df = pd.read_csv(self.db_path)
        
        # Bước 2: Lấy sản phẩm khách đã đánh giá
        rated_products = set(
            df[df['customer_id'] == customer_id]['product_id'].tolist()
        )
        
        # Bước 3: Lấy toàn bộ sản phẩm
        all_products = set(df['product_id'].unique())
        
        # Bước 4: Xác định sản phẩm chưa xem
        unrated_products = list(all_products - rated_products)
        
        if not unrated_products:
            print(f" Khách hàng {customer_id} đã đánh giá tất cả sản phẩm!")
            return []
        
        # Bước 5: Dự đoán rating cho mỗi sản phẩm chưa xem
        predictions = []
        for product_id in unrated_products:
            try:
                # Sử dụng mô hình để dự đoán
                pred = self.model.predict(customer_id, product_id, verbose=False)
                predictions.append((product_id, pred.est))
            except Exception as e:
                # Bỏ qua sản phẩm nếu có lỗi
                print(f"  ⚠️ Không thể dự đoán sản phẩm {product_id}: {e}")
                continue
        
        # Bước 6: Sắp xếp theo rating dự đoán giảm dần
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        # Bước 7: Lấy top-N
        recommendations = predictions[:n]
        
        return recommendations
