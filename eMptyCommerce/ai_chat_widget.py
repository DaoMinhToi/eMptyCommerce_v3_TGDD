"""
Module Floating Chat Widget - Trợ lý AI Tư vấn Sách
Cung cấp giao diện chat nổi ở góc dưới phải màn hình
"""

import streamlit as st
from ai_utils import get_ai_response
from book_data_loader import get_book_image, load_book_data
import re


def render_floating_chat_widget():
    """
    Render giao diện Floating Chat Widget ở góc dưới bên phải.
    - Sử dụng st.popover để tạo chat modal
    - Apply CSS để định vị fixed position
    """
    
    # CSS để tạo floating effect
    st.markdown("""
    <style>
    /* Floating Chat Widget Container */
    .chat-widget-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        font-family: 'Arial', sans-serif;
    }
    
    .chat-button {
        background: linear-gradient(135deg, #6C63FF 0%, #5A54D4 100%);
        border: none;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 4px 12px rgba(108, 99, 255, 0.4);
        transition: all 0.3s ease;
    }
    
    .chat-button:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 16px rgba(108, 99, 255, 0.6);
    }
    
    /* Chat Messages Styling */
    .chat-message-user {
        background-color: #6C63FF;
        color: white;
        padding: 10px 14px;
        border-radius: 12px;
        margin: 6px 0;
        border-bottom-right-radius: 4px;
        max-width: 85%;
        word-wrap: break-word;
        align-self: flex-end;
        margin-left: auto;
    }
    
    .chat-message-ai {
        background-color: #f0f0f0;
        color: #333;
        padding: 10px 14px;
        border-radius: 12px;
        margin: 6px 0;
        border-bottom-left-radius: 4px;
        max-width: 85%;
        word-wrap: break-word;
        align-self: flex-start;
    }
    
    .chat-input-group {
        display: flex;
        gap: 8px;
        margin-top: 10px;
        align-items: flex-end;
    }
    
    .chat-input {
        flex: 1;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 8px;
        font-size: 14px;
        font-family: 'Arial', sans-serif;
    }
    
    .chat-send-btn {
        background-color: #6C63FF;
        color: white;
        border: none;
        padding: 10px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        transition: background-color 0.3s ease;
    }
    
    .chat-send-btn:hover {
        background-color: #5A54D4;
    }
    
    .chat-header {
        background: linear-gradient(135deg, #6C63FF 0%, #5A54D4 100%);
        color: white;
        padding: 12px;
        border-radius: 8px 8px 0 0;
        text-align: center;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 0;
    }
    
    .chat-content {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 0 0 8px 8px;
        padding: 12px;
        max-height: 400px;
        overflow-y: auto;
        width: 320px;
        display: flex;
        flex-direction: column;
    }
    
    .chat-messages-area {
        flex: 1;
        overflow-y: auto;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
    }
    
    .book-recommendations {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 10px 0;
    }
    
    .book-card {
        text-align: center;
        border-radius: 8px;
        overflow: hidden;
        background: #f9f9f9;
        padding: 6px;
    }
    
    .book-card img {
        width: 100%;
        height: 120px;
        object-fit: cover;
        border-radius: 4px;
    }
    
    .book-card-title {
        font-size: 11px;
        margin-top: 6px;
        font-weight: 600;
        color: #333;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Tạo container floating
    col_spacer, col_chat = st.columns([10, 1])
    
    with col_chat:
        if st.button("💬", key="chat_button", help="Mở Trợ lý AI tư vấn sản phẩm"):
            st.session_state.chat_expanded = True
            st.rerun()
    
    # Nếu user bấm button, hiển thị chat modal
    if st.session_state.get("chat_expanded", False):
        with st.container():
            st.markdown('<div class="chat-widget-container">', unsafe_allow_html=True)
            
            # Header
            st.markdown('<div class="chat-header">🤖 eMpTy AI - Tư vấn Sản phẩm</div>', unsafe_allow_html=True)
            
            # Chat messages area
            with st.container():
                st.markdown('<div class="chat-content">', unsafe_allow_html=True)
                
                # Hiển thị lịch sử chat
                messages_container = st.container()
                with messages_container:
                    for message in st.session_state.get("messages", []):
                        if message["role"] == "user":
                            st.markdown(
                                f'<div class="chat-message-user">{message["content"]}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="chat-message-ai">{message["content"]}</div>',
                                unsafe_allow_html=True
                            )
                
                # Input area
                col_input, col_btn = st.columns([4, 1])
                
                with col_input:
                    user_input = st.text_input(
                        "Nhập tin nhắn...",
                        key="chat_input",
                        label_visibility="collapsed",
                        placeholder="Hỏi về sản phẩm..."
                    )
                
                with col_btn:
                    send_btn = st.button("↓", key="send_chat_btn", help="Gửi tin nhắn")
                
                # Xử lý gửi tin nhắn
                if send_btn and user_input:
                    # Add user message
                    st.session_state.messages.append({
                        "role": "user",
                        "content": user_input
                    })
                    
                    # Get AI response
                    ai_response = get_ai_response(
                        user_input, 
                        st.session_state.messages,
                        gemini_available=st.session_state.get("gemini_available", False)
                    )
                    
                    # Add AI message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    
                    # Lưu lịch sử chat vào query params
                    import json
                    try:
                        st.query_params["chat_history"] = json.dumps(st.session_state.messages)
                    except Exception as e:
                        print(f"⚠️ Lỗi lưu chat_history: {e}")
                    
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Close button
            st.markdown('<div style="text-align: center; margin-top: 8px;">', unsafe_allow_html=True)
            if st.button("Đóng", key="close_chat_btn"):
                st.session_state.chat_expanded = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)




def display_ai_message_with_images(ai_response):
    """
    Hiển thị tin nhắn AI kèm hình ảnh sách được đề cập.
    
    Args:
        ai_response: Text phản hồi từ AI
    """
    # Hiển thị text của AI (Hiển thị toàn bộ câu trả lời, không cắt ngắn)
    st.write(f"**eMpTy AI:** {ai_response}")
    
    # Tìm các tiêu đề sách trong response (các text trong ngoặc kép)
    # Pattern: "Tên Sách" hoặc Tên Sách (độ dài >= 2)
    pattern = r'"([^"]{2,})"'  # Tìm text trong ngoặc kép, dài từ 2 ký tự trở lên
    book_titles = re.findall(pattern, ai_response)
    
    # Lấy hình ảnh cho mỗi sách
    if book_titles:
        st.markdown("#### 📱 Sản phẩm được đề cập:")
        
        # Tạo grid hiển thị sách
        cols = st.columns(2)
        book_count = 0
        
        # Các từ khóa thông dụng cần lọc bỏ nếu vô tình bị đặt trong ngoặc kép
        ignored_words = {
            'của', 'tác giả', 'author', 'một cuốn', 'sách', 'tập', 'bạn', 'tôi', 'mình', 
            'xin chào', 'hello', 'eMpty AI', 'tiểu thuyết', 'trinh thám', 'kinh tế'
        }
        
        for title in book_titles[:4]:  # Giới hạn 4 sách
            clean_title = title.strip()
            # Lọc bỏ những title không phải tên sách
            if len(clean_title) >= 2 and clean_title.lower() not in ignored_words:
                img_url = get_book_image(clean_title)
                
                if img_url:
                    with cols[book_count % 2]:
                        with st.container(border=True):
                            st.image(img_url, use_container_width=True, caption=clean_title[:30])
                            book_count += 1


def render_simple_floating_button():
    """
    Render nút floating chat tối giản.
    Khi click, hiển thị popover với chat interface.
    """
    # CSS cho button floating
    st.markdown("""
    <style>
    .floating-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Khởi tạo session state
    if "show_chat_popup" not in st.session_state:
        st.session_state.show_chat_popup = False
    
    # Button floating
    with st.columns([20, 1])[1]:
        pass
    
    # Sử dụng popover (Streamlit 1.16+)
    try:
        with st.popover("💬", help="Trợ lý AI tư vấn sản phẩm"):
            st.markdown("### 🤖 eMpTy AI - Tư vấn Sản phẩm")
            st.divider()
            
            # 1. Tạo placeholder cho chat messages ở phía trên form
            chat_placeholder = st.empty()
            
            # Input area using form
            st.divider()
            
            with st.form(key="chat_form", clear_on_submit=True):
                col_input, col_btn = st.columns([4, 1], gap="small")
                
                with col_input:
                    user_message = st.text_input(
                        "Nhập câu hỏi...",
                        placeholder="Hỏi về sản phẩm...",
                        label_visibility="collapsed",
                        key="user_message_input"
                    )
                
                with col_btn:
                    send_button = st.form_submit_button("📤", use_container_width=True)
                
                # Xử lý gửi tin nhắn
                if send_button and user_message and user_message.strip():
                    # Add message to history
                    st.session_state.messages.append({
                        "role": "user",
                        "content": user_message
                    })
                    
                    # Hiển thị spinner khi đang xử lý
                    with st.spinner("🤔 Đang suy nghĩ..."):
                        # Get AI response
                        ai_response = get_ai_response(
                            user_message, 
                            st.session_state.messages,
                            gemini_available=st.session_state.get("gemini_available", False)
                        )
                    
                    # Add AI response
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    
                    # Lưu lịch sử chat vào query params
                    import json
                    try:
                        st.query_params["chat_history"] = json.dumps(st.session_state.messages)
                    except Exception as e:
                        print(f"⚠️ Lỗi lưu chat_history: {e}")
                    
                    st.success("✅ Phản hồi hoàn tất!", icon="✅")

            # 2. Vẽ lịch sử chat vào placeholder (đã có tin nhắn mới nếu vừa gửi)
            messages = st.session_state.get("messages", [])
            with chat_placeholder.container(height=350, border=False):
                for msg in messages:
                    if msg["role"] == "user":
                        st.write(f"**Bạn:** {msg['content']}")
                    else:
                        # Hiển thị AI message với hình ảnh
                        display_ai_message_with_images(msg['content'])
    
    except Exception as e:
        st.warning(f"Không thể hiển thị chat widget: {str(e)}")
