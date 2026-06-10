"""
Module để render Shopping Cart trên giao diện Streamlit
Cung cấp các hàm để hiển thị giỏ hàng, thêm/xóa sản phẩm, v.v.
"""

from typing import Optional
import streamlit as st
import pandas as pd
from db_utils import (
    get_cart_items, add_to_cart, remove_from_cart, 
    update_quantity, clear_cart, get_cart_summary,
    create_order, update_order_payment_status,
    generate_vietqr, verify_sepay_transaction,
    generate_order_id, get_customer_orders
)


def render_cart_header(cart_id: int):
    """
    Render tiêu đề giỏ hàng với số lượng sản phẩm.
    
    Args:
        cart_id: ID của giỏ hàng
    """
    summary = get_cart_summary(cart_id)
    total_items = summary['total_items']
    total_quantity = summary['total_quantity']
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader("🛒 Giỏ hàng của bạn")
    with col2:
        st.metric("Sản phẩm", total_items)
    with col3:
        st.metric("Tổng lượng", total_quantity)


def render_cart_items_table(cart_id: int) -> pd.DataFrame:
    """
    Render bảng danh sách sản phẩm trong giỏ hàng.
    
    Args:
        cart_id: ID của giỏ hàng
    
    Returns:
        DataFrame chứa danh sách sản phẩm
    """
    items_df = get_cart_items(cart_id)
    
    if items_df.empty:
        st.info("📭 Giỏ hàng của bạn còn trống. Hãy thêm sản phẩm!")
        return items_df
    
    # Chuẩn bị dữ liệu để hiển thị
    display_df = items_df[[
        'product_id', 'title', 'category', 'quantity', 'added_at'
    ]].copy()
    
    display_df.columns = [
        'Product ID', 'Tên sản phẩm', 'Thể loại', 'Số lượng', 'Thêm lúc'
    ]
    
    st.dataframe(display_df, use_container_width=True)
    
    return items_df


def render_cart_items_expandable(cart_id: int):
    """
    Render sản phẩm trong giỏ hàng dạng expandable (mở rộng) với hộp chọn thanh toán riêng.
    Cho phép quản lý từng sản phẩm.
    
    Args:
        cart_id: ID của giỏ hàng
    """
    items_df = get_cart_items(cart_id)
    
    if items_df.empty:
        st.info("📭 Giỏ hàng của bạn còn trống.")
        return
        
    # Khởi tạo trạng thái chọn sản phẩm
    if "selected_cart_items" not in st.session_state:
        st.session_state.selected_cart_items = {}
        
    for _, row in items_df.iterrows():
        pid = int(row['product_id'])
        if pid not in st.session_state.selected_cart_items:
            st.session_state.selected_cart_items[pid] = True
            
    # Định nghĩa callback khi bấm "Chọn tất cả"
    def toggle_all_items():
        val = st.session_state.select_all_cart_items
        for _, r in items_df.iterrows():
            p_id = int(r['product_id'])
            st.session_state.selected_cart_items[p_id] = val
            st.session_state[f"select_{p_id}"] = val

    # Định nghĩa callback khi chọn từng sản phẩm
    def on_item_change(p_id: int):
        st.session_state.selected_cart_items[p_id] = st.session_state[f"select_{p_id}"]
            
    # Checkbox chọn tất cả
    col_all_select, col_all_label = st.columns([1, 15])
    with col_all_select:
        all_selected = all(st.session_state.selected_cart_items.get(int(row['product_id']), True) for _, row in items_df.iterrows())
        st.session_state.select_all_cart_items = all_selected
        st.checkbox(
            "Chọn tất cả",
            key="select_all_cart_items",
            on_change=toggle_all_items,
            label_visibility="collapsed"
        )
    with col_all_label:
        st.markdown("**Chọn tất cả để thanh toán**")
        
    st.write("### Chi tiết sản phẩm")
    
    for idx, item in items_df.iterrows():
        pid = int(item['product_id'])
        col_select, col_exp = st.columns([1, 15])
        
        with col_select:
            st.write("") # Spacer để căn giữa checkbox theo chiều dọc
            st.write("")
            
            # Khởi tạo giá trị trong session state nếu chưa có để đồng nhất với checkbox
            if f"select_{pid}" not in st.session_state:
                st.session_state[f"select_{pid}"] = st.session_state.selected_cart_items.get(pid, True)
                
            st.checkbox(
                "Chọn",
                key=f"select_{pid}",
                on_change=on_item_change,
                args=(pid,),
                label_visibility="collapsed"
            )
            
        with col_exp:
            price = int(item.get('current_price', 50000))
            qty = int(item['quantity'])
            with st.expander(f"📱 {item['title']}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**ID:** {item['product_id']}")
                    st.write(f"**Thể loại:** {item['category']}")
                    st.write(f"**Đơn giá:** {price:,}đ")
                    st.write(f"**Thêm lúc:** {item['added_at']}")
                
                with col2:
                    st.write(f"**Số lượng:** {qty}")
                    st.write(f"**Thành tiền:** {price * qty:,}đ")
                
                with col3:
                    # Nút cập nhật số lượng
                    new_qty = st.number_input(
                        f"Cập nhật số lượng",
                        min_value=0,
                        value=item['quantity'],
                        key=f"qty_{item['cart_item_id']}_{idx}"
                    )
                    
                    if new_qty != item['quantity']:
                        update_quantity(item['cart_item_id'], new_qty)
                        st.rerun()
                
                # Nút xóa sản phẩm
                if st.button(f"❌ Xóa khỏi giỏ", key=f"remove_{item['cart_item_id']}_{idx}"):
                    remove_from_cart(item['cart_item_id'])
                    # Dọn dẹp session state khi xóa sản phẩm
                    if pid in st.session_state.selected_cart_items:
                        del st.session_state.selected_cart_items[pid]
                    if f"select_{pid}" in st.session_state:
                        del st.session_state[f"select_{pid}"]
                    st.success(f"Đã xóa {item['title']} khỏi giỏ!")
                    st.rerun()


def render_cart_actions(cart_id: int):
    """
    Render các nút hành động cho giỏ hàng (Xóa tất cả, Thanh toán, v.v.).
    
    Args:
        cart_id: ID của giỏ hàng
    """
    st.write("### Hành động")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Xóa tất cả", use_container_width=True):
            if st.session_state.get('confirm_clear_cart', False):
                clear_cart(cart_id)
                st.success("✓ Đã xóa tất cả sản phẩm trong giỏ!")
                st.session_state.confirm_clear_cart = False
                st.rerun()
            else:
                st.session_state.confirm_clear_cart = True
                st.warning("⚠️ Nhấn lại để xác nhận xóa tất cả")
    
    with col2:
        # Kiểm tra xem có ít nhất một sản phẩm được chọn hay không
        selected_pids = [pid for pid, val in st.session_state.get("selected_cart_items", {}).items() if val]
        items_df = get_cart_items(cart_id)
        selected_items_in_cart = items_df[items_df['product_id'].isin(selected_pids)] if not items_df.empty else pd.DataFrame()
        checkout_disabled = selected_items_in_cart.empty
        
        if st.button("💳 Thanh toán", use_container_width=True, disabled=checkout_disabled, help="Vui lòng chọn ít nhất một sản phẩm để thanh toán" if checkout_disabled else None):
            st.session_state.view = "checkout"
            # Reset trạng thái order của phiên checkout mới
            if 'checkout_order_id' in st.session_state:
                del st.session_state.checkout_order_id
            if 'checkout_order_created' in st.session_state:
                del st.session_state.checkout_order_created
            if 'checkout_success_order_id' in st.session_state:
                del st.session_state.checkout_success_order_id
            if 'checkout_success_amount' in st.session_state:
                del st.session_state.checkout_success_amount
            if 'checkout_success_method' in st.session_state:
                del st.session_state.checkout_success_method
            st.rerun()
    
    with col3:
        if st.button("🔄 Tiếp tục mua", use_container_width=True):
            st.session_state.view = "shopping"
            st.rerun()


def render_shopping_cart_page(cart_id: int, book_data: pd.DataFrame):
    """
    Render trang giỏ hàng hoàn chỉnh.
    
    Args:
        cart_id: ID của giỏ hàng
        book_data: DataFrame chứa dữ liệu tất cả sách
    """
    st.title("🛒 Giỏ hàng")
    
    # Render tiêu đề giỏ hàng
    render_cart_header(cart_id)
    
    st.divider()
    
    # Render danh sách sản phẩm
    items_df = get_cart_items(cart_id)
    
    if not items_df.empty:
        st.write("### Danh sách sản phẩm")
        render_cart_items_expandable(cart_id)
        
        st.divider()
        
        # Lọc danh sách sản phẩm được chọn để hiển thị thông số tổng tiền
        selected_pids = [pid for pid, val in st.session_state.get("selected_cart_items", {}).items() if val]
        selected_items = items_df[items_df['product_id'].isin(selected_pids)]
        
        selected_total_items = len(selected_items)
        selected_total_qty = int(selected_items['quantity'].sum()) if not selected_items.empty else 0
        
        if not selected_items.empty and 'current_price' not in selected_items.columns:
            selected_items['current_price'] = 50000
        selected_total_price = int((selected_items['current_price'] * selected_items['quantity']).sum()) if not selected_items.empty else 0
        
        # Hiển thị tóm tắt giỏ hàng (chỉ tính các sản phẩm được chọn để thanh toán)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sản phẩm đã chọn", f"{selected_total_items} / {len(items_df)}")
        with col2:
            st.metric("Tổng số lượng", selected_total_qty)
        with col3:
            st.metric("Tổng tiền thanh toán", f"{selected_total_price:,}đ")
    else:
        st.info("📭 Giỏ hàng của bạn còn trống")
        st.write("Hãy thêm sản phẩm vào giỏ hàng!")
    
    st.divider()
    
    # Nút hành động
    render_cart_actions(cart_id)


def render_cart_sidebar(cart_id: int):
    """
    Render hiển thị giỏ hàng ở sidebar (compact).
    
    Args:
        cart_id: ID của giỏ hàng
    """
    summary = get_cart_summary(cart_id)
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("🛒 Giỏ hàng")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Sản phẩm", summary['total_items'])
        with col2:
            st.metric("Tổng lượng", summary['total_quantity'])
        
        if st.button("📋 Xem chi tiết", use_container_width=True):
            st.session_state.view = "cart"
        if st.button("📜 Lịch sử mua hàng", use_container_width=True):
            st.session_state.view = "orders"
        
        st.markdown("---")


def record_purchase_and_retrain(customer_id: Optional[int], items_df: pd.DataFrame):
    """
    Ghi nhận tương tác PURCHASE (5.0 sao) cho các sách đã thanh toán và retrain mô hình.
    """
    if customer_id is None or items_df.empty:
        return
    
    try:
        from db_utils import add_user_interaction
        for _, row in items_df.iterrows():
            product_id = int(row['product_id'])
            add_user_interaction(customer_id, product_id, 'PURCHASE', 5.0)
            
        recommender_instance = st.session_state.get('recommender')
        if recommender_instance is not None:
            recommender_instance.update_and_retrain()
        st.session_state.warm_recommendations = None
    except Exception as e:
        print(f"❌ Lỗi ghi nhận tương tác PURCHASE và retrain: {e}")


def render_checkout_page(cart_id: int, book_data: pd.DataFrame):
    """
    Render trang thanh toán (Checkout) hoàn chỉnh.
    """
    # 1. Kiểm tra nếu đã đặt hàng thành công
    if st.session_state.get('checkout_success_order_id'):
        order_id = st.session_state.checkout_success_order_id
        amount = st.session_state.get('checkout_success_amount', 0)
        method = st.session_state.get('checkout_success_method', 'COD')
        
        st.balloons()
        
        st.markdown(f"""
        <div style="background-color: #d4edda; color: #155724; padding: 24px; border-radius: 12px; border: 1px solid #c3e6cb; margin-bottom: 24px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div style="font-size: 64px; margin-bottom: 12px;">🎉</div>
            <h2 style="margin: 0 0 12px 0; color: #155724;">Đặt hàng thành công!</h2>
            <p style="font-size: 16px; margin: 0;">Cảm ơn bạn đã mua sắm tại eMpTyCommerce. Đơn hàng của bạn đã được ghi nhận.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Hiển thị thông tin đơn hàng trong card premium
        st.markdown(f"""
        <div style="background-color: #ffffff; padding: 24px; border-radius: 12px; border: 1px solid #e0e0e0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 24px;">
            <h4 style="margin: 0 0 16px 0; border-bottom: 1px solid #eee; padding-bottom: 8px; color: #333;">📋 CHI TIẾT ĐƠN HÀNG</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 15px;">
                <tr>
                    <td style="padding: 8px 0; color: #666; font-weight: bold;">Mã đơn hàng:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #007bff;">{order_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Tổng số tiền:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #e74c3c;">{amount:,}đ</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Phương thức thanh toán:</td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold;">{"Thanh toán khi nhận hàng (COD)" if method == 'COD' else "Chuyển khoản ngân hàng tự động (SePay)"}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Trạng thái thanh toán:</td>
                    <td style="padding: 8px 0; text-align: right;"><span style="background-color: {'#ffeeba' if method == 'COD' else '#d4edda'}; color: {'#856404' if method == 'COD' else '#155724'}; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">{'Chờ thanh toán (COD)' if method == 'COD' else 'Đã thanh toán (Paid)'}</span></td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🛍️ Tiếp tục mua sắm", use_container_width=True, type="primary"):
            # Reset states
            del st.session_state.checkout_success_order_id
            if 'checkout_success_amount' in st.session_state:
                del st.session_state.checkout_success_amount
            if 'checkout_success_method' in st.session_state:
                del st.session_state.checkout_success_method
            if 'checkout_order_id' in st.session_state:
                del st.session_state.checkout_order_id
            if 'checkout_order_created' in st.session_state:
                del st.session_state.checkout_order_created
            st.session_state.view = "shopping"
            st.rerun()
        return

    # 2. Lấy giỏ hàng hiện tại và lọc theo sản phẩm được chọn
    all_items_df = get_cart_items(cart_id)
    selected_pids = [pid for pid, val in st.session_state.get("selected_cart_items", {}).items() if val]
    items_df = all_items_df[all_items_df['product_id'].isin(selected_pids)] if not all_items_df.empty else pd.DataFrame()
    
    if items_df.empty:
        st.warning("⚠️ Chưa chọn sản phẩm nào để thanh toán! Vui lòng quay lại giỏ hàng.")
        if st.button("🛒 Quay lại giỏ hàng"):
            st.session_state.view = "cart"
            st.rerun()
        return

    # 3. Tính toán tổng tiền
    if 'current_price' not in items_df.columns:
        items_df['current_price'] = 50000
    
    total_amount = int((items_df['current_price'] * items_df['quantity']).sum())

    # Giao diện chính
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("⬅️ Quay lại giỏ hàng", use_container_width=True):
            st.session_state.view = "cart"
            st.rerun()
            
    st.title("💳 Thanh toán đơn hàng")
    st.markdown("Vui lòng kiểm tra lại thông tin đơn hàng và lựa chọn phương thức thanh toán phù hợp.")
    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("📋 Tóm tắt đơn hàng")
        
        for idx, row in items_df.iterrows():
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #f0f0f0;">
                <div>
                    <span style="font-weight: bold; color: #333;">{row['title']}</span>
                    <br/>
                    <span style="font-size: 13px; color: #666;">Thể loại: {row['category']}</span>
                </div>
                <div style="text-align: right;">
                    <span style="font-weight: bold; color: #000;">{row['current_price']:,}đ</span> x {row['quantity']}
                    <br/>
                    <span style="font-weight: bold; color: #e74c3c;">{(row['current_price'] * row['quantity']):,}đ</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 12px; background-color: #f9f9f9; border-radius: 8px; margin-top: 16px;">
            <span style="font-size: 18px; font-weight: bold; color: #333;">Tổng tiền cần thanh toán:</span>
            <span style="font-size: 22px; font-weight: bold; color: #e74c3c;">{total_amount:,}đ</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        st.subheader("⚙️ Chọn phương thức thanh toán")
        payment_method = st.radio(
            "Phương thức thanh toán:",
            [
                "💵 Thanh toán khi nhận hàng (COD)",
                "🏦 Chuyển khoản ngân hàng tự động qua SePay (VietQR)"
            ],
            key="payment_method_radio"
        )

    with col_right:
        st.subheader("🛒 Tiến hành thanh toán")
        
        # Xử lý COD
        if "COD" in payment_method:
            st.info("💡 Bạn sẽ thanh toán số tiền đơn hàng khi nhân viên giao hàng đến nhà.")
            st.markdown(f"""
            <div style="background-color: #f1f3f5; padding: 16px; border-radius: 8px; border: 1px solid #dee2e6; margin-bottom: 16px;">
                <p style="margin: 0; font-size: 14px; color: #495057;">
                    <b>Hình thức:</b> COD (Thanh toán khi nhận hàng)<br/>
                    <b>Số tiền:</b> <span style="color:#e74c3c; font-weight:bold;">{total_amount:,}đ</span><br/>
                    <b>Phí giao hàng:</b> Miễn phí 🎁
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✅ Xác nhận đặt hàng COD", type="primary", use_container_width=True):
                with st.spinner("⏳ Đang tạo đơn hàng..."):
                    # Chuẩn bị items
                    items_list = []
                    for _, row in items_df.iterrows():
                        items_list.append({
                            'product_id': int(row['product_id']),
                            'quantity': int(row['quantity']),
                            'current_price': int(row['current_price'])
                        })
                    
                    customer_id = st.session_state.get('current_customer_id')
                    session_id = st.session_state.get('session_id') if customer_id is None else None
                    
                    order_id = create_order(
                        customer_id=customer_id,
                        session_id=session_id,
                        total_amount=total_amount,
                        payment_method='COD',
                        payment_status='Pending',
                        items=items_list
                    )
                    
                    if order_id:
                        # Chỉ xóa các sản phẩm được chọn thanh toán khỏi giỏ hàng
                        for _, row in items_df.iterrows():
                            remove_from_cart(int(row['cart_item_id']))
                        # Dọn dẹp trạng thái chọn trong session state
                        selected_cart_items = st.session_state.get("selected_cart_items", {})
                        for _, row in items_df.iterrows():
                            pid = int(row['product_id'])
                            if pid in selected_cart_items:
                                del selected_cart_items[pid]
                        # Ghi nhận tương tác PURCHASE và tự động học gợi ý
                        record_purchase_and_retrain(customer_id, items_df)
                        st.session_state.checkout_success_order_id = order_id
                        st.session_state.checkout_success_amount = total_amount
                        st.session_state.checkout_success_method = 'COD'
                        st.rerun()
                    else:
                        st.error("❌ Không thể tạo đơn hàng. Vui lòng thử lại!")
                        
        # Xử lý Chuyển khoản (SePay / VietQR)
        else:
            # 1. Sinh và lưu trữ order_id tạm thời trong session_state
            if 'checkout_order_id' not in st.session_state:
                st.session_state.checkout_order_id = generate_order_id()
                
            order_id = st.session_state.checkout_order_id
            
            # 2. Tạo đơn hàng 'Pending' trong DB nếu chưa tạo
            if not st.session_state.get('checkout_order_created', False):
                items_list = []
                for _, row in items_df.iterrows():
                    items_list.append({
                        'product_id': int(row['product_id']),
                        'quantity': int(row['quantity']),
                        'current_price': int(row['current_price'])
                    })
                
                customer_id = st.session_state.get('current_customer_id')
                session_id = st.session_state.get('session_id') if customer_id is None else None
                
                success_id = create_order(
                    customer_id=customer_id,
                    session_id=session_id,
                    total_amount=total_amount,
                    payment_method='BANK_TRANSFER',
                    payment_status='Pending',
                    items=items_list,
                    order_id=order_id
                )
                if success_id:
                    st.session_state.checkout_order_created = True
                    
            # 3. Lấy thông tin ngân hàng nhận
            bank_id = st.secrets.get("BANK_ID", "MB")
            account_no = st.secrets.get("ACCOUNT_NO", "123456789")
            account_name = st.secrets.get("ACCOUNT_NAME", "DAO MINH TOI")
            
            # 4. Sinh URL QR Code
            qr_url = generate_vietqr(bank_id, account_no, total_amount, order_id)
            
            st.markdown(f"""
            <div style="background-color: #e8f4fd; padding: 16px; border-radius: 8px; border: 1px solid #b8daff; margin-bottom: 16px;">
                <p style="margin: 0; font-size: 14px; color: #004085;">
                    Vui lòng quét mã VietQR bên dưới hoặc chuyển khoản chính xác theo thông tin bên dưới để hệ thống duyệt đơn hàng tự động.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.image(qr_url, caption=f"Quét mã QR để chuyển khoản cho mã đơn: {order_id}", use_container_width=True)
            
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e2e3e5; margin-bottom: 16px; font-size: 14px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Ngân hàng:</td>
                        <td style="padding: 4px 0; font-weight: bold; text-align: right;">{bank_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Số tài khoản:</td>
                        <td style="padding: 4px 0; font-weight: bold; text-align: right; color: #0056b3;">{account_no}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Chủ tài khoản:</td>
                        <td style="padding: 4px 0; font-weight: bold; text-align: right;">{account_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Số tiền:</td>
                        <td style="padding: 4px 0; font-weight: bold; text-align: right; color: #e74c3c;">{total_amount:,}đ</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Nội dung CK:</td>
                        <td style="padding: 4px 0; font-weight: bold; text-align: right; color: #28a745; font-size: 16px;">{order_id}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            # Tự động quét và kiểm tra giao dịch mỗi 6 giây qua Streamlit Fragment
            @st.fragment(run_every=6)
            def auto_check_payment():
                is_paid = verify_sepay_transaction(order_id, total_amount)
                if is_paid:
                    update_order_payment_status(order_id, 'Paid')
                    # Chỉ xóa các sản phẩm được chọn thanh toán khỏi giỏ hàng
                    for _, row in items_df.iterrows():
                        remove_from_cart(int(row['cart_item_id']))
                    # Dọn dẹp trạng thái chọn trong session state
                    selected_cart_items = st.session_state.get("selected_cart_items", {})
                    for _, row in items_df.iterrows():
                        pid = int(row['product_id'])
                        if pid in selected_cart_items:
                            del selected_cart_items[pid]
                    # Ghi nhận tương tác PURCHASE và tự động học gợi ý
                    cust_id = st.session_state.get('current_customer_id')
                    record_purchase_and_retrain(cust_id, items_df)
                    st.session_state.checkout_success_order_id = order_id
                    st.session_state.checkout_success_amount = total_amount
                    st.session_state.checkout_success_method = 'BANK_TRANSFER'
                    st.rerun()
                else:
                    st.markdown("""
                    <div style="display: flex; align-items: center; justify-content: center; gap: 8px; color: #004085; font-size: 14px; margin-top: 10px; margin-bottom: 15px; padding: 10px; background-color: #e8f4fd; border-radius: 6px; border: 1px solid #b8daff;">
                        <div style="width: 16px; height: 16px; border: 2px solid #004085; border-right-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                        <span>⏳ Hệ thống đang tự động kiểm tra giao dịch qua SePay API... (mỗi 6s)</span>
                    </div>
                    <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                    </style>
                    """, unsafe_allow_html=True)

            auto_check_payment()
            
            if st.button("💳 Tôi đã chuyển khoản", type="primary", use_container_width=True):
                with st.spinner("⏳ Đang kiểm tra giao dịch qua SePay API..."):
                    is_paid = verify_sepay_transaction(order_id, total_amount)
                    if is_paid:
                        update_order_payment_status(order_id, 'Paid')
                        # Chỉ xóa các sản phẩm được chọn thanh toán khỏi giỏ hàng
                        for _, row in items_df.iterrows():
                            remove_from_cart(int(row['cart_item_id']))
                        # Dọn dẹp trạng thái chọn trong session state
                        selected_cart_items = st.session_state.get("selected_cart_items", {})
                        for _, row in items_df.iterrows():
                            pid = int(row['product_id'])
                            if pid in selected_cart_items:
                                del selected_cart_items[pid]
                        # Ghi nhận tương tác PURCHASE và tự động học gợi ý
                        cust_id = st.session_state.get('current_customer_id')
                        record_purchase_and_retrain(cust_id, items_df)
                        st.session_state.checkout_success_order_id = order_id
                        st.session_state.checkout_success_amount = total_amount
                        st.session_state.checkout_success_method = 'BANK_TRANSFER'
                        st.rerun()
                    else:
                        st.error("❌ Chưa tìm thấy giao dịch! Vui lòng đợi từ 1-2 phút rồi nhấn lại. Đảm bảo bạn chuyển đúng số tiền và nội dung chuyển khoản.")


def render_purchase_history_page(customer_id: Optional[int], session_id: Optional[str], book_data: pd.DataFrame):
    """
    Render trang lịch sử mua hàng (Purchase History) cho người dùng.
    """
    st.title("📜 Lịch sử mua hàng")
    
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("⬅️ Quay lại mua sắm", use_container_width=True):
            st.session_state.view = "shopping"
            st.rerun()
            
    st.markdown("Xem lại danh sách các đơn hàng đã đặt và trạng thái thanh toán.")
    st.divider()
    
    # Lấy lịch sử đơn hàng
    orders = get_customer_orders(customer_id=customer_id, session_id=session_id)
    
    # Lọc chỉ hiển thị đơn hàng đã thanh toán (Paid) hoặc đơn hàng COD (chờ giao hàng)
    visible_orders = []
    if orders:
        visible_orders = [o for o in orders if o.get('payment_status') == 'Paid' or o.get('payment_method') == 'COD']
    
    if not visible_orders:
        st.info("📭 Bạn chưa có đơn hàng nào trong lịch sử.")
        if st.button("🛍️ Mua sắm ngay", type="primary"):
            st.session_state.view = "shopping"
            st.rerun()
        return
        
    for order in visible_orders:
        order_id = order['order_id']
        total_amount = order['total_amount']
        method = order['payment_method']
        status = order['payment_status']
        created_at = order['created_at']
        items = order['items']
        
        # Tạo badge trạng thái thanh toán
        if status == 'Paid':
            status_badge = '<span style="background-color: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">Đã thanh toán (Paid)</span>'
        elif status == 'Pending':
            if method == 'COD':
                status_badge = '<span style="background-color: #ffeeba; color: #856404; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">Chờ giao hàng (COD)</span>'
            else:
                status_badge = '<span style="background-color: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">Chờ thanh toán (Pending)</span>'
        else:
            status_badge = f'<span style="background-color: #dee2e6; color: #495057; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">{status}</span>'
            
        method_text = "Thanh toán khi nhận hàng (COD)" if method == 'COD' else "Chuyển khoản VietQR (SePay)"
        
        # Định dạng tiêu đề cho Expander
        expander_title = f"📦 Đơn hàng {order_id} — {total_amount:,}đ ({'Thành công' if status == 'Paid' or method == 'COD' else 'Chờ xử lý'})"
        
        with st.expander(expander_title):
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #e9ecef; font-size: 14px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Mã đơn hàng:</td>
                        <td style="padding: 4px 0; font-weight: bold; text-align: right; color: #007bff;">{order_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Ngày đặt hàng:</td>
                        <td style="padding: 4px 0; text-align: right; font-weight: bold;">{created_at}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Hình thức thanh toán:</td>
                        <td style="padding: 4px 0; text-align: right; font-weight: bold;">{method_text}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #666;">Trạng thái thanh toán:</td>
                        <td style="padding: 4px 0; text-align: right;">{status_badge}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("**Chi tiết sản phẩm:**")
            
            for item in items:
                col_cover, col_desc, col_rate = st.columns([1.2, 4.3, 2.5])
                with col_cover:
                    if item.get('cover_link') and pd.notna(item['cover_link']) and item['cover_link'] != '':
                        st.image(item['cover_link'], use_container_width=True)
                    else:
                        st.image("https://picsum.photos/100/150?random=1", use_container_width=True)
                with col_desc:
                    st.markdown(f"##### {item['title']}")
                    st.write(f"📂 Thể loại: {item['category']}")
                    st.write(f"💵 Đơn giá: {item['price']:,}đ x {item['quantity']}")
                    st.write(f"💰 Thành tiền: {item['price'] * item['quantity']:,}đ")
                
                with col_rate:
                    if customer_id is not None:
                        # Chỉ cho phép đánh giá nếu đơn hàng đã được thanh toán (Paid) hoặc là đơn COD
                        if status == 'Paid' or method == 'COD':
                            pid = int(item['product_id'])
                            # Lấy đánh giá hiện tại nếu có trong DB
                            current_val = 5.0
                            try:
                                from db_utils import get_db_connection
                                with get_db_connection() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "SELECT rating FROM User_Interactions WHERE customer_id = ? AND product_id = ? AND interaction_type = 'REVIEW'", 
                                        (customer_id, pid)
                                    )
                                    row = cursor.fetchone()
                                    if row:
                                        current_val = float(row['rating'])
                            except Exception:
                                pass
                            
                            rating_options = [1, 2, 3, 4, 5]
                            default_idx = rating_options.index(int(current_val)) if int(current_val) in rating_options else 4
                            
                            selected_stars = st.selectbox(
                                "⭐ Đánh giá của bạn:",
                                options=rating_options,
                                index=default_idx,
                                format_func=lambda x: "⭐" * x,
                                key=f"rate_{order_id}_{pid}"
                            )
                            
                            if st.button("Gửi đánh giá", key=f"btn_rate_{order_id}_{pid}", use_container_width=True):
                                from db_utils import add_user_interaction
                                with st.spinner("⏳ Đang gửi đánh giá và cập nhật gợi ý..."):
                                    # Lưu vào database
                                    add_user_interaction(customer_id, pid, 'REVIEW', float(selected_stars))
                                    # Retrain mô hình
                                    try:
                                        recommender_instance = st.session_state.get('recommender')
                                        if recommender_instance is not None:
                                            recommender_instance.update_and_retrain()
                                        st.session_state.warm_recommendations = None
                                        st.toast(f"⭐ Đã ghi nhận đánh giá {selected_stars} sao!", icon="🎉")
                                        import time
                                        time.sleep(0.8)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Lỗi khi tự học: {e}")
                        else:
                            st.caption("⏳ Chờ thanh toán để đánh giá")
                    else:
                        st.caption("🔒 Đăng nhập để đánh giá")
                st.divider()
