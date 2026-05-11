"""
Tất cả CSS và HTML styles cho eMpTyCommerce
Tách biệt khỏi logic chức năng
"""

import streamlit as st


def apply_header_styles():
    """Áp dụng CSS cho header và layout"""
    st.markdown("""
<style>
[data-testid="stHeader"] { display:none !important; }
[data-testid="stToolbar"] { display:none !important; }
.block-container { padding-top: 80px !important; }

/* Header bar */
div[data-testid="stAppViewContainer"] > div:first-child { margin-top: 0; }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render header bar cố định ở đầu trang"""
    st.markdown("""
<div style="
    position:fixed; top:0; left:0; right:0; z-index:9999;
    background:linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding:0 24px;
    height:64px;
    display:flex;
    align-items:center;
    gap:20px;
    box-shadow:0 2px 20px rgba(0,0,0,0.3);
    border-bottom: 1px solid rgba(255,255,255,0.1);
">
    <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
        <span style="font-size:24px;">🎯</span>
        <div>
            <div style="color:white;font-size:16px;font-weight:700;
                        letter-spacing:0.5px;line-height:1.2;">
                eMpTyCommerce
            </div>
            <div style="color:rgba(255,255,255,0.5);font-size:10px;">
                Hệ thống gợi ý sách thông minh
            </div>
        </div>
    </div>
    <div style="width:1px;height:36px;background:rgba(255,255,255,0.15);
                flex-shrink:0;"></div>
    <div style="background:rgba(108,99,255,0.3);border:1px solid rgba(108,99,255,0.6);
                border-radius:20px;padding:4px 12px;flex-shrink:0;">
        <span style="color:#a78bfa;font-size:11px;font-weight:500;">
            🤖 Hybrid AI Model
        </span>
    </div>
    <div style="flex:1;"></div>
    <div style="display:flex;gap:16px;flex-shrink:0;">
        <div style="text-align:center;">
            <div style="color:white;font-size:14px;font-weight:700;">1.657</div>
            <div style="color:rgba(255,255,255,0.5);font-size:10px;">Đầu sách</div>
        </div>
        <div style="text-align:center;">
            <div style="color:white;font-size:14px;font-weight:700;">77.660</div>
            <div style="color:rgba(255,255,255,0.5);font-size:10px;">Khách hàng</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def render_book_card(title: str, category: str, rating: float, n_reviews: int, 
                     price: int, cover_link: str, score=None, score_label=""):
    """
    Render một card sách đẹp
    
    Args:
        title: Tên sách
        category: Danh mục
        rating: Điểm rating
        n_reviews: Số lượt đánh giá
        price: Giá tiền
        cover_link: Link ảnh bìa
        score: Điểm (dùng cho hybrid/cosine)
        score_label: Label cho score
    """
    import pandas as pd
    
    short_title = (title[:40] + '...') if len(title) > 40 else title
    
    if pd.notna(cover_link) and str(cover_link).startswith('http'):
        img_html = f'<img src="{cover_link}" style="width:100%;height:200px;object-fit:cover;border-radius:8px 8px 0 0;">'
    else:
        img_html = '<div style="width:100%;height:200px;background:#f0f0f0;border-radius:8px 8px 0 0;display:flex;align-items:center;justify-content:center;font-size:36px;">📚</div>'
    
    return f"""
    <div style="border:1px solid #e0e0e0;border-radius:12px;
                overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                background:white;margin-bottom:8px;text-align:center;">
        {img_html}
        <div style="padding:10px;">
            <div style="font-size:12px;font-weight:600;color:#1a1a2e;
                        min-height:36px;line-height:1.4;margin-bottom:4px;">
                {short_title}
            </div>
            <div style="font-size:11px;color:#6c757d;
                        font-style:italic;margin-bottom:6px;">
                📂 {str(category)[:25]}
            </div>
            <div style="border-top:1px solid #f0f0f0;padding-top:8px;">
                <div style="font-size:15px;font-weight:700;color:#e74c3c;">
                    {price:,} ₫
                </div>
                <div style="font-size:11px;color:#f39c12;">
                    ⭐ {rating:.1f} · {n_reviews:,} đánh giá
                </div>
            </div>
        </div>
    </div>
    """


def render_book_card_hybrid(title: str, category: str, cover_link: str, 
                           score: float, score_label="Điểm Hybrid"):
    """
    Render book card cho Hybrid recommendations
    
    Args:
        title: Tên sách
        category: Danh mục
        cover_link: Link ảnh bìa
        score: Điểm hybrid/similarity
        score_label: Label cho score
    """
    import pandas as pd
    
    short_title = (title[:40] + '...') if len(title) > 40 else title
    
    if pd.notna(cover_link) and str(cover_link).startswith('http'):
        img_html = f'<img src="{cover_link}" style="width:100%;height:180px;object-fit:cover;border-radius:8px;">'
    else:
        img_html = '<div style="width:100%;height:180px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:36px;">📚</div>'
    
    try:
        score_f = float(score)
        score_display = f"{score_f*100:.0f}%" if score_f <= 1 else f"{score_f:.2f}"
    except:
        score_display = "N/A"
    
    return f"""
    <div style="border:1px solid #e0e0e0;border-radius:12px;padding:12px;
                background:white;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                text-align:center;height:100%;">
        {img_html}
        <div style="font-size:12px;font-weight:600;color:#1a1a2e;
                    margin-top:10px;min-height:36px;line-height:1.4;">
            {short_title}
        </div>
        <div style="font-size:11px;color:#6c757d;margin:6px 0;">
            📂 {str(category)[:25]}
        </div>
        <div style="border-top:1px solid #f0f0f0;padding-top:8px;margin-top:8px;">
            <div style="font-size:22px;font-weight:700;color:#6C63FF;">
                {score_display}
            </div>
            <div style="font-size:10px;color:#999;">
                {score_label}
            </div>
        </div>
    </div>
    """


def render_footer():
    """Render footer"""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
        <p><small>💡 Hybrid Recommendation System | Cold-Start Problem Solution</small></p>
        <p><small>Powered by: Scikit-Learn (TF-IDF) + Surprise (SVD) + Streamlit</small></p>
        </div>
        """,
        unsafe_allow_html=True
    )
