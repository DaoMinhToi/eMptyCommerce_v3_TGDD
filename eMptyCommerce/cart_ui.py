"""
Module để render Shopping Cart trên giao diện Streamlit
Cung cấp các hàm để hiển thị giỏ hàng, thêm/xóa sản phẩm, v.v.
"""

import streamlit as st
import pandas as pd
from db_utils import (
    get_cart_items, add_to_cart, remove_from_cart, 
    update_quantity, clear_cart, get_cart_summary,
    create_order, update_order_payment_status,
    generate_vietqr, verify_sepay_transaction,
    generate_order_id
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
        'Product ID', 'Tên sách', 'Thể loại', 'Số lượng', 'Thêm lúc'
    ]
    
    st.dataframe(display_df, use_container_width=True)
    
    return items_df


def render_cart_items_expandable(cart_id: int):
    """
    Render sản phẩm trong giỏ hàng dạng expandable (mở rộng).
    Cho phép quản lý từng sản phẩm.
    
    Args:
        cart_id: ID của giỏ hàng
    """
    items_df = get_cart_items(cart_id)
    
    if items_df.empty:
        st.info("📭 Giỏ hàng của bạn còn trống.")
        return
    
    st.write("### Chi tiết sản phẩm")
    
    for idx, item in items_df.iterrows():
        with st.expander(f"📖 {item['title']} (x{item['quantity']})"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**ID:** {item['product_id']}")
                st.write(f"**Thể loại:** {item['category']}")
                st.write(f"**Thêm lúc:** {item['added_at']}")
            
            with col2:
                st.write(f"**Số lượng:** {item['quantity']}")
            
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
        if st.button("💳 Thanh toán", use_container_width=True):
            st.session_state.view = "checkout"
            # Reset trạng thái order của phiên checkout mới
            if 'checkout_order_id' in st.session_state:
                del st.session_state.checkout_order_id
            if 'checkout_order_created' in st.session_state:
                del st.session_state.checkout_order_created
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
        
        # Hiển thị tóm tắt giỏ hàng
        summary = get_cart_summary(cart_id)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Số loại sản phẩm", summary['total_items'])
        with col2:
            st.metric("Tổng số lượng", summary['total_quantity'])
        with col3:
            st.metric("Trạng thái", "Sẵn sàng thanh toán ✓")
    else:
        st.info("📭 Giỏ hàng của bạn còn trống")
        st.write("Hãy thêm sách từ danh sách sản phẩm!")
    
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
        
        st.markdown("---")


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

    # 2. Lấy giỏ hàng hiện tại
    items_df = get_cart_items(cart_id)
    if items_df.empty:
        st.warning("⚠️ Giỏ hàng trống! Không thể thực hiện thanh toán.")
        if st.button("🏠 Quay về trang mua sắm"):
            st.session_state.view = "shopping"
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
                        clear_cart(cart_id)
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
                    items=items_list
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
            
            if st.button("💳 Tôi đã chuyển khoản", type="primary", use_container_width=True):
                with st.spinner("⏳ Đang kiểm tra giao dịch qua SePay API..."):
                    is_paid = verify_sepay_transaction(order_id, total_amount)
                    if is_paid:
                        update_order_payment_status(order_id, 'Paid')
                        clear_cart(cart_id)
                        st.session_state.checkout_success_order_id = order_id
                        st.session_state.checkout_success_amount = total_amount
                        st.session_state.checkout_success_method = 'BANK_TRANSFER'
                        st.rerun()
                    else:
                        st.error("❌ Chưa tìm thấy giao dịch! Vui lòng đợi từ 1-2 phút rồi nhấn lại. Đảm bảo bạn chuyển đúng số tiền và nội dung chuyển khoản.")
