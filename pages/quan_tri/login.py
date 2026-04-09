import streamlit as st


ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "123456"


def render():
    """Trang dang nhap admin"""
    st.markdown("<div class='page-title'>Đăng nhập Admin</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Chỉ tài khoản Admin mới truy cập được Dashboard và Báo cáo</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    with st.form("admin_login_form"):
        email = st.text_input("Email", placeholder="admin@gmail.com")
        password = st.text_input("Mật khẩu", type="password", placeholder="123456")
        submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            st.session_state.user_role = "admin"
            st.session_state.admin_email = email
            st.session_state.menu_option = "Dashboard Quản trị"
            st.success("Đăng nhập thành công")
            st.rerun()
        else:
            st.error("Sai Email hoặc mật khẩu")
