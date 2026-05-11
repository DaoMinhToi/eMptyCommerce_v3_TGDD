"""
UI Components - Các hàm render component giao diện
Chứa logic UI nhưng không chứa logic chức năng chính
"""

import streamlit as st
import pandas as pd
import os
from styles import render_book_card, render_book_card_hybrid


def render_search_bar(session_state):
    """Render thanh tìm kiếm dưới header"""
    h1, h2, h3 = st.columns([1, 5, 1])
    with h2:
        header_input = st.text_input(
            "search",
            placeholder="🔍  Nhập tên sách để tìm nội dung tương tự...",
            key="header_input_box",
            label_visibility="collapsed"
        )
    with h3:
        header_btn = st.button("Tìm kiếm", key="header_search_btn",
                               use_container_width=True)

    if header_btn and header_input:
        session_state.search_query = header_input
        session_state.do_search = True
        st.rerun()


def render_category_books_grid(books_df: pd.DataFrame, DATA_DIR: str, 
                               cols_per_row: int = 5):
    """
    Render grid sách từ một danh mục
    
    Args:
        books_df: DataFrame của sách từ danh mục
        DATA_DIR: Thư mục dữ liệu
        cols_per_row: Số cột một hàng
    """
    st.caption(f"📊 Tìm thấy {len(books_df)} sách · Hiển thị top 10")
    
    if not books_df.empty:
        for row_start in range(0, len(books_df), cols_per_row):
            row_data = books_df.iloc[row_start:row_start+cols_per_row]
            cols = st.columns(cols_per_row)
            for i, (_, book) in enumerate(row_data.iterrows()):
                with cols[i]:
                    title   = str(book.get('title','N/A'))
                    cat     = str(book.get('category','N/A'))
                    rating  = float(book.get('avg_rating', 0))
                    n_rev   = int(book.get('n_review', 0))
                    cover   = book.get('cover_link','')
                    price   = int(book.get('current_price', 0))
                    
                    card_html = render_book_card(
                        title=title,
                        category=cat,
                        rating=rating,
                        n_reviews=n_rev,
                        price=price,
                        cover_link=cover
                    )
                    st.markdown(card_html, unsafe_allow_html=True)


def render_hybrid_recommendations_grid(recommendations_df: pd.DataFrame, 
                                       cols_per_row: int = 5):
    """
    Render grid gợi ý Hybrid
    
    Args:
        recommendations_df: DataFrame gợi ý từ mô hình Hybrid
        cols_per_row: Số cột một hàng
    """
    st.caption(f"Hybrid Model (60% CF + 40% Content-based)")
    
    rec_list = recommendations_df.reset_index(drop=True)
    
    for row_start in range(0, len(rec_list), cols_per_row):
        row_data = rec_list.iloc[row_start:row_start+cols_per_row]
        cols = st.columns(cols_per_row)
        for i, (_, book) in enumerate(row_data.iterrows()):
            with cols[i]:
                title    = str(book.get('title', 'N/A'))
                category = str(book.get('category', 'N/A'))
                score    = book.get('hybrid_score', book.get('score', 0))
                cover    = book.get('cover_link', '')
                
                card_html = render_book_card_hybrid(
                    title=title,
                    category=category,
                    cover_link=cover,
                    score=score,
                    score_label="Điểm Hybrid"
                )
                st.markdown(card_html, unsafe_allow_html=True)


def render_cosine_search_results_grid(similar_books_df: pd.DataFrame, 
                                      cols_per_row: int = 5):
    """
    Render grid kết quả tìm kiếm Cosine Similarity
    
    Args:
        similar_books_df: DataFrame sách tương tự (có cột cosine_score)
        cols_per_row: Số cột một hàng
    """
    st.markdown("##### 📚 5 sách có nội dung tương tự nhất:")
    cols = st.columns(cols_per_row)
    
    for i, (_, book) in enumerate(similar_books_df.iterrows()):
        with cols[i]:
            title    = str(book.get('title','N/A'))
            category = str(book.get('category','N/A'))
            score    = float(book.get('cosine_score', 0))
            cover    = book.get('cover_link','')
            
            card_html = render_book_card_hybrid(
                title=title,
                category=category,
                cover_link=cover,
                score=score,
                score_label="Độ tương đồng Cosine"
            )
            st.markdown(card_html, unsafe_allow_html=True)


def render_customer_info_metrics(rated_books_count: int, avg_rating: float):
    """
    Render thông tin khách hàng dạng metrics
    
    Args:
        rated_books_count: Số sách đã đánh giá
        avg_rating: Điểm đánh giá trung bình
    """
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Đã đánh giá", rated_books_count)
    with col2:
        st.metric("⭐ Trung bình", f"{avg_rating:.2f}")
    with col3:
        st.metric("🎯 Sở thích", "Sách yêu thích" if avg_rating >= 4 else "Đa dạng")
    
    st.markdown("---")


def render_search_result_container(final_query: str, book_df: pd.DataFrame, 
                                   tfidf_matrix, vectorizer, 
                                   find_similar_books_func):
    """
    Render container kết quả tìm kiếm ngay sau header
    
    Args:
        final_query: Từ khóa tìm kiếm
        book_df: DataFrame sách đầy đủ
        tfidf_matrix: Ma trận TF-IDF
        vectorizer: Vectorizer TF-IDF
        find_similar_books_func: Hàm tìm sách tương tự
    """
    with st.spinner(f"Đang tìm sách tương tự với '{final_query}'..."):
        source_book, similar_books, error = find_similar_books_func(
            final_query, book_df, tfidf_matrix, top_n=5
        )
    
    if error:
        st.warning(f"⚠️ {error}")
    else:
        st.success(f"✅ Tìm thấy sách: **{source_book['title']}**")
        st.markdown(f"📂 Danh mục: *{source_book.get('category','N/A')}*")
        
        render_cosine_search_results_grid(similar_books, cols_per_row=5)
        st.markdown("---")
