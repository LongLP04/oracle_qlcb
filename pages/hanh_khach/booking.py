import streamlit as st
from database import execute_query, execute_update
import oracledb
import pandas as pd
import pydeck as pdk
import unicodedata
import hashlib
import uuid

DEFAULT_BALANCE = 100000000
ECONOMY_SPECIAL_SURCHARGE = 200000
FIRST_CLASS_SURCHARGE = 500000


def _normalize_place(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    for prefix in ("tp ", "tp.", "thanh pho "):
        if normalized.startswith(prefix):
            normalized = normalized.replace(prefix, "", 1).strip()
    return normalized


def _coords_from_code(value: str) -> tuple[float, float]:
    seed = hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()
    lat_seed = int(seed[:8], 16)
    lon_seed = int(seed[8:16], 16)
    lat = 8.5 + (lat_seed % 1500) / 100.0
    lon = 102.0 + (lon_seed % 1300) / 100.0
    return lat, lon


def _get_account_balance(connection, socccd: str, default_balance: int) -> int | None:
    if not socccd:
        return None
    success, rows = execute_query(
        connection,
        "SELECT SODU FROM HANH_KHACH WHERE SOCCCD = :socccd",
        (socccd,)
    )
    if not success:
        return None
    if rows:
        return rows[0].get("SODU", default_balance)
    return default_balance


def _update_account_balance(connection, socccd: str, new_balance: int) -> bool:
    success, _ = execute_update(
        connection,
        "UPDATE HANH_KHACH SET SODU = :sodu WHERE SOCCCD = :socccd",
        (new_balance, socccd),
    )
    return success


def _violates_vertical_gap_for_multi(selected_seats: list, seat_col: str) -> bool:
    rows = ['A', 'B', 'C', 'D', 'E', 'F']
    row_index = {row: idx for idx, row in enumerate(rows)}

    if len(selected_seats) < 2:
        return False

    occupied_rows = sorted(
        row_index[code[:1]]
        for code in selected_seats
        if code[1:] == seat_col and code[:1] in row_index
    )
    for idx in range(len(occupied_rows) - 1):
        if occupied_rows[idx + 1] - occupied_rows[idx] == 2:
            return True
    return False


def _find_invalid_columns(selected_seats: list) -> list[str]:
    columns = sorted({seat[1:] for seat in selected_seats if len(seat) >= 2})
    invalid = []
    for col in columns:
        if _violates_vertical_gap_for_multi(selected_seats, col):
            invalid.append(col)
    return invalid


def _reset_booking_state() -> None:
    st.session_state.booking_step = 1
    st.session_state.booking_data = {
        'hoten': '',
        'socccd': '',
        'email': '',
        'sodt': '',
        'macb': None,
        'flight_info': None,
        'selected_seats': [],
        'giavecoban': 0
    }
    st.session_state.confirm_booking = False


def _seat_class_and_price(seat_code: str, base_price: int) -> tuple[str, int, int]:
    try:
        seat_col = int(seat_code[1:])
    except (TypeError, ValueError):
        seat_col = 0

    if seat_col <= 2:
        surcharge = FIRST_CLASS_SURCHARGE
        class_name = "Hạng nhất"
    elif seat_col <= 4:
        surcharge = ECONOMY_SPECIAL_SURCHARGE
        class_name = "Phổ thông đặc biệt"
    else:
        surcharge = 0
        class_name = "Phổ thông"
    return class_name, base_price + surcharge, surcharge


def _build_fare_breakdown(selected_seats: list[str], base_price: int) -> list[dict]:
    summary = {}
    for seat in selected_seats:
        class_name, price, _ = _seat_class_and_price(seat, base_price)
        if class_name not in summary:
            summary[class_name] = {
                "Hạng ghế": class_name,
                "Số lượng": 0,
                "Giá/vé": price,
                "Thành tiền": 0,
            }
        summary[class_name]["Số lượng"] += 1
        summary[class_name]["Thành tiền"] += price
    return list(summary.values())



def render(connection):
    """Quy trình đặt vé máy bay"""
    
    st.markdown(
        """
        <style>
        .app-title {font-size: 28px; font-weight: 700; margin-bottom: 4px;}
        .app-subtitle {color: #64748b; margin-bottom: 16px;}
        .card {
            background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px;
            padding: 12px 16px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        .section-title {font-size: 17px; font-weight: 700; margin: 2px 0 12px;}
        .soft-divider {height: 1px; background: #eef2f7; margin: 14px 0;}
        .pill {display:inline-block; padding: 6px 12px; border-radius: 999px; background:#f1f5f9; color:#475569; font-size:13px;}
        .legend {display:flex; gap:16px; align-items:center; flex-wrap:wrap; color:#475569;}
        .legend-item {display:flex; gap:6px; align-items:center;}
        .info-summary {font-size: 15px; font-weight: 600; color: #0f172a; margin-top: 8px;}
        .info-summary span {color: #475569; font-weight: 500;}
        .info-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 12px 14px;
            margin-top: 10px;
        }
        .info-card .title {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #0f172a;
        }
        .info-card .line {
            font-size: 15px;
            margin: 2px 0;
            color: #0f172a;
        }
        .info-card .line span {color: #475569;}
        .action-btn div[data-testid="stButton"] > button {
            font-size: 16px !important;
            padding: 10px 16px !important;
            border-radius: 10px !important;
            min-width: 140px !important;
            height: 42px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if "booking_popup" not in st.session_state:
        st.session_state.booking_popup = None

    if st.session_state.get("booking_popup"):
        popup = st.session_state.booking_popup

        @st.dialog("Thông báo thanh toán")
        def _show_booking_popup():
            st.success("Thanh toán thành công")
            st.write(f"Mã xác nhận: {popup['code']}")
            st.write(f"Chuyến bay: {popup['macb']} | {popup['route']}")
            st.write(f"Ghế: {', '.join(popup['seats'])}")
            if popup.get("fare_breakdown"):
                st.write("Chi tiết hạng vé:")
                for item in popup["fare_breakdown"]:
                    st.write(
                        "- {hang}: {count} vé x {price:,.0f}đ = {total:,.0f}đ".format(
                            hang=item["Hạng ghế"],
                            count=item["Số lượng"],
                            price=item["Giá/vé"],
                            total=item["Thành tiền"],
                        )
                    )
            st.write(f"Tổng tiền: {popup['total']:,.0f}đ")
            st.write(f"Đã trừ: {popup['deducted']:,.0f}đ")
            st.write(f"Số dư còn lại: {popup['balance']:,.0f}đ")
            if st.button("Đóng"):
                st.session_state.booking_popup = None
                st.rerun()

        _show_booking_popup()


    st.markdown("<div class='app-title'>Đặt vé máy bay</div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle'>Quy trình 3 bước: thông tin hành khách, chọn ghế, xác nhận thanh toán</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    
    # ===== KHỞI TẠO SESSION STATE =====
    if 'booking_step' not in st.session_state:
        st.session_state.booking_step = 1
    if 'booking_data' not in st.session_state:
        st.session_state.booking_data = {
            'hoten': '',
            'socccd': '',
            'email': '',
            'sodt': '',
            'macb': None,
            'flight_info': None,
            'selected_seats': [],
            'giavecoban': 0
        }
    
    # ===== NHẬP THÔNG TIN HÀNH KHÁCH & CHỌN CHUYẾN BAY =====
    if st.session_state.booking_step == 1:
        st.progress(0.33)
        
        col1, col2 = st.columns([1.1, 1])
        
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Thông tin hành khách</div>", unsafe_allow_html=True)
            if "input_hoten" not in st.session_state:
                st.session_state.input_hoten = st.session_state.booking_data['hoten']
            if "input_socccd" not in st.session_state:
                st.session_state.input_socccd = st.session_state.booking_data['socccd']
            if "input_email" not in st.session_state:
                st.session_state.input_email = st.session_state.booking_data['email']
            if "input_sodt" not in st.session_state:
                st.session_state.input_sodt = st.session_state.booking_data['sodt']

            st.text_input("Họ tên", key="input_hoten", placeholder="Nguyễn Văn A")
            st.text_input("Số CCCD", key="input_socccd", placeholder="012345678901")
            st.text_input("Email", key="input_email", placeholder="email@example.com")
            st.text_input("Số điện thoại", key="input_sodt", placeholder="0912345678")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Chọn chuyến bay</div>", unsafe_allow_html=True)
            
            # Lấy danh sách chuyến bay
            success_cb, flights = execute_query(
                connection,
                """SELECT CB.MACB, CB.DIEMDI, CB.DIEMDEN, CB.NGAYGIOKHOIHANH, CB.GIAVECOBAN
                   FROM CHUYEN_BAY CB
                   WHERE CB.NGAYGIOKHOIHANH >= SYSDATE
                   ORDER BY CB.NGAYGIOKHOIHANH"""
            )
            
            if success_cb and flights:
                flight_dict = {
                    f"{f['MACB']} | {f['DIEMDI']} → {f['DIEMDEN']} | {f['NGAYGIOKHOIHANH']}": f 
                    for f in flights
                }
                selected_flight_text = st.selectbox(
                    "Chuyến bay",
                    options=list(flight_dict.keys()),
                    key="select_flight"
                )
                selected_flight = flight_dict[selected_flight_text]
                st.markdown(
                    f"<span class='pill'>Giá vé: {selected_flight['GIAVECOBAN']:,.0f}đ</span>",
                    unsafe_allow_html=True
                )

                st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
                st.markdown("<div class='section-title'>Tuyến bay đã chọn</div>", unsafe_allow_html=True)
                city_coords = {
                    "ha noi": (21.0285, 105.8542),
                    "han": (21.0285, 105.8542),
                    "haiphong": (20.8449, 106.6881),
                    "hai phong": (20.8449, 106.6881),
                    "hph": (20.8449, 106.6881),
                    "da nang": (16.0544, 108.2022),
                    "ho chi minh": (10.8231, 106.6297),
                    "sai gon": (10.8231, 106.6297),
                    "sgn": (10.8231, 106.6297),
                    "nha trang": (12.2388, 109.1967),
                    "phu quoc": (10.2899, 103.9840),
                    "pqc": (10.2899, 103.9840),
                    "hue": (16.4637, 107.5909),
                    "can tho": (10.0452, 105.7469),
                    "vca": (10.0452, 105.7469),
                    "vinh": (18.6796, 105.6813),
                    "da lat": (11.9404, 108.4583),
                    "dad": (11.9404, 108.4583),
                    "cxr": (12.2388, 109.1967),
                    "chu lai": (15.4059, 108.7049),
                    "xng": (15.4059, 108.7049),
                    "bac lieu": (9.2943, 105.7278),
                    "blu": (9.2943, 105.7278),
                    "cao bang": (22.6657, 106.2579),
                    "cbg": (22.6657, 106.2579),
                }

                start_key = _normalize_place(str(selected_flight["DIEMDI"]))
                end_key = _normalize_place(str(selected_flight["DIEMDEN"]))

                if start_key in city_coords:
                    start_lat, start_lon = city_coords[start_key]
                else:
                    start_lat, start_lon = _coords_from_code(str(selected_flight["DIEMDI"]))

                if end_key in city_coords:
                    end_lat, end_lon = city_coords[end_key]
                else:
                    end_lat, end_lon = _coords_from_code(str(selected_flight["DIEMDEN"]))

                df_route = pd.DataFrame([
                    {
                        "macb": selected_flight["MACB"],
                        "diem_di": selected_flight["DIEMDI"],
                        "diem_den": selected_flight["DIEMDEN"],
                        "start_lat": start_lat,
                        "start_lon": start_lon,
                        "end_lat": end_lat,
                        "end_lon": end_lon,
                    }
                ])

                view_state = pdk.ViewState(
                    latitude=(start_lat + end_lat) / 2,
                    longitude=(start_lon + end_lon) / 2,
                    zoom=4.8,
                    pitch=30
                )

                arc_layer = pdk.Layer(
                    "ArcLayer",
                    data=df_route,
                    get_source_position="[start_lon, start_lat]",
                    get_target_position="[end_lon, end_lat]",
                    get_source_color=[255, 196, 0],
                    get_target_color=[0, 200, 255],
                    get_width=3,
                    pickable=True,
                    auto_highlight=True
                )

                tooltip = {
                    "html": "<b>{macb}</b><br/>{diem_di} → {diem_den}",
                    "style": {"backgroundColor": "#0f172a", "color": "#f8fafc"},
                }

                st.pydeck_chart(
                    pdk.Deck(
                        layers=[arc_layer],
                        initial_view_state=view_state,
                        tooltip=tooltip,
                        map_style="mapbox://styles/mapbox/light-v10"
                    ),
                    use_container_width=True
                )
            else:
                st.error("Không có chuyến bay")
                selected_flight = None
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Xác nhận thông tin</div>", unsafe_allow_html=True)
        if st.button("Tiếp tục", use_container_width=True, type="primary"):
            hoten = (st.session_state.get("input_hoten") or "").strip()
            socccd = (st.session_state.get("input_socccd") or "").strip()
            email = (st.session_state.get("input_email") or "").strip()
            sodt = (st.session_state.get("input_sodt") or "").strip()
            if not hoten or not socccd or not email or not sodt:
                st.error("Vui lòng nhập đầy đủ thông tin!")
            elif not selected_flight:
                st.error("Vui lòng chọn chuyến bay!")
            else:
                st.session_state.booking_data = {
                    'hoten': hoten,
                    'socccd': socccd,
                    'email': email,
                    'sodt': sodt,
                    'macb': selected_flight['MACB'],
                    'flight_info': selected_flight,
                    'selected_seats': [],
                    'giavecoban': selected_flight['GIAVECOBAN']
                }
                st.session_state.booking_step = 2
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    # ===== CHỌN GHẾ =====
    elif st.session_state.booking_step == 2:
        st.progress(0.66)

        
        
        booking_data = st.session_state.booking_data
        flight = booking_data['flight_info']
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='section-title'>Chọn ghế - {flight['MACB']} ({flight['DIEMDI']} → {flight['DIEMDEN']})</div>",
            unsafe_allow_html=True
        )
        current_balance = _get_account_balance(
            connection, booking_data["socccd"], DEFAULT_BALANCE
        )
        st.markdown(
            """
            <div class='info-card'>
                <div class='title'>Thông tin hành khách</div>
                <div class='line'>Họ tên: <span>{hoten}</span></div>
                <div class='line'>Số CCCD: <span>{socccd}</span></div>
                <div class='line'>Email: <span>{email}</span></div>
                <div class='line'>Số điện thoại: <span>{sodt}</span></div>
                <div class='line'>Số dư: <span>{balance}</span></div>
            </div>
            """.format(
                hoten=booking_data["hoten"],
                socccd=booking_data["socccd"],
                email=booking_data["email"],
                sodt=booking_data["sodt"],
                balance=(
                    f"{current_balance:,.0f}d"
                    if current_balance is not None
                    else "Không thể lấy"
                ),
            ),
            unsafe_allow_html=True,
        )
        
        # Lấy danh sách ghế đã đặt
        success_seats, booked_seats_data = execute_query(
            connection,
            f"SELECT SOGHE FROM DAT_VE WHERE MACB = '{flight['MACB']}' AND TRANGTHAI != 'Da Huy'"
        )
        booked_seats = [s['SOGHE'] for s in booked_seats_data] if success_seats and booked_seats_data else []
        
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Sơ đồ ghế (6 hàng x 10 cột) - Tối đa 9 ghế</div>", unsafe_allow_html=True)

        st.markdown("<div class='seat-map'>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class='legend'>
                <div class='legend-item'>🟩 Trống</div>
                <div class='legend-item'>🟥 Đã đặt</div>
                <div class='legend-item'>🔵 Đã chọn</div>
                <div class='legend-item'>🟦 Phổ thông</div>
                <div class='legend-item'>🟪 Phổ thông đặc biệt</div>
                <div class='legend-item'>🟫 Hạng nhất</div>
                <div class='legend-item'><strong>Chọn:</strong> {count}/9</div>
            </div>
            """.format(count=len(st.session_state.booking_data['selected_seats'])),
            unsafe_allow_html=True
        )
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <style>
            .seat-map div[data-testid="stButton"] > button {
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
            </style>
            """,
            unsafe_allow_html=True
        )

        rows = ['A', 'B', 'C', 'D', 'E', 'F']
        seat_numbers = list(range(1, 11))
        layout = [1, 2, None, 3, 4, None, 5, 6, 7, 8, 9, 10]

        selected_seats = st.session_state.booking_data['selected_seats']

        # Header số ghế
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
                if seat_num <= 2:
                    cabin_label = "🟫"
                    cabin_name = "Hạng nhất"
                elif seat_num <= 4:
                    cabin_label = "🟪"
                    cabin_name = "Phổ thông đặc biệt"
                else:
                    cabin_label = "🟦"
                    cabin_name = "Phổ thông"

                with row_cols[idx]:
                    if seat_code in booked_seats:
                        st.button("🟥", disabled=True, key=f"seat_{seat_code}", help="Đã đặt")
                    elif seat_code in selected_seats:
                        if st.button("🔵", key=f"seat_{seat_code}", help="Đã chọn"):
                            selected_seats.remove(seat_code)
                            st.rerun()
                    else:
                        if st.button(cabin_label, key=f"seat_{seat_code}", help=f"{cabin_name} - {seat_code}"):
                            if len(selected_seats) >= 9:
                                st.error("Tối đa 9 ghế!")
                            else:
                                prospective = selected_seats + [seat_code]
                                if _violates_vertical_gap_for_multi(prospective, seat_code[1:]):
                                    st.error("Không để trống 1 ghế giữa (theo cột)!")
                                else:
                                    selected_seats.append(seat_code)
                                    st.rerun()
        
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        
        if selected_seats:
            st.success(f"Đã chọn: {', '.join(sorted(selected_seats))}")
        else:
            st.warning("Chưa chọn ghế nào")

        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='action-btn'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            if st.button("Quay lại", use_container_width=True, type="primary"):
                st.session_state.booking_step = 1
                st.rerun()
        
        with col2:
            if st.button("Tiếp tục", use_container_width=True, type="primary"):
                if selected_seats:
                    st.session_state.booking_step = 3
                    st.rerun()
                else:
                    st.error("Vui lòng chọn ít nhất 1 ghế!")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # ===== XÁC NHẬN THANH TOÁN =====
    elif st.session_state.booking_step == 3:
        st.progress(1.0)

        
        
        booking_data = st.session_state.booking_data
        flight = booking_data['flight_info']
        selected_seats = booking_data['selected_seats']
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Xác nhận thanh toán</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Thông tin hành khách:**")
            st.write(f"Họ tên: {booking_data['hoten']}")
            st.write(f"Số CCCD: {booking_data['socccd']}")
            st.write(f"Email: {booking_data['email']}")
            st.write(f"Số điện thoại: {booking_data['sodt']}")

        with col2:
            st.markdown("**Thông tin chuyến bay:**")
            st.write(f"Mã: {flight['MACB']}")
            st.write(f"Tuyến: {flight['DIEMDI']} → {flight['DIEMDEN']}")
            st.write(f"Ngày: {flight['NGAYGIOKHOIHANH']}")
        
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        
        # Danh sách ghế
        st.markdown("**Danh sách ghế đã chọn:**")
        
        seats_data = []
        for idx, seat in enumerate(sorted(selected_seats), 1):
            class_name, seat_price, surcharge = _seat_class_and_price(
                seat, booking_data["giavecoban"]
            )
            seats_data.append({
                'STT': idx,
                'Ghế': seat,
                'Hạng ghế': class_name,
                'Giá': f"{seat_price:,.0f}đ",
                'Phụ thu': f"{surcharge:,.0f}đ",
            })
        
        df_seats = pd.DataFrame(seats_data)
        st.dataframe(df_seats, use_container_width=True, hide_index=True)
        
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        
        # Tính tổng tiền
        tong_tien = sum(
            _seat_class_and_price(seat, booking_data["giavecoban"])[1]
            for seat in selected_seats
        )
        fare_breakdown = _build_fare_breakdown(
            selected_seats, booking_data["giavecoban"]
        )
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Số ghế", len(selected_seats))
        col2.metric("Giá gốc", f"{booking_data['giavecoban']:,.0f}đ")
        col3.metric("Tổng tiền", f"{tong_tien:,.0f}đ")

        if fare_breakdown:
            st.markdown("**Chi tiết theo hạng ghế:**")
            st.dataframe(
                pd.DataFrame(fare_breakdown),
                use_container_width=True,
                hide_index=True,
            )

        current_balance = _get_account_balance(
            connection, booking_data["socccd"], DEFAULT_BALANCE
        )
        if current_balance is not None:
            st.metric("Số dư tài khoản", f"{current_balance:,.0f}đ")
        
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        
        st.markdown("<div class='action-btn'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Quay lại", use_container_width=True, type="primary"):
                st.session_state.booking_step = 2
                st.rerun()

        with col2:
            if st.button("Xác nhận đặt vé", use_container_width=True, type="primary"):
                st.session_state.confirm_booking = True

        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get("confirm_booking"):
            st.warning(
                f"Xác nhận đặt vé {len(selected_seats)} ghế, tổng tiền {tong_tien:,.0f}đ?"
            )
            yes_col, no_col = st.columns(2)
            proceed_booking = False
            if yes_col.button("Có"):
                proceed_booking = True
                st.session_state.confirm_booking = False
            if no_col.button("Không"):
                st.session_state.confirm_booking = False

            if proceed_booking:
                # Thực thi đặt vé cho từng ghế
                success_count = 0
                error_messages = []
                
                # Tìm hoặc tạo hành khách
                try:
                    # Kiểm tra xem hành khách có tồn tại không
                    success_check, check_result = execute_query(
                        connection,
                        f"SELECT MAHK FROM HANH_KHACH WHERE SOCCCD = '{booking_data['socccd']}'"
                    )
                    
                    if success_check and check_result:
                        mahk = check_result[0]['MAHK']
                    else:
                        # Tạo hành khách mới
                        cursor = connection.cursor()
                        success_max, max_hk = execute_query(
                            connection,
                            "SELECT COALESCE(MAX(MAHK), 0) as MAX_HK FROM HANH_KHACH"
                        )
                        mahk = (max_hk[0].get('MAX_HK', 0) if max_hk else 0) + 1
                        
                        insert_sql = (
                            "INSERT INTO HANH_KHACH (MAHK, HOTEN, SOCCCD, EMAIL, SODT, SODU) "
                            "VALUES (:mahk, :hoten, :socccd, :email, :sodt, :sodu)"
                        )
                        cursor.execute(
                            insert_sql,
                            {
                                "mahk": mahk,
                                "hoten": booking_data["hoten"],
                                "socccd": booking_data["socccd"],
                                "email": booking_data["email"],
                                "sodt": booking_data["sodt"],
                                "sodu": DEFAULT_BALANCE,
                            },
                        )
                        connection.commit()
                        cursor.close()
                except Exception as e:
                    st.error(f"Lỗi khi tạo hành khách: {str(e)}")
                    mahk = None
                
                if mahk:
                    current_balance = _get_account_balance(
                        connection, booking_data["socccd"], DEFAULT_BALANCE
                    )
                    if current_balance is None:
                        st.error("Không thể lấy số dư tài khoản")
                        return
                    if current_balance < tong_tien:
                        st.error("Số dư tài khoản không đủ để thanh toán")
                        return

                    # Kiem tra ghe truoc khi dat
                    success_seats, booked_seats_data = execute_query(
                        connection,
                        f"SELECT SOGHE FROM DAT_VE WHERE MACB = '{flight['MACB']}' AND TRANGTHAI != 'Da Huy'"
                    )
                    booked_seats = (
                        [s['SOGHE'] for s in booked_seats_data]
                        if success_seats and booked_seats_data
                        else []
                    )
                    precheck_errors = []
                    for seat in sorted(selected_seats):
                        if seat in booked_seats:
                            precheck_errors.append(f"Ghế {seat}: Đã được đặt")
                    invalid_columns = _find_invalid_columns(selected_seats)
                    for col in invalid_columns:
                        precheck_errors.append(
                            f"Cột {col}: Không để trống 1 ghế giữa"
                        )
                    if precheck_errors:
                        st.error("Không thể đặt vé vì có ghế không hợp lệ:")
                        for error in precheck_errors:
                            st.write(f"  - {error}")
                        return

                    # Đặt vé cho từng ghế
                    for seat in sorted(selected_seats):
                        try:
                            cursor = connection.cursor()
                            ket_qua_var = cursor.var(str)
                            
                            # Gọi Procedure SP_DAT_VE
                            cursor.callproc(
                                'PKG_QUAN_LY_DAT_VE.SP_DAT_VE',
                                [mahk, flight['MACB'], seat, ket_qua_var]
                            )

                            ket_qua_dat = ket_qua_var.getvalue()
                            if ket_qua_dat and str(ket_qua_dat).upper().startswith("LOI"):
                                error_messages.append(f"Ghế {seat}: {ket_qua_dat}")
                                cursor.close()
                                break

                            cursor.execute(
                                """SELECT MAVE FROM DAT_VE
                                   WHERE MAHK = :mahk AND MACB = :macb AND SOGHE = :soghe
                                   ORDER BY MAVE DESC FETCH FIRST 1 ROWS ONLY""",
                                (mahk, flight['MACB'], seat)
                            )
                            row = cursor.fetchone()
                            if not row:
                                error_messages.append(f"Ghế {seat}: Không tìm thấy mã vé")
                                cursor.close()
                                break

                            ma_ve = row[0]
                            ket_qua_tt = cursor.var(str)
                            cursor.callproc(
                                'PKG_QUAN_LY_DAT_VE.SP_THANH_TOAN_VE',
                                [ma_ve, ket_qua_tt]
                            )

                            ket_qua_tt_val = ket_qua_tt.getvalue()
                            if ket_qua_tt_val and str(ket_qua_tt_val).upper().startswith("LOI"):
                                error_messages.append(f"Ghế {seat}: {ket_qua_tt_val}")
                                cursor.close()
                                break

                            success_count += 1
                            cursor.close()
                        
                        except oracledb.DatabaseError as db_error:
                            error_msg = str(db_error)
                            if "ORA-20001" in error_msg:
                                error_messages.append(f"Ghế {seat}: Vi phạm giới hạn 9 vé")
                            else:
                                error_messages.append(f"Ghế {seat}: {error_msg}")
                            connection.rollback()
                            break
                        
                        except Exception as e:
                            error_messages.append(f"Ghế {seat}: {str(e)}")
                            connection.rollback()
                            break
                    
                    # Hiển thị kết quả
                    st.markdown("---")
                    
                    if error_messages:
                        st.error("❌ Đặt vé thất bại. Không ghi nhận giao dịch.")
                        for error in error_messages:
                            st.write(f"  - {error}")
                        return
                    
                    if success_count == len(selected_seats):
                        amount_deducted = sum(
                            _seat_class_and_price(seat, booking_data["giavecoban"])[1]
                            for seat in selected_seats
                        )
                        new_balance = current_balance - amount_deducted
                        if _update_account_balance(connection, booking_data["socccd"], new_balance):
                            st.info(
                                f"Đã trừ: {amount_deducted:,.0f}đ | Số dư sau thanh toán: {new_balance:,.0f}đ"
                            )
                        st.success(f"✅ Đặt vé thành công {success_count} ghế!")
                        st.balloons()
                        st.session_state.booking_popup = {
                            "code": uuid.uuid4().hex[:8].upper(),
                            "macb": flight["MACB"],
                            "route": f"{flight['DIEMDI']} → {flight['DIEMDEN']}",
                            "seats": sorted(selected_seats),
                            "total": amount_deducted,
                            "deducted": amount_deducted,
                            "fare_breakdown": fare_breakdown,
                            "balance": new_balance,
                        }
                        st.session_state.last_booking_message = (
                            f"Đặt vé thành công {success_count} ghế. Vui lòng kiểm tra tại Trang chủ."
                        )
                        st.session_state.booking_step = 1
                        _reset_booking_state()
                        st.rerun()
                    
                    # Nút đặt vé mới
                    if st.button("Đặt vé mới"):
                        _reset_booking_state()
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
