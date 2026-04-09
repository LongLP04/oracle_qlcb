import streamlit as st
from database import execute_query
import pandas as pd
import pydeck as pdk
import unicodedata
import hashlib
import oracledb


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


def _build_alias_map() -> dict:
    return {
        "sai gon": ["sgn", "tan son nhat", "ho chi minh", "tphcm", "hcm"],
        "ha noi": ["han", "noi bai", "hanoi"],
        "da lat": ["dad", "dli"],
        "phu quoc": ["pqc", "phu quoc island"],
        "hai phong": ["hph", "cat bi"],
        "cam ranh": ["cxr", "khanh hoa"],
        "chu lai": ["xng", "quang nam"],
        "can tho": ["vca", "cantho"],
        "bac lieu": ["blu"],
        "cao bang": ["cbg"],
        "da nang": ["dadn", "danang", "dng"],
        "hue": ["hue", "phu bai", "thua thien hue"],
        "nha trang": ["nha trang", "khanh hoa"],
        "vinh": ["vinh", "nghe an"],
    }


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
            options_map.setdefault(display, lookup_key)
        else:
            options_map.setdefault(raw_value, raw_value)

    options = list(options_map.keys())
    options.sort()
    return options, options_map


def _match_search(value: str, query_tokens: list[str], alias_map: dict) -> bool:
    normalized_value = _normalize_place(value)
    if not normalized_value:
        return False

    all_aliases = set()
    for key, aliases in alias_map.items():
        if normalized_value == _normalize_place(key) or normalized_value in aliases:
            all_aliases.update([_normalize_place(key)] + aliases)

    searchable = " ".join([normalized_value] + list(all_aliases))
    return all(token in searchable for token in query_tokens)


def _search_flights_by_fn(connection, diem_di: str, diem_den: str) -> list[dict]:
    cursor = connection.cursor()
    try:
        ref_cursor = cursor.callfunc(
            "FN_TIM_CHUYEN_BAY",
            oracledb.CURSOR,
            [diem_di, diem_den],
        )
        rows = ref_cursor.fetchall()
        columns = [desc[0] for desc in ref_cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception:
        return []
    finally:
        cursor.close()


def _filter_future_rows(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    df_rows = pd.DataFrame(rows)
    if "NGAYGIOKHOIHANH" not in df_rows.columns:
        return rows
    df_rows["NGAYGIOKHOIHANH"] = pd.to_datetime(
        df_rows["NGAYGIOKHOIHANH"],
        errors="coerce",
    )
    now = pd.Timestamp.now()
    df_rows = df_rows[df_rows["NGAYGIOKHOIHANH"] >= now]
    return df_rows.to_dict("records")


def render(connection):
    """Trang chu hanh khach: xem danh sach chuyen bay"""
    st.markdown(
        """
        <div class='hero-image'>
            <div class='pill'>Tháng 4 - Ưu đãi mùa xuân</div>
            <div class='hero-title'>Ưu đãi đến 15%</div>
            <div class='hero-sub'>Đặt vé sớm, khám phá hành trình mới cùng giá ưu đãi.</div>
            <div style='margin-top:10px;'>
                <span style='background:#f6b21a;color:#0b2d4d;padding:8px 14px;border-radius:999px;font-weight:700;'>Khám phá ngay</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    if st.session_state.get("last_booking_message"):
        st.success(st.session_state.last_booking_message)
        st.session_state.last_booking_message = ""

    success, data = execute_query(
        connection,
        """SELECT MACB, DIEMDI, DIEMDEN, NGAYGIOKHOIHANH, GIAVECOBAN
           FROM CHUYEN_BAY
           WHERE NGAYGIOKHOIHANH >= SYSDATE
           ORDER BY NGAYGIOKHOIHANH"""
    )

    if success and data:
        df = pd.DataFrame(data)
        df.columns = ["Mã chuyến bay", "Điểm đi", "Điểm đến", "Ngày giờ khởi hành", "Giá vé cơ bản"]

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Tìm kiếm chuyến bay</div>", unsafe_allow_html=True)
        location_options, location_map = _build_location_options(connection)
        location_options = [""] + location_options
        with st.form("tim_chuyen_bay_form"):
            col_a, col_b, col_c = st.columns([1, 1, 0.6])
            with col_a:
                diem_di = st.selectbox("Điểm đi", options=location_options)
            with col_b:
                diem_den = st.selectbox("Điểm đến", options=location_options)
            with col_c:
                submitted = st.form_submit_button("Tìm", use_container_width=True)

        fn_rows = []
        if submitted and diem_di and diem_den:
            diem_di_value = location_map.get(diem_di, diem_di).strip()
            diem_den_value = location_map.get(diem_den, diem_den).strip()
            fn_rows = _search_flights_by_fn(connection, diem_di_value, diem_den_value)
            fn_rows = _filter_future_rows(fn_rows)
            if not fn_rows:
                st.warning("Không tìm thấy chuyến bay chưa tới giờ bay theo điểm đi/đến đã chọn.")
        alias_map = _build_alias_map()
        if fn_rows:
            df_filtered = pd.DataFrame(fn_rows)
            rename_map = {
                "MACB": "Mã chuyến bay",
                "DIEMDI": "Điểm đi",
                "DIEMDEN": "Điểm đến",
                "NGAYGIOKHOIHANH": "Ngày giờ khởi hành",
                "GIAVECOBAN": "Giá vé cơ bản",
            }
            df_filtered = df_filtered.rename(columns=rename_map)
        else:
            df_filtered = df

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

        map_rows = []
        for _, row in df_filtered.iterrows():
            diem_di = str(row["Điểm đi"]).strip()
            diem_den = str(row["Điểm đến"]).strip()
            start_key = _normalize_place(diem_di)
            end_key = _normalize_place(diem_den)

            if start_key in city_coords:
                start_lat, start_lon = city_coords[start_key]
            else:
                start_lat, start_lon = _coords_from_code(diem_di)

            if end_key in city_coords:
                end_lat, end_lon = city_coords[end_key]
            else:
                end_lat, end_lon = _coords_from_code(diem_den)

            map_rows.append({
                "macb": row["Mã chuyến bay"],
                "diem_di": row["Điểm đi"],
                "diem_den": row["Điểm đến"],
                "start_lat": start_lat,
                "start_lon": start_lon,
                "end_lat": end_lat,
                "end_lon": end_lon,
            })

        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Bản đồ chuyến bay</div>", unsafe_allow_html=True)
        st.caption("Bản đồ hiển thị tuyến bay được nhận diện từ điểm đi/đến")

        if map_rows:
            df_map = pd.DataFrame(map_rows)
            view_state = pdk.ViewState(
                latitude=15.8,
                longitude=106.2,
                zoom=4.4,
                pitch=35
            )

            arc_layer = pdk.Layer(
                "ArcLayer",
                data=df_map,
                get_source_position="[start_lon, start_lat]",
                get_target_position="[end_lon, end_lat]",
                get_source_color=[255, 196, 0],
                get_target_color=[0, 200, 255],
                get_width=2.5,
                pickable=True,
                auto_highlight=True
            )

            start_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position="[start_lon, start_lat]",
                get_fill_color=[0, 170, 100],
                get_radius=12000,
                pickable=True
            )

            end_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position="[end_lon, end_lat]",
                get_fill_color=[255, 80, 80],
                get_radius=12000,
                pickable=True
            )

            tooltip = {
                "html": "<b>{macb}</b><br/>{diem_di} → {diem_den}",
                "style": {"backgroundColor": "#0f172a", "color": "#f8fafc"},
            }

            st.pydeck_chart(
                pdk.Deck(
                    layers=[arc_layer, start_layer, end_layer],
                    initial_view_state=view_state,
                    tooltip=tooltip,
                    map_style="mapbox://styles/mapbox/light-v10"
                ),
                use_container_width=True
            )
            st.caption("Màu sắc: Điểm đi (xanh), Điểm đến (đỏ), Tuyến bay (vàng/lam)")
        else:
            st.info("Chưa có dữ liệu chuyến bay để vẽ bản đồ.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Danh sách chuyến bay</div>", unsafe_allow_html=True)
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        st.info(f"Tổng cộng: **{len(df_filtered)}** chuyến bay")
        st.markdown("</div>", unsafe_allow_html=True)
    elif success:
        st.warning("Không có chuyến bay")
    else:
        st.error(f"Lỗi khi lấy dữ liệu: {data}")
