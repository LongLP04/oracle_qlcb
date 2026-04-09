import streamlit as st
from database import execute_query


def render(connection):
    """Danh sach chuyen bay va so do ghe (chi doc)"""
    st.markdown("<div class='page-title'>Danh sách chuyến bay</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Xem toàn bộ chuyến bay và tình trạng ghế</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .seat-map-admin div[data-testid="stButton"] > button {
            width: 34px !important;
            height: 34px !important;
            padding: 0 !important;
            border-radius: 6px !important;
            border: 1px solid #d4d7e3 !important;
            font-weight: 600 !important;
            font-family: "Segoe UI", "Tahoma", sans-serif !important;
            font-size: 16px !important;
            line-height: 1 !important;
        }
        .legend {display:flex; gap:16px; align-items:center; flex-wrap:wrap; color:#475569;}
        .legend-item {display:flex; gap:6px; align-items:center;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "admin_seat_info" not in st.session_state:
        st.session_state.admin_seat_info = None

    if st.session_state.get("admin_seat_info"):
        info = st.session_state.admin_seat_info

        @st.dialog("Thông tin khách đặt ghế")
        def _show_seat_info():
            st.write(f"Họ tên: {info['hoten']}")
            st.write(f"CCCD: {info['socccd']}")
            st.write(f"Email: {info['email']}")
            st.write(f"Số điện thoại: {info['sodt']}")
            st.write(f"Mã vé: {info['mave']}")
            st.write(f"Trạng thái: {info['trangthai']}")
            st.write(f"Ngày đặt: {info['ngaydat']}")
            if st.button("Đóng"):
                st.session_state.admin_seat_info = None
                st.rerun()

        _show_seat_info()

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Lọc chuyến bay</div>", unsafe_allow_html=True)
    status = st.radio(
        "Trạng thái chuyến bay",
        ["Tất cả", "Chưa bay", "Đã bay"],
        horizontal=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    base_query = (
        "SELECT MACB, DIEMDI, DIEMDEN, NGAYGIOKHOIHANH, GIAVECOBAN "
        "FROM CHUYEN_BAY"
    )
    if status == "Chưa bay":
        base_query += " WHERE NGAYGIOKHOIHANH >= SYSDATE"
    elif status == "Đã bay":
        base_query += " WHERE NGAYGIOKHOIHANH < SYSDATE"
    base_query += " ORDER BY NGAYGIOKHOIHANH DESC"

    success_cb, flights = execute_query(connection, base_query)
    if not success_cb:
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
    selected_flight = flight_dict[selected_text]
    st.markdown(
        f"<span class='pill'>Giá vé: {selected_flight['GIAVECOBAN']:,.0f}đ</span>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    success_seats, seat_rows = execute_query(
        connection,
        """
        SELECT DV.SOGHE, DV.MAVE, DV.TRANGTHAI,
               TO_CHAR(DV.NGAYDAT, 'DD/MM/YYYY HH24:MI') AS NGAYDAT,
               HK.HOTEN, HK.SOCCCD, HK.EMAIL, HK.SODT
        FROM DAT_VE DV
        JOIN HANH_KHACH HK ON DV.MAHK = HK.MAHK
        WHERE DV.MACB = :macb AND DV.TRANGTHAI != 'Da Huy'
        """,
        (selected_flight["MACB"],),
    )
    booked_map = {}
    if success_seats and seat_rows:
        for row in seat_rows:
            booked_map[row["SOGHE"]] = {
                "mave": row.get("MAVE"),
                "trangthai": row.get("TRANGTHAI"),
                "ngaydat": row.get("NGAYDAT"),
                "hoten": row.get("HOTEN"),
                "socccd": row.get("SOCCCD"),
                "email": row.get("EMAIL"),
                "sodt": row.get("SODT"),
            }

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>Sơ đồ ghế (chỉ đọc)</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='legend'>
            <div class='legend-item'>🟩 Trống</div>
            <div class='legend-item'>🟥 Đã đặt</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows = ["A", "B", "C", "D", "E", "F"]
    layout = [1, 2, None, 3, 4, None, 5, 6, 7, 8, 9, 10]

    st.markdown("<div class='seat-map-admin'>", unsafe_allow_html=True)

    header_cols = st.columns([0.6] + [1] * len(layout))
    header_cols[0].markdown("** **")
    for idx, seat_num in enumerate(layout, start=1):
        if seat_num is None:
            header_cols[idx].markdown(" ")
        else:
            header_cols[idx].markdown(f"**{seat_num:02d}**")

    for row_label in rows:
        row_cols = st.columns([0.6] + [1] * len(layout))
        row_cols[0].markdown(f"**{row_label}**")

        for idx, seat_num in enumerate(layout, start=1):
            if seat_num is None:
                row_cols[idx].markdown(" ")
                continue

            seat_code = f"{row_label}{seat_num:02d}"
            with row_cols[idx]:
                if seat_code in booked_map:
                    if st.button("🟥", key=f"admin_seat_{seat_code}"):
                        st.session_state.admin_seat_info = booked_map[seat_code]
                        st.rerun()
                else:
                    st.button("🟩", disabled=True, key=f"admin_seat_{seat_code}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
