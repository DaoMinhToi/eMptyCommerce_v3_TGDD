import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# Global cache cho model name và API Key
_AVAILABLE_MODEL = None
_LAST_API_KEY = None

# ==================== CẤU HÌNH GEMINI API ====================
def init_gemini_api():
    """
    Khởi tạo Gemini API từ .streamlit/secrets.toml
    
    Returns:
        bool: True nếu API sẵn có, False nếu không
    """
    global _AVAILABLE_MODEL, _LAST_API_KEY
    try:
        gemini_api_key = st.secrets.get("GEMINI_API_KEY")
        if gemini_api_key:
            # Chỉ cấu hình và quét model nếu API Key có sự thay đổi
            if gemini_api_key != _LAST_API_KEY:
                genai.configure(api_key=gemini_api_key)
                _LAST_API_KEY = gemini_api_key
                _AVAILABLE_MODEL = None  # Reset cache model cũ
                _detect_available_model()
            return True
        else:
            print("⚠️ GEMINI_API_KEY không được tìm thấy trong .streamlit/secrets.toml")
            _AVAILABLE_MODEL = None
            _LAST_API_KEY = None
            return False
    except Exception as e:
        print(f"⚠️ Lỗi cấu hình Gemini API: {e}")
        return False


def _detect_available_model():
    """
    Phát hiện model Gemini khả dụng bằng liệt kê từ API.
    """
    global _AVAILABLE_MODEL
    
    # Liệt kê tất cả models khả dụng từ API
    try:
        print("🔍 Liệt kê tất cả models Gemini khả dụng...")
        models_list = list(genai.list_models())
        
        # Danh sách model theo thứ tự ưu tiên
        preferred_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-3.5-flash"
        ]
        
        # Tìm model phù hợp theo thứ tự ưu tiên
        for pref in preferred_models:
            for m in models_list:
                if 'generateContent' in m.supported_generation_methods:
                    model_id = m.name.replace('models/', '')
                    if pref in model_id:
                        _AVAILABLE_MODEL = model_id
                        print(f"✅ Phát hiện model khả dụng (ưu tiên): {model_id}")
                        return
                    
        # Nếu không có trong danh sách ưu tiên nhưng list thành công, lấy model đầu tiên hỗ trợ generateContent
        for m in models_list:
            if 'generateContent' in m.supported_generation_methods:
                model_id = m.name.replace('models/', '')
                _AVAILABLE_MODEL = model_id
                print(f"✅ Phát hiện model khả dụng: {model_id}")
                return
    except Exception as e:
        print(f"⚠️ Lỗi khi list models: {str(e)}")
    
    # Fallback: sử dụng model mặc định hiện tại là gemini-2.5-flash
    print("⚠️ Fallback: sử dụng gemini-2.5-flash...")
    _AVAILABLE_MODEL = "gemini-2.5-flash"


def get_available_model():
    """
    Lấy tên model Gemini khả dụng.
    
    Returns:
        str: Tên model hoặc None nếu không có model nào
    """
    global _AVAILABLE_MODEL
    if _AVAILABLE_MODEL is None:
        _detect_available_model()
    return _AVAILABLE_MODEL


# ==================== HÀM TÌM KIẾM NGỮ CẢNH SÁCH (RAG) ====================
def search_context_books(query_text, top_n=6):
    """
    Tìm kiếm các sách liên quan nhất trong cơ sở dữ liệu dựa trên câu hỏi của người dùng.
    
    Kết hợp:
    1. So khớp danh mục (Category)
    2. Khớp cụm từ trong tiêu đề (Title)
    3. Khớp cụm từ tác giả (Authors)
    4. Khớp từ khóa riêng lẻ
    5. Độ tương đồng Cosine TF-IDF (từ recommender model nếu đã khởi tạo)
    """
    from book_data_loader import load_book_data
    
    df_clean = load_book_data()
    if df_clean is None or df_clean.empty:
        return []
        
    app_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(app_dir, 'data', 'book_data.csv')
    
    try:
        if os.path.exists(full_path):
            df_full = pd.read_csv(full_path).drop_duplicates(subset=['product_id'])
            df = pd.merge(
                df_clean[['product_id', 'title', 'category', 'cover_link', 'tokenized_desc']],
                df_full[['product_id', 'current_price', 'avg_rating']],
                on='product_id',
                how='left'
            )
            df['authors'] = "Thế Giới Di Động"
        else:
            df = df_clean.copy()
            df['authors'] = "Thế Giới Di Động"
            df['current_price'] = 5000000
            df['avg_rating'] = 4.5
    except Exception as e:
        print(f"⚠️ Lỗi load/merge product data trong search_context_books: {e}")
        df = df_clean.copy()
        df['authors'] = "Thế Giới Di Động"
        df['current_price'] = 5000000
        df['avg_rating'] = 4.5

    query_lower = query_text.lower().strip()
    
    # Tính điểm khớp cho từng cuốn sách
    scores = pd.Series(0.0, index=df.index)
    
    # 1. Tìm theo danh mục
    categories = df['category'].dropna().unique()
    for cat in categories:
        if cat.lower() in query_lower:
            scores[df['category'] == cat] += 12.0
            
    # 2. Khớp cụm từ đầy đủ trong tiêu đề
    scores[df['title'].str.lower().str.contains(query_lower, na=False)] += 15.0
    
    # 3. Khớp cụm từ trong tác giả
    if 'authors' in df.columns:
        scores[df['authors'].str.lower().str.contains(query_lower, na=False)] += 12.0
        
    # 4. Khớp mô tả đầy đủ
    if 'tokenized_desc' in df.columns:
        scores[df['tokenized_desc'].str.lower().str.contains(query_lower, na=False)] += 5.0
        
    # 5. Khớp các từ khóa đơn lẻ (bỏ qua stopwords tiếng Việt thông dụng)
    keywords = [w.strip() for w in query_lower.split() if len(w.strip()) > 2]
    vietnamese_stopwords = {
        'sản', 'phẩm', 'thiết', 'bị', 'máy', 'điện', 'thoại', 'laptop', 'tai', 'nghe',
        'đồng', 'hồ', 'cửa', 'hàng', 'những', 'của', 'một', 'cho', 'này', 'tìm', 
        'bán', 'chạy', 'hay', 'gợi', 'ý', 'tư', 'vấn', 'nào', 'muốn', 'thích',
        'giới', 'thiệu', 'bạn', 'mình', 'có', 'không', 'về'
    }
    for kw in keywords:
        if kw in vietnamese_stopwords:
            continue
        scores[df['title'].str.lower().str.contains(kw, na=False)] += 2.0
        if 'authors' in df.columns:
            scores[df['authors'].str.lower().str.contains(kw, na=False)] += 1.5
        if 'tokenized_desc' in df.columns:
            scores[df['tokenized_desc'].str.lower().str.contains(kw, na=False)] += 0.5
            
    # 6. Sử dụng Cosine Similarity từ recommender nếu có sẵn trong session state
    recommender_obj = None
    if hasattr(st.session_state, '__contains__'):
        try:
            if 'recommender' in st.session_state:
                recommender_obj = st.session_state.recommender
        except:
            pass
    elif hasattr(st.session_state, 'recommender'):
        recommender_obj = getattr(st.session_state, 'recommender')
        
    if recommender_obj is not None:
        try:
            rec = recommender_obj
            if rec.tfidf_vectorizer is not None and rec.tfidf_matrix is not None:
                from sklearn.metrics.pairwise import cosine_similarity
                query_vec = rec.tfidf_vectorizer.transform([query_lower])
                sim_scores = cosine_similarity(query_vec, rec.tfidf_matrix).flatten()
                
                if len(sim_scores) == len(df):
                    scores += pd.Series(sim_scores, index=df.index) * 6.0
        except Exception as e:
            print(f"⚠️ Lỗi tính cosine similarity trong search_context_books: {e}")
            
    # Lọc sách có điểm khớp lớn hơn 0
    matched_df = df[scores > 0].copy()
    matched_df['match_score'] = scores[scores > 0]
    
    if not matched_df.empty:
        matched_df = matched_df.sort_values(by='match_score', ascending=False)
        return matched_df.head(top_n).to_dict(orient='records')
        
    # Fallback: Trả về sách phổ biến
    try:
        from book_data_loader import get_popular_books
        pop_books = get_popular_books(limit=top_n)
        if pop_books is not None and not pop_books.empty:
            if os.path.exists(full_path):
                df_full = pd.read_csv(full_path).drop_duplicates(subset=['product_id'])
                merged_pop = pd.merge(
                    pop_books[['product_id', 'title', 'category', 'cover_link']],
                    df_full[['product_id', 'authors', 'current_price', 'avg_rating']],
                    on='product_id',
                    how='left'
                )
                return merged_pop.to_dict(orient='records')
            return pop_books.to_dict(orient='records')
    except Exception as e:
        print(f"⚠️ Lỗi fallback get_popular_books: {e}")
        
    return df.head(top_n).to_dict(orient='records')


# ==================== HÀM TRỢ LỰC AI TƯ VẤN SÁCH ====================
def get_ai_response(user_message, chat_history, gemini_available=True):
    """
    Gửi tin nhắn tới Gemini API và nhận phản hồi từ AI Trợ lý tư vấn sách.
    Tự động tìm kiếm sách liên quan trong hệ thống để làm ngữ cảnh.
    """
    if not gemini_available:
        return "❌ Chức năng AI không khả dụng. Vui lòng kiểm tra cấu hình API Key."
    
    try:
        # Lấy model khả dụng
        model_name = get_available_model()
        if not model_name:
            return "❌ Không tìm thấy model Gemini nào khả dụng. Vui lòng kiểm tra API Key."
        
        # 1. Tìm kiếm sản phẩm liên quan trong hệ thống
        relevant_books = search_context_books(user_message, top_n=8)
        
        # 2. Xây dựng ngữ cảnh sản phẩm
        context_str = ""
        if relevant_books:
            context_str = "\nCác sản phẩm có sẵn trong hệ thống cửa hàng eMpTyCommerce liên quan đến yêu cầu của khách hàng:\n"
            for b in relevant_books:
                price = b.get('current_price', 50000)
                rating = b.get('avg_rating', 5.0)
                category = b.get('category', 'Chưa phân loại')
                desc = b.get('tokenized_desc', '')
                
                desc_summary = "Không có mô tả chi tiết."
                if pd.notna(desc) and str(desc).strip():
                    # clean tokenized description for readability
                    desc_summary = str(desc).replace('_', ' ')
                    desc_summary = desc_summary[:150] + "..." if len(desc_summary) > 150 else desc_summary
                    
                context_str += f"- Sản phẩm: \"{b['title']}\"\n"
                context_str += f"  * Giá bán: {int(price):,} đ\n"
                context_str += f"  * Đánh giá: {rating:.1f}/5.0\n"
                context_str += f"  * Thể loại: {category}\n"
                context_str += f"  * Tóm tắt: {desc_summary}\n\n"
        
        # 3. Cấu hình Dynamic System Instruction
        system_instruction = f"""Bạn là một Trợ lý AI Tư vấn Sản phẩm chuyên nghiệp, hoạt động độc quyền cho hệ thống eMpTyCommerce. 
Luôn xưng là 'mình' hoặc 'eMpTy AI' và gọi người dùng là 'bạn' một cách thân thiện. 
Bạn chỉ được phép trả lời, tóm tắt, gợi ý hoặc giải đáp các chủ đề liên quan đến thiết bị công nghệ (điện thoại, laptop, phụ kiện, âm thanh, đồng hồ), thương hiệu hoặc sở thích mua sắm. 

DƯỚI ĐÂY LÀ DANH SÁCH SẢN PHẨM ĐANG CÓ SẴN TRONG HỆ THỐNG CỬA HÀNG eMpTyCommerce:
{context_str}

QUY TẮC PHẢN HỒI NGHIÊM NGẶT:
1. Bạn CHỈ được phép giới thiệu, tư vấn và gợi ý các sản phẩm thực sự có trong DANH SÁCH SẢN PHẨM ĐANG CÓ SẴN ở trên. Tuyệt đối không tự bịa ra sản phẩm hoặc gợi ý sản phẩm ngoài danh sách trên.
2. Mỗi lần tư vấn/gợi ý sản phẩm, hãy giới thiệu khoảng 3-4 sản phẩm phù hợp nhất từ danh sách trên (nếu trong danh sách trên có đủ) để người dùng có nhiều sự lựa chọn. Không giới thiệu duy nhất một sản phẩm trừ khi danh sách trên chỉ có một sản phẩm khớp.
3. Khi nhắc đến tên sản phẩm, bạn BẮT BUỘC phải đặt tên sản phẩm chính xác 100% trong dấu ngoặc kép đôi, ví dụ: "Tai nghe Bluetooth AirPods Pro Gen 2". Điều này rất quan trọng để hệ thống lập tức hiển thị ảnh của sản phẩm.
4. Nếu người dùng chỉ chào hỏi hoặc hỏi thăm thông thường (ví dụ: "xin chào", "hello", "bạn là ai"), hãy chào lại thân thiện, tự giới thiệu mình là eMpTy AI và hỏi nhu cầu mua sắm thiết bị công nghệ của họ một cách lịch sự, KHÔNG gợi ý sản phẩm ngay lập tức trừ khi được yêu cầu.
5. Nếu người dùng hỏi bất kỳ câu hỏi nào ngoài chủ đề công nghệ/sản phẩm (như viết code, toán học, thời tiết, chính trị...), bạn phải từ chối một cách lịch sự và khéo léo điều hướng họ quay lại các sản phẩm công nghệ của cửa hàng.
6. Câu trả lời cần ngắn gọn, tập trung, mang tính chất tư vấn bán hàng chuyên nghiệp và thân thiện.
"""
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        
        # Chuẩn bị lịch sử chat theo format Gemini
        formatted_history = []
        for msg in chat_history:
            if msg["role"] in ["user", "user_message"]:
                formatted_history.append({
                    "role": "user",
                    "parts": [msg["content"]]
                })
            elif msg["role"] in ["assistant", "ai", "model"]:
                formatted_history.append({
                    "role": "model",
                    "parts": [msg["content"]]
                })
        
        # Gửi tin nhắn mới
        response = model.generate_content(
            contents=formatted_history + [{"role": "user", "parts": [user_message]}],
            stream=False
        )
        
        return response.text
    
    except Exception as e:
        error_msg = str(e)
        
        # Kiểm tra các loại lỗi thông thường
        if "429" in error_msg or "quota" in error_msg.lower():
            return "❌ **Hạn chế API:** Đã vượt quá giới hạn sử dụng Gemini API. Vui lòng chờ một chút rồi thử lại, hoặc nâng cấp gói tại [Google AI Studio](https://aistudio.google.com/apikey)"
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            return "❌ **Lỗi xác thực:** API Key không hợp lệ hoặc đã hết hạn. Vui lòng kiểm tra .streamlit/secrets.toml"
        elif "403" in error_msg:
            return "❌ **Lỗi quyền hạn:** API Key không có quyền truy cập. Vui lòng kiểm tra quyền trong Google Cloud Console"
        else:
            return f"❌ Lỗi khi gọi Gemini API: {error_msg[:100]}..."
