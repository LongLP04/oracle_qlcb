import streamlit as st
from database import execute_query
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==================== DASHBOARD QUẢN LÝ CHUYẾN BAY ====================
def render(connection):
    """Dashboard quản lý chuyến bay - hiển thị thống kê chi tiết"""
    
    st.markdown("<div class='page-title'>Dashboard quản lý chuyến bay</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Biểu đồ và thống kê chi tiết</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    
    # ===== THỐNG KÊ CHÍNH (TOP METRICS) =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Tổng quan</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            success, data = execute_query(
                connection,
                "SELECT COUNT(*) as TOTAL FROM CHUYEN_BAY WHERE NGAYGIOKHOIHANH > SYSDATE"
            )
            if success and data:
                total_flights = data[0].get('TOTAL', 0)
                st.metric("Chuyến bay sắp tới", f"{total_flights}")
            else:
                st.metric("Chuyến bay sắp tới", "N/A")
        except Exception as e:
            st.metric("Chuyến bay sắp tới", "Lỗi")
    
    with col2:
        try:
            success, data = execute_query(
                connection,
                "SELECT COUNT(*) as TOTAL FROM DAT_VE WHERE TRUNC(NGAYDAT) = TRUNC(SYSDATE)"
            )
            if success and data:
                today_bookings = data[0].get('TOTAL', 0)
                st.metric("Vé đặt hôm nay", f"{today_bookings}")
            else:
                st.metric("Vé đặt hôm nay", "N/A")
        except Exception as e:
            st.metric("Vé đặt hôm nay", "Lỗi")
    
    with col3:
        try:
            success, data = execute_query(
                connection,
                "SELECT COUNT(*) as TOTAL FROM DAT_VE"
            )
            if success and data:
                total_bookings = data[0].get('TOTAL', 0)
                st.metric("Tổng vé đã đặt", f"{total_bookings}")
            else:
                st.metric("Tổng vé đã đặt", "N/A")
        except Exception as e:
            st.metric("Tổng vé đã đặt", "Lỗi")
    
    with col4:
        try:
            success, data = execute_query(
                connection,
                "SELECT COUNT(DISTINCT MaHK) as TOTAL FROM DAT_VE"
            )
            if success and data:
                unique_passengers = data[0].get('TOTAL', 0)
                st.metric("Hành khách đã đặt vé", f"{unique_passengers}")
            else:
                st.metric("Hành khách đã đặt vé", "N/A")
        except Exception as e:
            st.metric("Hành khách đã đặt vé", "Lỗi")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    # ===== DOANH THU & TY LE LAP DAY (GOI FUNCTION DB) =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Doanh thu và tỷ lệ lấp đầy</div>", unsafe_allow_html=True)

    success_flights, flights = execute_query(
        connection,
        "SELECT MACB FROM CHUYEN_BAY ORDER BY NGAYGIOKHOIHANH DESC",
    )
    if success_flights and flights:
        flight_ids = [row.get("MACB") for row in flights if row.get("MACB")]
        selected_macb = st.selectbox("Chọn chuyến bay", options=flight_ids)

        success_rev, rev_rows = execute_query(
            connection,
            "SELECT PKG_FLIGHT_MANAGEMENT.FN_DOANH_THU_CHUYEN_BAY(:macb) AS DOANH_THU FROM dual",
            (selected_macb,),
        )
        success_fill, fill_rows = execute_query(
            connection,
            "SELECT FN_TY_LE_LAP_DAY(:macb) AS TY_LE FROM dual",
            (selected_macb,),
        )

        col_rev, col_fill = st.columns(2)
        doanh_thu = rev_rows[0].get("DOANH_THU") if success_rev and rev_rows else None
        ty_le = fill_rows[0].get("TY_LE") if success_fill and fill_rows else None
        col_rev.metric("Doanh thu chuyến bay", f"{doanh_thu:,.0f}đ" if doanh_thu is not None else "N/A")
        col_fill.metric("Tỷ lệ lấp đầy", f"{ty_le:.2f}%" if ty_le is not None else "N/A")
    else:
        st.info("Chưa có dữ liệu chuyến bay để tính doanh thu và tỷ lệ lấp đầy.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    # ===== BẢNG VÉ HỦY GẦN ĐÂY =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Vé đã hủy gần đây</div>", unsafe_allow_html=True)

    try:
        success, data = execute_query(
            connection,
            """SELECT DV.MAVE, HK.HOTEN, CB.MACB,
                      CB.DIEMDI, CB.DIEMDEN, DV.SOGHE,
                      TO_CHAR(DV.NGAYHUY, 'DD/MM/YYYY HH24:MI') as NGAY_HUY
               FROM DAT_VE DV
               JOIN HANH_KHACH HK ON DV.MAHK = HK.MAHK
               JOIN CHUYEN_BAY CB ON DV.MACB = CB.MACB
               WHERE DV.TRANGTHAI = 'Da Huy'
               ORDER BY DV.NGAYHUY DESC
               FETCH FIRST 20 ROWS ONLY"""
        )
        if not success:
            success, data = execute_query(
                connection,
                """SELECT DV.MAVE, HK.HOTEN, CB.MACB,
                          CB.DIEMDI, CB.DIEMDEN, DV.SOGHE,
                          TO_CHAR(DV.NGAYDAT, 'DD/MM/YYYY HH24:MI') as NGAY_HUY
                   FROM DAT_VE DV
                   JOIN HANH_KHACH HK ON DV.MAHK = HK.MAHK
                   JOIN CHUYEN_BAY CB ON DV.MACB = CB.MACB
                   WHERE DV.TRANGTHAI = 'Da Huy'
                   ORDER BY DV.NGAYDAT DESC
                   FETCH FIRST 20 ROWS ONLY"""
            )

        if success and data:
            df = pd.DataFrame(data)
            df.columns = [
                'Mã vé',
                'Hành khách',
                'Mã chuyến bay',
                'Xuất phát',
                'Đích đến',
                'Số ghế',
                'Ngày hủy',
            ]
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mã vé": st.column_config.TextColumn(width=100),
                    "Hành khách": st.column_config.TextColumn(width=150),
                    "Mã chuyến bay": st.column_config.TextColumn(width=100),
                    "Xuất phát": st.column_config.TextColumn(width=120),
                    "Đích đến": st.column_config.TextColumn(width=120),
                    "Số ghế": st.column_config.NumberColumn(format="%d"),
                    "Ngày hủy": st.column_config.TextColumn(width=150)
                }
            )
        else:
            st.info("Chưa có dữ liệu")

    except Exception as e:
        st.error(f"Lỗi: {str(e)}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    
    # ===== BIỂU ĐỒ HÀNH KHÁCH ĐẶT NHIỀU VÉ NHẤT =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Top 10 hành khách đặt nhiều vé nhất")
        
        try:
            success, data = execute_query(
                connection,
                """SELECT HK.HOTEN, COUNT(DV.MAVE) as SO_VE
                   FROM HANH_KHACH HK
                   LEFT JOIN DAT_VE DV ON HK.MAHK = DV.MAHK
                   GROUP BY HK.MAHK, HK.HOTEN
                   ORDER BY SO_VE DESC
                   FETCH FIRST 10 ROWS ONLY"""
            )
            
            if success and data:
                df = pd.DataFrame(data)
                
                fig = px.bar(
                    df,
                    x='SO_VE',
                    y='HOTEN',
                    orientation='h',
                    labels={'SO_VE': 'Số vé', 'HOTEN': 'Hành khách'},
                    color='SO_VE',
                    color_continuous_scale='Blues'
                )
                
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu")
        
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")
    
    # ===== BIỂU ĐỒ CHUYẾN BAY BẬN NHẤT =====
    with col_chart2:
        st.subheader("Top 10 chuyến bay bận nhất")
        
        try:
            success, data = execute_query(
                connection,
                """SELECT CB.MACB, COUNT(DV.MAVE) as SO_VE_DAT
                   FROM CHUYEN_BAY CB
                   LEFT JOIN DAT_VE DV ON CB.MACB = DV.MACB
                   GROUP BY CB.MACB
                   ORDER BY SO_VE_DAT DESC
                   FETCH FIRST 10 ROWS ONLY"""
            )
            
            if success and data:
                df = pd.DataFrame(data)
                
                fig = px.bar(
                    df,
                    x='SO_VE_DAT',
                    y='MACB',
                    orientation='h',
                    labels={'SO_VE_DAT': 'Số vé', 'MACB': 'Chuyến bay'},
                    color='SO_VE_DAT',
                    color_continuous_scale='Greens'
                )
                
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu")
        
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    
    # ===== BIỂU ĐỒ THỐNG KÊ THEO THÁNG =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Thống kê đặt vé theo tháng</div>", unsafe_allow_html=True)
    
    try:
        success, data = execute_query(
            connection,
            """SELECT TO_CHAR(NGAYDAT, 'MM/YYYY') as THANG, COUNT(*) as SO_VE
               FROM DAT_VE
               GROUP BY TO_CHAR(NGAYDAT, 'MM/YYYY')
               ORDER BY TO_DATE(THANG, 'MM/YYYY') DESC"""
        )
        
        if success and data:
            df = pd.DataFrame(data)
            df = df.sort_values('THANG')
            
            fig = px.line(
                df,
                x='THANG',
                y='SO_VE',
                markers=True,
                labels={'THANG': 'Tháng', 'SO_VE': 'Số vé'},
                title="Xu hướng đặt vé theo tháng"
            )
            
            fig.update_layout(
                height=350,
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu")
    
    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    
    # ===== BẢNG CHI TIẾT VÉ ĐẶT GẦN ĐÂY =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>20 vé đặt gần đây nhất</div>", unsafe_allow_html=True)
    
    try:
        success, data = execute_query(
            connection,
            """SELECT DV.MAVE, HK.HOTEN, CB.MACB, 
                      CB.DIEMDI, CB.DIEMDEN, DV.SOGHE,
                      TO_CHAR(DV.NGAYDAT, 'DD/MM/YYYY HH24:MI') as NGAYDAT
               FROM DAT_VE DV
               JOIN HANH_KHACH HK ON DV.MAHK = HK.MAHK
               JOIN CHUYEN_BAY CB ON DV.MACB = CB.MACB
               ORDER BY DV.NGAYDAT DESC
               FETCH FIRST 20 ROWS ONLY"""
        )
        
        if success and data:
            df = pd.DataFrame(data)
            df.columns = ['Mã đặt vé', 'Hành khách', 'Mã chuyến bay', 'Xuất phát', 'Đích đến', 'Số ghế', 'Ngày đặt']
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mã đặt vé": st.column_config.TextColumn(width=100),
                    "Hành khách": st.column_config.TextColumn(width=150),
                    "Mã chuyến bay": st.column_config.TextColumn(width=100),
                    "Xuất phát": st.column_config.TextColumn(width=120),
                    "Đích đến": st.column_config.TextColumn(width=120),
                    "Số ghế": st.column_config.NumberColumn(format="%d"),
                    "Ngày đặt": st.column_config.TextColumn(width=150)
                }
            )
        else:
            st.info("Chưa có dữ liệu")
    
    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
    st.markdown("</div>", unsafe_allow_html=True)
