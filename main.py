import streamlit as st
import oracledb
from datetime import datetime
from pages.hanh_khach import booking, home, my_tickets
from pages.quan_tri import dashboard, report, login, flight_list, add_flight, edit_flight
from database import get_db_connection, close_db_connection, DB_CONFIG

# ==================== CẤU HÌNH STREAMLIT ====================
st.set_page_config(
    page_title="Hệ thống quản lý hàng không",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;700&display=swap');
    :root {
        --vna-navy: #0b2d4d;
        --vna-teal: #007a8a;
        --vna-teal-dark: #00606b;
        --vna-gold: #f6b21a;
        --vna-bg: #f5f7fb;
        --vna-card: #ffffff;
        --vna-border: #e2e8f0;
        --vna-text: #0f172a;
        --vna-muted: #64748b;
    }
    html, body, [class*="css"] {font-family: 'Manrope', sans-serif;}
    .stApp {background: var(--vna-bg); color: var(--vna-text);}
    h1, h2, h3 {letter-spacing: -0.3px;}
    .page-title {font-size: 28px; font-weight: 700; margin: 2px 0 4px;}
    .page-subtitle {color: var(--vna-muted); margin-bottom: 16px;}
    .section-card {background: var(--vna-card); border:1px solid var(--vna-border); border-radius:16px; padding:16px 18px; box-shadow:0 14px 30px rgba(11,45,77,.08);}
    .section-card > div:first-child {margin-top: 0 !important;}
    .card > div:first-child {margin-top: 0 !important;}
    .section-title {font-size: 16px; font-weight: 700; margin: 2px 0 12px;}
    .soft-divider {height: 1px; background: #e8edf4; margin: 14px 0;}
    .pill {display:inline-block; padding: 4px 10px; border-radius: 999px; background:#eef6f8; color: var(--vna-teal-dark); font-size:12px; border:1px solid #cfe9ee;}
    .hero {
        background: linear-gradient(120deg, rgba(11,45,77,0.92), rgba(0,122,138,0.86)),
                    radial-gradient(circle at 10% 20%, rgba(246,178,26,0.18), transparent 40%);
        color: #fff; border-radius: 18px; padding: 24px 26px; box-shadow:0 20px 50px rgba(11,45,77,.25);
        position: relative; overflow: hidden;
    }
    .hero::after {
        content: ""; position: absolute; inset: -20% -10% auto auto; width: 260px; height: 260px;
        background: radial-gradient(circle, rgba(255,255,255,.18), rgba(255,255,255,0));
        transform: rotate(25deg);
    }
    .hero-image {
        background: linear-gradient(180deg, rgba(11,45,77,0.35), rgba(11,45,77,0.85)),
                    radial-gradient(circle at 20% 20%, rgba(246,178,26,0.18), transparent 45%),
                    radial-gradient(circle at 80% 70%, rgba(0,122,138,0.25), transparent 45%);
        border-radius: 18px; padding: 28px 26px; color: #fff; position: relative; overflow: hidden;
    }
    .hero-image::before {
        content: ""; position: absolute; inset: 0; opacity: .4;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='360' viewBox='0 0 640 360'%3E%3Cpath d='M40 260 C160 140 340 120 600 180' fill='none' stroke='%23ffffff' stroke-width='2' stroke-dasharray='6 10'/%3E%3Cpath d='M90 240 L210 205 L260 210 L140 250 Z' fill='%23ffffff' fill-opacity='0.16'/%3E%3Cpath d='M260 210 L380 200 L420 212 L300 222 Z' fill='%23ffffff' fill-opacity='0.12'/%3E%3C/svg%3E");
        background-size: cover; background-position: center;
    }
    .hero-title {font-size: 30px; font-weight: 700; margin: 4px 0 6px;}
    .hero-sub {color: #e2f3f6; margin-bottom: 12px;}
    section[data-testid="stSidebar"] {background: var(--vna-navy); color:#e2e8f0;}
    section[data-testid="stSidebar"] * {color:#e2e8f0;}
    section[data-testid="stSidebar"] .stRadio > label {color:#cbd5e1;}
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {background:#0f3559; border:1px solid #143a5c; padding:8px 12px; border-radius:10px; margin-bottom:8px;}
    .brand {
        display:flex; gap:10px; align-items:center; padding:8px 0 12px; border-bottom:1px solid #143a5c;
        margin-bottom:12px;
    }
    .brand-title {font-weight:700; color:#f6b21a; line-height:1.1;}
    .brand-sub {font-size:12px; color:#cbd5e1;}
    .stButton > button {border-radius:12px; background: var(--vna-teal); color: #fff; border:1px solid var(--vna-teal-dark);}
    .stButton > button:hover {background: var(--vna-teal-dark);}
    header, footer {visibility: hidden; height: 0;}
    .topbar {
        display:flex; align-items:center; justify-content:space-between;
        background: linear-gradient(90deg, rgba(11,45,77,.95), rgba(0,122,138,.95));
        padding: 12px 18px; border-radius: 16px; color:#fff; box-shadow:0 14px 30px rgba(11,45,77,.25);
        margin: 8px 0 16px;
    }
    .topbar-left {display:flex; align-items:center; gap:12px;}
    .topbar-search {
        background:#ffffff; border-radius:999px; padding:6px 12px; color:#0f172a;
        min-width:260px; border:1px solid #dbe3ef;
    }
    [data-testid="stForm"] {border: 0 !important; padding: 0 !important; margin-top: 0 !important;}
    [data-testid="stForm"] > div {gap: 0 !important; margin-top: 0 !important;}
    .lang-pill {background:#0b2d4d; border:1px solid #1f4f6e; color:#f6b21a; padding:6px 10px; border-radius:999px; font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True
)

# ==================== KHỞI TẠO SESSION STATE ====================
if "connection" not in st.session_state:
    st.session_state.connection = None
    st.session_state.user_logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = "guest"

# ==================== KẾT NỐI TỰ ĐỘNG VÀO BACKEND ====================
@st.cache_resource
def init_db_connection():
    """Kết nối tự động đến Oracle Database khi app khởi động"""
    try:
        connection = get_db_connection(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            sid=DB_CONFIG["sid"],
            username=DB_CONFIG["username"],
            password=DB_CONFIG["password"]
        )
        return connection
    except Exception as e:
        st.error(f"❌ Không thể kết nối Database: {str(e)}")
        return None

# Khởi tạo kết nối khi session state chưa có
if st.session_state.connection is None:
    st.session_state.connection = init_db_connection()
    if st.session_state.connection:
        st.session_state.user_logged_in = True
    else:
        st.session_state.user_logged_in = False

st.markdown(
    """
    <div class='topbar'>
        <div class='topbar-left'>
            <span style='font-weight:700;letter-spacing:.2px;'>Vietnam Airlines</span>
            <span style='opacity:.7;'>|</span>
            <span style='opacity:.9;'>Quản lý hàng không</span>
        </div>
        <div class='topbar-left'>
            <div class='topbar-search'>Tìm kiếm</div>
            <div class='lang-pill'>VI</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ==================== SIDEBAR MENU ====================
st.sidebar.markdown(
    """
    <div class='brand'>
        <svg width='34' height='34' viewBox='0 0 64 64' xmlns='http://www.w3.org/2000/svg'>
            <circle cx='32' cy='32' r='30' fill='%23007a8a'/>
            <path d='M12 36 L50 20 L44 30 L56 30 L52 36 L30 40 Z' fill='%23f6b21a'/>
            <circle cx='28' cy='24' r='4' fill='%23ffffff'/>
        </svg>
        <div>
            <div class='brand-title'>VNAir</div>
            <div class='brand-sub'>Quản lý hàng không</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
st.sidebar.title("Menu Quản lý")

menu_map_admin = {
    "Trang chủ": "Trang chủ",
    "Dashboard Quản trị": "Dashboard Quản trị",
    "Báo cáo": "Báo cáo",
    "Danh sách chuyến bay": "Danh sách chuyến bay",
    "Thêm chuyến bay": "Thêm chuyến bay",
    "Chỉnh sửa chuyến bay": "Chỉnh sửa chuyến bay",
}
menu_map_guest = {
    "Trang chủ": "Trang chủ",
    "Đặt vé": "Đặt vé",
    "Vé đã đặt": "Vé đã đặt",
    "Đăng nhập (Admin)": "Đăng nhập (Admin)",
}

menu_map = menu_map_admin if st.session_state.user_role == "admin" else menu_map_guest
menu_labels = list(menu_map.keys())
if "menu_option" not in st.session_state or st.session_state.menu_option not in menu_map:
    st.session_state.menu_option = menu_labels[0]

for label in menu_labels:
    is_selected = st.session_state.menu_option == label
    if st.sidebar.button(
        label,
        use_container_width=True,
        type="primary" if is_selected else "secondary",
    ):
        st.session_state.menu_option = label
        st.rerun()

selected_route = menu_map[st.session_state.menu_option]

# ==================== HIỂN THỊ TRẠNG THÁI KẾT NỐI ====================
# st.sidebar.markdown("---")
# st.sidebar.subheader("Trang thai Database")

# if st.session_state.user_logged_in and st.session_state.connection:
#     st.sidebar.success("Checked: Da ket noi Database")
    
#     # Hiển thị thông tin kết nối
#     with st.sidebar.expander("Thong tin ket noi"):
#         st.caption(f"**Host**: {DB_CONFIG['host']}")
#         st.caption(f"**Port**: {DB_CONFIG['port']}")
#         st.caption(f"**SID**: {DB_CONFIG['sid']}")
#         st.caption(f"**User**: {DB_CONFIG['username']}")
#         st.caption(f"**Status**: OK Active")
# else:
#     st.sidebar.error("X Chua ket noi Database")
#     st.sidebar.warning("Vui long kiem tra cai dat Oracle Backend")


# ==================== ROUTER MENU ====================
if not st.session_state.user_logged_in:
    st.error("Lỗi kết nối Database")
    st.info("""
    ### Hướng dẫn khắc phục:
    1. Kiểm tra Database Oracle đang chạy
    2. Kiểm tra thông số kết nối trong database.py:
       - Host: localhost
       - Port: 1521
       - SID: xe
       - Username: NHOM3_AIRLINE
       - Password: 123456
    3. Khởi động lại ứng dụng: streamlit run main.py
    """)
else:
    if selected_route == "Trang chủ":
        home.render(st.session_state.connection)
    elif selected_route == "Đặt vé":
        booking.render(st.session_state.connection)
    elif selected_route == "Vé đã đặt":
        my_tickets.render(st.session_state.connection)
    elif selected_route == "Dashboard Quản trị":
        if st.session_state.user_role == "admin":
            dashboard.render(st.session_state.connection)
        else:
            st.error("Bạn không có quyền truy cập Dashboard")
    elif selected_route == "Báo cáo":
        if st.session_state.user_role == "admin":
            report.render(st.session_state.connection)
        else:
            st.error("Bạn không có quyền truy cập Báo cáo")
    elif selected_route == "Danh sách chuyến bay":
        if st.session_state.user_role == "admin":
            flight_list.render(st.session_state.connection)
        else:
            st.error("Bạn không có quyền truy cập Danh sách chuyến bay")
    elif selected_route == "Thêm chuyến bay":
        if st.session_state.user_role == "admin":
            add_flight.render(st.session_state.connection)
        else:
            st.error("Bạn không có quyền truy cập Thêm chuyến bay")
    elif selected_route == "Chỉnh sửa chuyến bay":
        if st.session_state.user_role == "admin":
            edit_flight.render(st.session_state.connection)
        else:
            st.error("Bạn không có quyền truy cập Chỉnh sửa chuyến bay")
    elif selected_route == "Đăng nhập (Admin)":
        login.render()

if st.session_state.user_role == "admin":
    if st.sidebar.button("Đăng xuất", use_container_width=True):
        st.session_state.user_role = "guest"
        st.session_state.admin_email = ""
        st.rerun()

# ==================== FOOTER ====================
st.sidebar.markdown("---")
st.sidebar.caption(f"2026 Hệ thống quản lý hàng không | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
