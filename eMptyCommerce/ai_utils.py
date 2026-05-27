"""
Module AI Utilities - Các hàm liên quan đến Gemini API
"""

import streamlit as st
import google.generativeai as genai

# Global cache cho model name
_AVAILABLE_MODEL = None

# ==================== CẤU HÌNH GEMINI API ====================
def init_gemini_api():
    """
    Khởi tạo Gemini API từ .streamlit/secrets.toml
    
    Returns:
        bool: True nếu API sẵn có, False nếu không
    """
    try:
        gemini_api_key = st.secrets.get("GEMINI_API_KEY")
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            # Tìm model khả dụng
            _detect_available_model()
            return True
        else:
            print("⚠️ GEMINI_API_KEY không được tìm thấy trong .streamlit/secrets.toml")
            return False
    except Exception as e:
        print(f"⚠️ Lỗi cấu hình Gemini API: {e}")
        return False


def _detect_available_model():
    """
    Phát hiện model Gemini khả dụng bằng liệt kê từ API.
    """
    global _AVAILABLE_MODEL
    
    # Nếu không tìm thấy, liệt kê tất cả models khả dụng
    try:
        print("🔍 Liệt kê tất cả models Gemini khả dụng...")
        models_list = list(genai.list_models())
        for m in models_list:
            if 'generateContent' in m.supported_generation_methods:
                model_id = m.name.replace('models/', '')
                _AVAILABLE_MODEL = model_id
                print(f"✅ Phát hiện model khả dụng: {model_id}")
                return
    except Exception as e:
        print(f"⚠️ Lỗi khi list models: {str(e)}")
    
    # Fallback: thử danh sách các model phổ biến
    print("⚠️ Fallback: thử danh sách model...")
    models_to_try = ["gemini-pro", "text-bison"]
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            _AVAILABLE_MODEL = model_name
            print(f"✅ Phát hiện model khả dụng: {model_name}")
            return
        except:
            continue
    
    print("❌ Không tìm thấy model Gemini nào khả dụng!")
    _AVAILABLE_MODEL = None


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


# ==================== HÀM TRỢ LỰC AI TƯ VẤN SÁCH ====================
def get_ai_response(user_message, chat_history, gemini_available=True):
    """
    Gửi tin nhắn tới Gemini API và nhận phản hồi từ AI Trợ lý tư vấn sách.
    
    Args:
        user_message (str): Tin nhắn của người dùng
        chat_history (list): Lịch sử trò chuyện trước đó
        gemini_available (bool): Có sẵn API hay không
    
    Returns:
        str: Phản hồi từ AI hoặc thông báo lỗi
    """
    if not gemini_available:
        return "❌ Chức năng AI không khả dụng. Vui lòng kiểm tra cấu hình API Key."
    
    try:
        # Lấy model khả dụng
        model_name = get_available_model()
        if not model_name:
            return "❌ Không tìm thấy model Gemini nào khả dụng. Vui lòng kiểm tra API Key."
        
        # Khởi tạo model với system instruction
        system_instruction = """Bạn là một Trợ lý AI Tư vấn Sách chuyên nghiệp, hoạt động độc quyền cho hệ thống eMpTyCommerce. Luôn xưng là 'mình' hoặc 'eMpTy AI' và gọi người dùng là 'bạn' một cách thân thiện. Bạn chỉ được phép trả lời, tóm tắt, gợi ý hoặc giải đáp các chủ đề liên quan đến sách, tác giả, giá tiền sách hoặc sở thích đọc sách. Nếu người dùng hỏi bất kỳ câu hỏi nào ngoài chủ đề sách (như viết code, toán học, thời tiết, chính trị...), bạn phải từ chối một cách lịch sự và khéo léo điều hướng họ quay lại chủ đề sách của cửa hàng."""
        
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
