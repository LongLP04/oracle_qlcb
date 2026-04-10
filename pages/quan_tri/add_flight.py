import streamlit as st
from datetime import datetime, time
from database import execute_update, execute_query


def _combine_datetime(date_value, time_value) -> datetime:
    if isinstance(time_value, time):
        return datetime.combine(date_value, time_value)
    return datetime.combine(date_value, time(0, 0))


def _build_location_options(connection) -> tuple[list[str], dict]:
    code_to_name = {
        "HAN": "Hà Nội",
        "SGN": "TP.Hồ Chí Minh",
        "DAD": "Đà Nẵng",
        "HPH": "Hải Phòng",
        "VCA": "Cần Thơ",
        "CXR": "Nha Trang",
        "PQC": "Phú Quốc",
        "DLI": "Đà Lạt",
        "HUI": "Huế",
        "VII": "Vinh",
        "CBG": "Cao Bằng",
        "BLU": "Bạc Liêu",
        "XNG": "Chu Lai",
        "THD": "Thanh Hóa",
        "VDH": "Quảng Bình",
        "VCL": "Quảng Nam",
        "VKG": "Kiên Giang",
        "BMV": "Đắk Lắk",
        "UIH": "Bình Định",
        "PXU": "Gia Lai",
        "DTH": "Đồng Tháp",
        "CAH": "Cà Mau",
        "VDO": "Quảng Ninh",
        "DIN": "Điện Biên",
        "TBB": "Yên Bái",
        "HNB": "Hòa Bình",
        "VPH": "Phú Thọ",
    }

    success, rows = execute_query(
        connection,
        """
        SELECT DISTINCT DIEMDI AS DIEM FROM CHUYEN_BAY
        UNION
        SELECT DISTINCT DIEMDEN AS DIEM FROM CHUYEN_BAY
        """,
    )

    if not success or not rows:
        return [], {}

    options_map: dict[str, str] = {}
    for row in rows:
        raw_value = str(row.get("DIEM") or "").strip()
        if not raw_value:
            continue
        lookup_key = raw_value.upper()
        if lookup_key in code_to_name:
            display = f"{lookup_key} ({code_to_name[lookup_key]})"
        else:
            display = raw_value
        options_map.setdefault(display, raw_value)

    options = list(options_map.keys())
    options.sort()
    return options, options_map


def render(connection):
    """Them chuyen bay (admin)"""
    st.markdown("<div class='page-title'>Thêm chuyến bay</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Tạo chuyến bay mới cho hệ thống</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Thông tin chuyến bay</div>", unsafe_allow_html=True)

    location_options, location_map = _build_location_options(connection)
    if not location_options:
        st.warning("Chưa có điểm đi/đến trong dữ liệu để chọn.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    success_planes, planes = execute_query(
        connection,
        """
        SELECT MAMAYBAY, LOAIMAYBAY, TONGGHE
        FROM MAY_BAY
        WHERE TINHTRANG = 'San Sang'
        ORDER BY MAMAYBAY
        """,
    )
    if not success_planes or not planes:
        st.warning("Không có máy bay sẵn sàng để chọn.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    plane_options = {}
    for plane in planes:
        code = str(plane.get("MAMAYBAY") or "").strip()
        if not code:
            continue
        model = str(plane.get("LOAIMAYBAY") or "").strip()
        seats = plane.get("TONGGHE")
        if model and seats is not None:
            label = f"{code} | {model} | {seats} ghế"
        elif model:
            label = f"{code} | {model}"
        else:
            label = code
        plane_options[label] = code

    with st.form("add_flight_form"):
        col1, col2 = st.columns(2)
        with col1:
            macb = st.text_input("Mã chuyến bay", placeholder="VN123")
            diem_di_select = st.selectbox("Điểm đi", options=location_options)
            ngay = st.date_input("Ngày khởi hành")
        with col2:
            diem_den_select = st.selectbox("Điểm đến", options=location_options)
            gio = st.time_input("Giờ khởi hành")
            giave = st.number_input("Giá vé cơ bản", min_value=0, step=10000)
            soghetrong = st.number_input("Số ghế trống", min_value=1, step=1)
            plane_select = st.selectbox("Máy bay", options=list(plane_options.keys()))

        submit = st.form_submit_button("Thêm chuyến bay", use_container_width=True)

    if submit:
        macb = (macb or "").strip()
        diem_di = (location_map.get(diem_di_select) or "").strip()
        diem_den = (location_map.get(diem_den_select) or "").strip()
        mamaybay = (plane_options.get(plane_select) or "").strip()
        if not macb or not diem_di or not diem_den:
            st.error("Vui lòng nhập đầy đủ mã chuyến bay, điểm đi, điểm đến.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
        if not mamaybay:
            st.error("Vui lòng chọn máy bay.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        thoi_gian = _combine_datetime(ngay, gio)
        if thoi_gian < datetime.now():
            st.error("Giờ khởi hành phải lớn hơn thời điểm hiện tại.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        success_conflict, conflict_rows = execute_query(
            connection,
            """
            SELECT COUNT(*) AS CNT
            FROM CHUYEN_BAY
            WHERE MAMAYBAY = :mamaybay
                            AND ABS(CAST(NGAYGIOKHOIHANH AS DATE) - CAST(:ngaygio AS DATE)) < (6/24)
            """,
            {
                "mamaybay": mamaybay,
                "ngaygio": thoi_gian,
            },
        )
        if success_conflict and conflict_rows:
            if int(conflict_rows[0].get("CNT", 0)) > 0:
                st.error("Máy bay đã có chuyến bay trùng hoặc cách < 6 giờ. Vui lòng chọn máy bay khác.")
                st.markdown("</div>", unsafe_allow_html=True)
                return

        success, message = execute_update(
            connection,
            """
            INSERT INTO CHUYEN_BAY (MACB, DIEMDI, DIEMDEN, NGAYGIOKHOIHANH, GIAVECOBAN, SOGHETRONG, MAMAYBAY)
            VALUES (:macb, :diemdi, :diemden, :ngaygio, :giave, :soghetrong, :mamaybay)
            """,
            {
                "macb": macb,
                "diemdi": diem_di,
                "diemden": diem_den,
                "ngaygio": thoi_gian,
                "giave": giave,
                "soghetrong": soghetrong,
                "mamaybay": mamaybay,
            },
        )

        if success:
            st.success("Đã thêm chuyến bay mới.")
        else:
            st.error(message)

    st.markdown("</div>", unsafe_allow_html=True)
