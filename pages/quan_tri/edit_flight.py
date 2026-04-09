import streamlit as st
from datetime import datetime, time
from database import execute_query, execute_update


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


def _get_booking_count(connection, macb: str) -> int:
    success, rows = execute_query(
        connection,
        """
        SELECT COUNT(*) AS CNT
        FROM DAT_VE
        WHERE MACB = :macb AND TRANGTHAI != 'Da Huy'
        """,
        (macb,),
    )
    if success and rows:
        return int(rows[0].get("CNT", 0))
    return 0


def render(connection):
    """Chinh sua chuyen bay (admin)"""
    st.markdown("<div class='page-title'>Chỉnh sửa chuyến bay</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Cập nhật thông tin hoặc số ghế trống</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    success, flights = execute_query(
        connection,
        """
        SELECT MACB, DIEMDI, DIEMDEN, NGAYGIOKHOIHANH, GIAVECOBAN, SOGHETRONG
        FROM CHUYEN_BAY
        WHERE NGAYGIOKHOIHANH >= SYSDATE
        ORDER BY NGAYGIOKHOIHANH DESC
        """,
    )
    if not success:
        st.error(f"Lỗi khi lấy chuyến bay: {flights}")
        return
    if not flights:
        st.warning("Không có chuyến bay")
        return

    flight_dict = {
        f"{f['MACB']} | {f['DIEMDI']} -> {f['DIEMDEN']} | {f['NGAYGIOKHOIHANH']}": f
        for f in flights
    }

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Chọn chuyến bay</div>", unsafe_allow_html=True)
    selected_text = st.selectbox("Chuyến bay", options=list(flight_dict.keys()))
    selected = flight_dict[selected_text]
    st.markdown("</div>", unsafe_allow_html=True)

    booking_count = _get_booking_count(connection, selected["MACB"])
    if booking_count > 0:
        st.error("Chuyến bay đã có hành khách đặt ghế, không được chỉnh sửa.")

    location_options, location_map = _build_location_options(connection)
    if not location_options:
        st.warning("Chưa có điểm đi/đến trong dữ liệu để chọn.")
        return

    def _find_option(value: str) -> int:
        for idx, display in enumerate(location_options):
            if location_map.get(display) == value:
                return idx
        return 0

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Thông tin chuyến bay</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        macb = st.text_input("Mã chuyến bay", value=selected["MACB"], disabled=True)
        diem_di_idx = _find_option(selected["DIEMDI"])
        diem_di_select = st.selectbox(
            "Điểm đi",
            options=location_options,
            index=diem_di_idx,
            disabled=booking_count > 0,
        )
        ngay_value = selected["NGAYGIOKHOIHANH"]
        if isinstance(ngay_value, datetime):
            ngay_default = ngay_value.date()
            gio_default = ngay_value.time()
        else:
            ngay_default = datetime.now().date()
            gio_default = time(0, 0)
        ngay = st.date_input(
            "Ngày khởi hành",
            value=ngay_default,
            disabled=booking_count > 0,
        )
    with col2:
        diem_den_idx = _find_option(selected["DIEMDEN"])
        diem_den_select = st.selectbox(
            "Điểm đến",
            options=location_options,
            index=diem_den_idx,
            disabled=booking_count > 0,
        )
        gio = st.time_input(
            "Giờ khởi hành",
            value=gio_default,
            disabled=booking_count > 0,
        )
        giave = st.number_input(
            "Giá vé cơ bản",
            min_value=0,
            step=10000,
            value=int(selected.get("GIAVECOBAN") or 0),
            disabled=booking_count > 0,
        )

    soghetrong = st.number_input(
        "Số ghế trống",
        min_value=1,
        step=1,
        value=int(selected.get("SOGHETRONG") or 1),
        disabled=booking_count > 0,
    )

    col_save, col_delete = st.columns([1, 1])
    with col_save:
        if st.button("Lưu thay đổi", use_container_width=True, disabled=booking_count > 0):
            diem_di = (location_map.get(diem_di_select) or "").strip()
            diem_den = (location_map.get(diem_den_select) or "").strip()
            if not diem_di or not diem_den:
                st.error("Vui lòng chọn điểm đi và điểm đến.")
            else:
                thoi_gian = _combine_datetime(ngay, gio)
                if thoi_gian < datetime.now():
                    st.error("Giờ khởi hành phải lớn hơn thời điểm hiện tại.")
                else:
                    success, message = execute_update(
                        connection,
                        """
                        UPDATE CHUYEN_BAY
                        SET DIEMDI = :diemdi,
                            DIEMDEN = :diemden,
                            NGAYGIOKHOIHANH = :ngaygio,
                            GIAVECOBAN = :giave,
                            SOGHETRONG = :soghetrong
                        WHERE MACB = :macb
                        """,
                        {
                            "diemdi": diem_di,
                            "diemden": diem_den,
                            "ngaygio": thoi_gian,
                            "giave": giave,
                            "soghetrong": soghetrong,
                            "macb": selected["MACB"],
                        },
                    )
                    if success:
                        st.success("Đã cập nhật chuyến bay.")
                    else:
                        st.error(message)

    with col_delete:
        if st.button("Xóa chuyến bay", use_container_width=True, disabled=booking_count > 0):
            success, message = execute_update(
                connection,
                "DELETE FROM CHUYEN_BAY WHERE MACB = :macb",
                {"macb": selected["MACB"]},
            )
            if success:
                st.success("Đã xóa chuyến bay.")
                st.rerun()
            else:
                st.error(message)

    st.markdown("</div>", unsafe_allow_html=True)
