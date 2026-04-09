import streamlit as st
from database import execute_query, execute_update
import pandas as pd
import oracledb
import uuid

DEFAULT_BALANCE = 100000000
ECONOMY_SPECIAL_SURCHARGE = 200000
FIRST_CLASS_SURCHARGE = 500000


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


def _refund_rate(days_to_depart: float) -> float:
    if days_to_depart <= 2:
        return 0.60
    if days_to_depart <= 7:
        return 0.70
    return 0.88


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


def render(connection):
    """Tra cuu ve da dat theo thong tin hanh khach"""
    st.markdown("<div class='page-title'>Vé đã đặt</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Nhập thông tin để xem lại vé đã đặt</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    if "ticket_query" not in st.session_state:
        st.session_state.ticket_query = None
    if "cancel_preview" not in st.session_state:
        st.session_state.cancel_preview = {}
    if "cancel_popup" not in st.session_state:
        st.session_state.cancel_popup = None
    if "ticket_view" not in st.session_state:
        st.session_state.ticket_view = None
    if "ticket_codes" not in st.session_state:
        st.session_state.ticket_codes = {}

    if st.session_state.get("cancel_popup"):
        popup = st.session_state.cancel_popup

        @st.dialog("Thông báo hoàn tiền")
        def _show_cancel_popup():
            st.success("Hủy vé thành công")
            if popup.get("hang_ghe"):
                st.write(f"Hạng ghế: {popup['hang_ghe']}")
            if popup.get("giave") is not None:
                st.write(f"Giá vé: {popup['giave']:,.0f}đ")
            st.write(f"Hoàn tiền: {popup['refund']:,.0f}đ")
            st.write(f"Phí hủy: {popup['fee']:,.0f}đ")
            st.write(f"Đặt trước: {popup['days']:.1f} ngày")
            st.write(f"Số dư mới: {popup['balance']:,.0f}đ")
            if st.button("Đóng"):
                st.session_state.cancel_popup = None
                st.rerun()

        _show_cancel_popup()

    if st.session_state.get("ticket_view"):
        ticket = st.session_state.ticket_view

        @st.dialog("Vé điện tử")
        def _show_ticket_view():
            st.markdown(
                """
                <style>
                .barcode {
                    height: 48px;
                    background: repeating-linear-gradient(
                        90deg,
                        #0f172a 0 2px,
                        #ffffff 2px 4px
                    );
                    border-radius: 6px;
                    border: 1px solid #e2e8f0;
                    margin: 8px 0 6px;
                }
                .barcode-code {
                    font-family: monospace;
                    font-size: 12px;
                    letter-spacing: 2px;
                    color: #475569;
                    text-align: center;
                    margin-bottom: 10px;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("**VÉ ĐIỆN TỬ VÀ XÁC NHẬN HÀNH TRÌNH**")
            st.write(f"Mã đặt chỗ (số vé): {ticket['code']}")
            st.markdown("<div class='barcode'></div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='barcode-code'>{ticket['code']}</div>",
                unsafe_allow_html=True,
            )
            st.write(f"Hành khách: {ticket['hoten']}")
            st.write(f"CCCD: {ticket['socccd']}")
            st.write(f"Email: {ticket['email']}")
            st.write(f"Số ghế: {ticket['soghe']}")
            st.write(f"Hạng ghế: {ticket['hang_ghe']}")
            st.write(f"Giá vé: {ticket['gia_ve']:,.0f}đ")
            st.write(f"Chuyến bay: {ticket['macb']}")
            st.write(f"Tuyến bay: {ticket['diem_di']} → {ticket['diem_den']}")
            st.write(f"Giờ khởi hành: {ticket['ngaygio']}")
            st.write(f"Trạng thái: {ticket['trang_thai']}")
            if st.button("Đóng"):
                st.session_state.ticket_view = None
                st.rerun()

        _show_ticket_view()

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Tra cứu vé</div>", unsafe_allow_html=True)
    with st.form("tra_cuu_ve_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            hoten = st.text_input("Họ tên", key="ticket_hoten")
        with col2:
            email = st.text_input("Email", key="ticket_email")
        with col3:
            socccd = st.text_input("Số CCCD", key="ticket_socccd")
        submitted = st.form_submit_button("Tra cứu", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not hoten or not email or not socccd:
            st.error("Vui lòng nhập đầy đủ Họ tên, Email và CCCD")
            return
        st.session_state.ticket_query = {
            "hoten": hoten,
            "email": email,
            "socccd": socccd,
        }

    if st.session_state.ticket_query:
        query = st.session_state.ticket_query
        balance = _get_account_balance(connection, query["socccd"], DEFAULT_BALANCE)
        if balance is not None:
            st.metric("Số dư tài khoản", f"{balance:,.0f}đ")
        success, data = execute_query(
            connection,
            """SELECT DV.MAVE, HK.HOTEN, HK.EMAIL, HK.SOCCCD,
                      CB.MACB, CB.DIEMDI, CB.DIEMDEN, CB.NGAYGIOKHOIHANH,
                      CB.GIAVECOBAN,
                      DV.SOGHE, DV.TRANGTHAI,
                      TO_CHAR(DV.NGAYDAT, 'DD/MM/YYYY HH24:MI') AS NGAYDAT
               FROM DAT_VE DV
               JOIN HANH_KHACH HK ON DV.MAHK = HK.MAHK
               JOIN CHUYEN_BAY CB ON DV.MACB = CB.MACB
               WHERE HK.HOTEN = :hoten AND HK.EMAIL = :email AND HK.SOCCCD = :socccd
               ORDER BY DV.NGAYDAT DESC""",
            (query["hoten"], query["email"], query["socccd"])
        )

        if success and data:
            flight_options = ["Tất cả"] + sorted(
                {str(row.get("MACB")) for row in data if row.get("MACB")}
            )
            selected_flight = st.selectbox(
                "Lọc theo chuyến bay",
                options=flight_options,
            )

            filtered_data = data
            if selected_flight != "Tất cả":
                filtered_data = [
                    row for row in data if str(row.get("MACB")) == selected_flight
                ]

            df = pd.DataFrame(filtered_data)
            seat_classes = []
            seat_prices = []
            for row in filtered_data:
                base_price = row.get("GIAVECOBAN") or 0
                class_name, seat_price, _ = _seat_class_and_price(
                    row.get("SOGHE", ""),
                    int(base_price),
                )
                seat_classes.append(class_name)
                seat_prices.append(seat_price)

            df.columns = [
                "Mã vé",
                "Hành khách",
                "Email",
                "CCCD",
                "Mã chuyến bay",
                "Điểm đi",
                "Điểm đến",
                "Ngày giờ khởi hành",
                "Giá cơ bản",
                "Số ghế",
                "Trạng thái",
                "Ngày đặt",
            ]
            df["Hạng ghế"] = seat_classes
            df["Giá vé"] = seat_prices
            st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Danh sách vé</div>", unsafe_allow_html=True)
            st.success(f"Tìm thấy {len(df)} vé")
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Hủy vé</div>", unsafe_allow_html=True)
            st.caption("Chỉ áp dụng cho vé chưa bị hủy")

            for row in filtered_data:
                mave = row.get("MAVE")
                trang_thai = row.get("TRANGTHAI", "")
                if not mave or str(trang_thai).lower() == "da huy":
                    continue

                cols = st.columns([5, 2, 1.2, 1.2])
                class_name, seat_price, _ = _seat_class_and_price(
                    row.get("SOGHE", ""),
                    int(row.get("GIAVECOBAN") or 0),
                )
                cols[0].write(
                    "Vé {mave} | {route} | Ghế {seat} ({seat_class}) | {price:,.0f}đ".format(
                        mave=mave,
                        route=f"{row.get('DIEMDI')} → {row.get('DIEMDEN')}",
                        seat=row.get("SOGHE"),
                        seat_class=class_name,
                        price=seat_price,
                    )
                )
                cols[1].write(str(trang_thai))
                if cols[2].button("Xem", key=f"view_{mave}"):
                    mave_id = int(mave)
                    if mave_id not in st.session_state.ticket_codes:
                        st.session_state.ticket_codes[mave_id] = uuid.uuid4().hex[:8].upper()
                    st.session_state.ticket_view = {
                        "code": st.session_state.ticket_codes[mave_id],
                        "hoten": row.get("HOTEN"),
                        "socccd": row.get("SOCCCD"),
                        "email": row.get("EMAIL"),
                        "soghe": row.get("SOGHE"),
                        "hang_ghe": class_name,
                        "gia_ve": seat_price,
                        "macb": row.get("MACB"),
                        "diem_di": row.get("DIEMDI"),
                        "diem_den": row.get("DIEMDEN"),
                        "ngaygio": row.get("NGAYGIOKHOIHANH"),
                        "trang_thai": row.get("TRANGTHAI"),
                    }
                    st.rerun()
                if cols[3].button("Hủy vé", key=f"cancel_{mave}"):
                    try:
                        mave_id = int(mave)
                        success_time, time_rows = execute_query(
                            connection,
                            """SELECT c.NGAYGIOKHOIHANH AS NGAY_BAY,
                                      SYSTIMESTAMP AS DB_NOW,
                                      c.GIAVECOBAN AS GIAVE,
                                      v.SOGHE AS SOGHE
                               FROM DAT_VE v
                               JOIN CHUYEN_BAY c ON v.MACB = c.MACB
                               WHERE v.MAVE = :mave""",
                            (mave_id,)
                        )
                        if success_time and time_rows:
                            ngay_bay = time_rows[0].get("NGAY_BAY")
                            db_now = time_rows[0].get("DB_NOW")
                            giave = time_rows[0].get("GIAVE")
                            soghe = time_rows[0].get("SOGHE")
                            class_name, seat_price, _ = _seat_class_and_price(
                                soghe,
                                int(giave or 0),
                            )
                            if ngay_bay and db_now:
                                khoang_cach = ngay_bay - db_now
                                if khoang_cach.total_seconds() <= 24 * 60 * 60:
                                    st.warning("Sát giờ bay, không thể hủy vé!")
                                    st.caption(f"Giờ DB: {db_now} | Giờ bay: {ngay_bay}")
                                    return
                            if ngay_bay and db_now and giave:
                                days_to_depart = (ngay_bay - db_now).total_seconds() / 86400
                                refund_amount = int(seat_price * _refund_rate(days_to_depart))
                                fee_amount = int(seat_price - refund_amount)
                                st.session_state.cancel_preview[mave_id] = {
                                    "refund": refund_amount,
                                    "fee": fee_amount,
                                    "days": days_to_depart,
                                    "giave": seat_price,
                                    "hang_ghe": class_name,
                                }
                    except oracledb.DatabaseError as db_error:
                        st.error(f"Lỗi Database: {str(db_error)}")
                    except Exception as e:
                        st.error(f"Lỗi: {str(e)}")

                preview = st.session_state.cancel_preview.get(int(mave))
                if preview:
                    st.warning(
                        "Xác nhận hủy vé? Hạng: {hang} | Giá vé: {gia:,.0f}đ | Hoàn: {refund:,.0f}đ | Phí: {fee:,.0f}đ | Đặt trước {days:.1f} ngày".format(
                            hang=preview.get("hang_ghe", ""),
                            gia=preview["giave"],
                            refund=preview["refund"],
                            fee=preview["fee"],
                            days=preview["days"],
                        )
                    )
                    yes_col, no_col = st.columns(2)
                    if yes_col.button("Có", key=f"confirm_cancel_{mave}"):
                        try:
                            mave_id = int(mave)
                            cursor = connection.cursor()
                            ket_qua_var = cursor.var(str)
                            cursor.callproc(
                                "PKG_QUAN_LY_DAT_VE.SP_HUY_VE_TRA_TIEN",
                                [mave_id, ket_qua_var]
                            )
                            ket_qua = ket_qua_var.getvalue()
                            if ket_qua and str(ket_qua).upper().startswith("LOI"):
                                st.error(str(ket_qua))
                            else:
                                balance = _get_account_balance(connection, query["socccd"], DEFAULT_BALANCE)
                                if balance is not None:
                                    new_balance = balance + preview["refund"]
                                    if _update_account_balance(connection, query["socccd"], new_balance):
                                        st.session_state.cancel_popup = {
                                            "refund": preview["refund"],
                                            "fee": preview["fee"],
                                            "days": preview["days"],
                                            "hang_ghe": preview.get("hang_ghe", ""),
                                            "giave": preview.get("giave", 0),
                                            "balance": new_balance,
                                        }
                                st.success(str(ket_qua) if ket_qua else "Hủy vé thành công")
                                st.session_state.cancel_preview.pop(mave_id, None)
                                st.rerun()
                        except oracledb.DatabaseError as db_error:
                            st.error(f"Lỗi Database: {str(db_error)}")
                        except Exception as e:
                            st.error(f"Lỗi: {str(e)}")
                    if no_col.button("Không", key=f"cancel_no_{mave}"):
                        st.session_state.cancel_preview.pop(int(mave), None)
            st.markdown("</div>", unsafe_allow_html=True)
        elif success:
            st.warning("Không tìm thấy vé nào")
        else:
            st.error(f"Lỗi khi tra cứu: {data}")
