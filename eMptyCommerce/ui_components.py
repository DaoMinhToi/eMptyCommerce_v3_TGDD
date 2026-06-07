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
            value=session_state.get('search_query', ''),
            placeholder="🔍  Nhập tên sách để tìm nội dung tương tự...",
            key="header_input_box",
            label_visibility="collapsed"
        )
    with h3:
        header_btn = st.button("Tìm kiếm", key="header_search_btn",
                               use_container_width=True)

    # Trigger search when button clicked OR when Enter pressed (input changed)
    should_search = False
    
    if header_btn and header_input:
        # User clicked the button
        should_search = True
    elif header_input and header_input != session_state.get('last_input', ''):
        # User pressed Enter (input value changed and is non-empty)
        should_search = True
    
    # Always track last input value
    session_state.last_input = header_input
    
    if should_search:
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
    from db_utils import add_to_cart

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
                    product_id = book.get('product_id', book.get('id'))
                    
                    card_html = render_book_card(
                        title=title,
                        category=cat,
                        rating=rating,
                        n_reviews=n_rev,
                        price=price,
                        cover_link=cover
                    )
                    st.markdown(card_html, unsafe_allow_html=True)
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🛒 Thêm", key=f"cat_cart_{product_id}", use_container_width=True):
                            add_to_cart(st.session_state.cart_id, product_id, 1)
                            st.success(f"✅ Đã thêm '{title[:15]}...'")
                    with col_btn2:
                        if st.button("💬 Review", key=f"cat_rev_{product_id}", use_container_width=True):
                            st.session_state["selected_book_for_reviews"] = product_id
                            st.session_state["should_scroll_to_top"] = True
                            st.rerun()


def render_hybrid_recommendations_grid(recommendations_df: pd.DataFrame, 
                                       cols_per_row: int = 5):
    """
    Render grid gợi ý Hybrid
    
    Args:
        recommendations_df: DataFrame gợi ý từ mô hình Hybrid
        cols_per_row: Số cột một hàng
    """
    from db_utils import add_to_cart
    
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
                product_id = book.get('product_id', book.get('id'))
                
                card_html = render_book_card_hybrid(
                    title=title,
                    category=category,
                    cover_link=cover,
                    score=score,
                    score_label="Điểm Hybrid"
                )
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Hàng nút Thêm / Đánh giá
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🛒 Thêm", key=f"warm_rec_cart_{product_id}", use_container_width=True):
                        add_to_cart(st.session_state.cart_id, product_id, 1)
                        st.success(f"✅ Đã thêm '{title[:15]}...'")
                with col_btn2:
                    if st.button("💬 Review", key=f"warm_rec_rev_{product_id}", use_container_width=True):
                        st.session_state["selected_book_for_reviews"] = product_id
                        st.session_state["should_scroll_to_top"] = True
                        st.rerun()


def render_cosine_search_results_grid(similar_books_df: pd.DataFrame, 
                                      cols_per_row: int = 5):
    """
    Render grid kết quả tìm kiếm Cosine Similarity
    
    Args:
        similar_books_df: DataFrame sách tương tự (có cột cosine_score)
        cols_per_row: Số cột một hàng
    """
    from db_utils import add_to_cart
    
    st.markdown("##### 📚 5 sách có nội dung tương tự nhất:")
    cols = st.columns(cols_per_row)
    
    for i, (_, book) in enumerate(similar_books_df.iterrows()):
        with cols[i]:
            title    = str(book.get('title','N/A'))
            category = str(book.get('category','N/A'))
            score    = float(book.get('cosine_score', 0))
            cover    = book.get('cover_link','')
            product_id = book.get('product_id', book.get('id'))
            
            card_html = render_book_card_hybrid(
                title=title,
                category=category,
                cover_link=cover,
                score=score,
                score_label="Độ tương đồng Cosine"
            )
            st.markdown(card_html, unsafe_allow_html=True)
            
            # Hàng nút Thêm / Đánh giá
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🛒 Thêm", key=f"search_rec_cart_{product_id}", use_container_width=True):
                    add_to_cart(st.session_state.cart_id, product_id, 1)
                    st.success(f"✅ Đã thêm '{title[:15]}...'")
            with col_btn2:
                if st.button("💬 Review", key=f"search_rec_rev_{product_id}", use_container_width=True):
                    st.session_state["selected_book_for_reviews"] = product_id
                    st.session_state["should_scroll_to_top"] = True
                    st.rerun()


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


def show_book_reviews(book_id: int, reviews: list[dict]):
    """
    Hiển thị đánh giá và bình luận của sách theo layout một trang duy nhất,
    phân trang 5 bình luận/trang, hỗ trợ Light/Dark mode.
    
    Args:
        book_id: ID của sách
        reviews: Danh sách các review, mỗi review là 1 dict chứa:
                 "ma_kh" (str), "so_sao" (int 1-5),
                 "tieu_de" (str | None), "noi_dung" (str | None), "ngay" (str | None)
    """
    # Hàm render sao theo yêu cầu kỹ thuật
    def render_stars(n):
        return "★" * n + "☆" * (5 - n)

    total = len(reviews)
    
    # CSS style cho HTML card bình luận hỗ trợ cả Light/Dark theme thông qua CSS variables
    st.markdown("<style>"
                ":root {"
                "  --review-card-bg: #f9f9f9;"
                "  --review-card-color: #333333;"
                "}"
                "[data-theme='dark'] {"
                "  --review-card-bg: #1e1e1e;"
                "  --review-card-color: #f9f9f9;"
                "}"
                "@media (prefers-color-scheme: dark) {"
                "  :root {"
                "    --review-card-bg: #1e1e1e;"
                "    --review-card-color: #f9f9f9;"
                "  }"
                "}"
                "</style>", unsafe_allow_html=True)

    # 1. PHẦN TỔNG QUAN (nằm trên cùng - dùng st.columns(2))
    col_left, col_right = st.columns(2)
    
    if total > 0:
        avg_rating = sum(r.get("so_sao", 0) for r in reviews) / total
        
        # Cột trái: Điểm trung bình lớn + hàng sao + tổng số đánh giá
        with col_left:
            st.markdown(f'<div style="text-align: center; padding: 15px 0;">'
                        f'<h1 style="font-size: 64px; margin: 0; color: #f5a623; font-weight: bold; line-height: 1;">{avg_rating:.1f}</h1>'
                        f'<div style="font-size: 24px; color: #f5a623; margin: 8px 0;">{render_stars(int(round(avg_rating)))}</div>'
                        f'<div style="font-size: 14px; color: var(--review-card-color, #666);">({total} đánh giá)</div>'
                        f'</div>', unsafe_allow_html=True)
            
        # Cột phải: Biểu đồ bar ngang cho từng mức sao (5★ → 1★)
        with col_right:
            star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            for r in reviews:
                s = r.get("so_sao", 0)
                if s in star_counts:
                    star_counts[s] += 1
            
            # Vẽ biểu đồ bar ngang dùng HTML/CSS inline
            bar_html = "<div style='display: flex; flex-direction: column; gap: 8px; padding-top: 5px;'>"
            for star in range(5, 0, -1):
                count_s = star_counts[star]
                pct_s = (count_s / total) * 100
                bar_html += f'<div style="display: flex; align-items: center; font-size: 13px;">' \
                            f'<span style="width: 25px; font-weight: bold; color: #f5a623;">{star}★</span>' \
                            f'<div style="flex-grow: 1; background-color: rgba(128, 128, 128, 0.2); height: 10px; border-radius: 5px; margin: 0 10px; overflow: hidden;">' \
                            f'<div style="background-color: #f5a623; width: {pct_s}%; height: 100%; border-radius: 5px;"></div>' \
                            f'</div>' \
                            f'<span style="width: 50px; text-align: right; color: var(--review-card-color, #666);">{count_s} ({pct_s:.0f}%)</span>' \
                            f'</div>'
            bar_html += "</div>"
            st.markdown(bar_html, unsafe_allow_html=True)
    else:
        # Xử lý khi chưa có đánh giá nào
        with col_left:
            st.markdown(f'<div style="text-align: center; padding: 15px 0;">'
                        f'<h1 style="font-size: 64px; margin: 0; color: #ccc; font-weight: bold; line-height: 1;">0.0</h1>'
                        f'<div style="font-size: 24px; color: #ccc; margin: 8px 0;">{render_stars(0)}</div>'
                        f'<div style="font-size: 14px; color: var(--review-card-color, #999);">({total} đánh giá)</div>'
                        f'</div>', unsafe_allow_html=True)
            
        with col_right:
            bar_html = "<div style='display: flex; flex-direction: column; gap: 8px; padding-top: 5px;'>"
            for star in range(5, 0, -1):
                bar_html += f'<div style="display: flex; align-items: center; font-size: 13px;">' \
                            f'<span style="width: 25px; font-weight: bold; color: #ccc;">{star}★</span>' \
                            f'<div style="flex-grow: 1; background-color: rgba(128, 128, 128, 0.2); height: 10px; border-radius: 5px; margin: 0 10px; overflow: hidden;">' \
                            f'<div style="background-color: #ccc; width: 0%; height: 100%; border-radius: 5px;"></div>' \
                            f'</div>' \
                            f'<span style="width: 50px; text-align: right; color: #ccc;">0 (0%)</span>' \
                            f'</div>'
            bar_html += "</div>"
            st.markdown(bar_html, unsafe_allow_html=True)

    st.markdown("---")

    # 2. PHẦN BÌNH LUẬN (nằm dưới, không dùng tab riêng)
    st.markdown(f"### 💬 Bình luận từ khách hàng ({total})")

    if total == 0:
        st.info("📚 Quyển sách này chưa có bình luận nào từ khách hàng.")
        return

    # Khởi tạo st.session_state cho phân trang bình luận
    # Reset trang nếu đổi book_id
    if "review_book_id" not in st.session_state or st.session_state["review_book_id"] != book_id:
        st.session_state["review_book_id"] = book_id
        st.session_state["review_page"] = 1
    
    if "review_page" not in st.session_state:
        st.session_state["review_page"] = 1

    limit = 5
    max_pages = max(1, (total + limit - 1) // limit)
    
    # Clip trang hiện tại trong khoảng hợp lệ
    if st.session_state["review_page"] > max_pages:
        st.session_state["review_page"] = max_pages
    if st.session_state["review_page"] < 1:
        st.session_state["review_page"] = 1

    start_idx = (st.session_state["review_page"] - 1) * limit
    end_idx = start_idx + limit
    page_reviews = reviews[start_idx:end_idx]

    # Hiển thị từng bình luận dưới dạng card HTML
    for r in page_reviews:
        ma_kh = r.get("ma_kh", "Ẩn danh")
        so_sao = r.get("so_sao", 5)
        tieu_de = r.get("tieu_de")
        noi_dung = r.get("noi_dung")
        ngay = r.get("ngay")
        
        # Tiêu đề bình luận
        if tieu_de and str(tieu_de).strip() and str(tieu_de) != 'nan':
            title_html = f"<strong>{tieu_de}</strong>"
        else:
            title_html = "<span style='font-style: italic; color: #888;'>Không có tiêu đề</span>"
            
        # Nội dung bình luận
        content_html = ""
        if noi_dung and str(noi_dung).strip() and str(noi_dung) != 'nan':
            content_html = f"<div style='margin-top: 6px; font-size: 14px;'>{noi_dung}</div>"
            
        # Ngày bình luận
        date_html = ""
        if ngay and str(ngay).strip() and str(ngay) != 'nan':
            date_html = f"<div style='text-align: right; font-size: 11px; color: #999; margin-top: 6px;'>📅 {ngay}</div>"

        # HTML card dùng CSS inline theo đúng yêu cầu
        card_html = f'<div class="review-card" style="background: var(--review-card-bg, #f9f9f9); border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; border-left: 3px solid #f5a623;">' \
                    f'<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(128,128,128,0.1); padding-bottom: 4px; margin-bottom: 6px;">' \
                    f'<span style="color: #f5a623; font-weight: bold; font-size: 14px;">{render_stars(so_sao)}</span>' \
                    f'<span style="color: #888; font-size: 12px; font-weight: 500;">👤 KH: {ma_kh}</span>' \
                    f'</div>' \
                    f'<div style="color: var(--review-card-color, #333333);">' \
                    f'{title_html}' \
                    f'{content_html}' \
                    f'</div>' \
                    f'{date_html}' \
                    f'</div>'
        st.markdown(card_html, unsafe_allow_html=True)

    # Phân trang: Nút Trước / Tiếp
    if max_pages > 1:
        st.write("") # Spacer
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Trước", key=f"prev_rev_{book_id}", disabled=(st.session_state["review_page"] <= 1), use_container_width=True):
                st.session_state["review_page"] -= 1
                st.rerun()
        with col_info:
            st.markdown(f"<div style='text-align: center; line-height: 2.2; font-size: 14px; color: var(--review-card-color, #333);'>Trang {st.session_state['review_page']} / {max_pages}</div>", unsafe_allow_html=True)
        with col_next:
            if st.button("Tiếp →", key=f"next_rev_{book_id}", disabled=(st.session_state["review_page"] >= max_pages), use_container_width=True):
                st.session_state["review_page"] += 1
                st.rerun()

