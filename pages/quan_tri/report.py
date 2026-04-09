import streamlit as st
from database import execute_query
import pandas as pd
import plotly.express as px

# ==================== TRANG BÁO CÁO ====================
def render(connection):
    """Trang báo cáo và thống kê"""
    
    st.markdown("<div class='page-title'>Báo cáo và thống kê</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Báo cáo chi tiết về doanh thu và hoạt động bay</div>", unsafe_allow_html=True)
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    
    # ===== TABS BÁO CÁO =====
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Top doanh thu", "Chuyến bay khả thi", "Thống kê chi tiết"])
    
    # ===== TAB 1: TOP DOANH THU =====
    with tab1:
        st.subheader("Top chuyến bay theo doanh thu")
        st.markdown("Xem các chuyến bay có doanh thu cao nhất (View VW_TOP_DOANH_THU)")
        
        try:
            success, top_revenue = execute_query(
                connection,
                "SELECT * FROM VW_TOP_DOANH_THU ORDER BY DOANH_THU DESC FETCH FIRST 10 ROWS ONLY"
            )
            
            if not success or not top_revenue:
                success, top_revenue = execute_query(
                    connection,
                    """SELECT CB.MACB,
                              SUM(CASE WHEN DV.TRANGTHAI = 'Da Huy' THEN 0 ELSE CB.GIAVECOBAN END) AS DOANH_THU
                       FROM CHUYEN_BAY CB
                       LEFT JOIN DAT_VE DV ON CB.MACB = DV.MACB
                       GROUP BY CB.MACB
                       ORDER BY DOANH_THU DESC
                       FETCH FIRST 10 ROWS ONLY"""
                )

            if success and top_revenue:
                df = pd.DataFrame(top_revenue)
                st.dataframe(df, use_container_width=True, hide_index=True)

                if 'MACB' in df.columns and 'DOANH_THU' in df.columns:
                    fig = px.bar(
                        df,
                        x='MACB',
                        y='DOANH_THU',
                        labels={'MACB': 'Chuyến bay', 'DOANH_THU': 'Doanh thu'},
                        color='DOANH_THU',
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Không có dữ liệu báo cáo doanh thu")
        
        except Exception as e:
            st.error(f"Lỗi khi lấy dữ liệu: {str(e)}")
    
    # ===== TAB 2: CHUYẾN BAY KHẢ THI =====
    with tab2:
        st.subheader("Chuyến bay khả thi")
        st.markdown("Xem danh sách chuyến bay sắp khởi hành (View VW_CHUYEN_BAY_KHA_THI)")
        
        try:
            success, available_flights = execute_query(
                connection,
                "SELECT * FROM VW_CHUYEN_BAY_KHA_THI ORDER BY THOIGIAN_KHOI_HANH"
            )
            
            if not success or not available_flights:
                success, available_flights = execute_query(
                    connection,
                    """SELECT MACB, DIEMDI, DIEMDEN, NGAYGIOKHOIHANH, GIAVECOBAN
                       FROM CHUYEN_BAY
                       WHERE NGAYGIOKHOIHANH >= SYSDATE
                       ORDER BY NGAYGIOKHOIHANH"""
                )

            if success and available_flights:
                df = pd.DataFrame(available_flights)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"Tổng cộng: **{len(df)}** chuyến bay khả thi")
            else:
                st.warning("Không có chuyến bay khả thi")
        
        except Exception as e:
            st.error(f"Lỗi khi lấy dữ liệu: {str(e)}")
    
    # ===== TAB 3: THỐNG KÊ CHI TIẾT =====
    with tab3:
        st.subheader("Thống kê chi tiết")
        
        sub_col1, sub_col2 = st.columns(2)
        
        # ===== THỐNG KÊ HÀNH KHÁCH =====
        with sub_col1:
            st.markdown("**Hành khách đặt nhiều vé nhất:**")
            
            try:
                success, top_passengers = execute_query(
                    connection,
                    """SELECT HK.HOTEN, COUNT(DV.MAVE) as SO_VE
                       FROM HANH_KHACH HK
                       LEFT JOIN DAT_VE DV ON HK.MAHK = DV.MAHK
                       GROUP BY HK.MAHK, HK.HOTEN
                       ORDER BY SO_VE DESC
                       FETCH FIRST 10 ROWS ONLY"""
                )
                
                if success and top_passengers:
                    df = pd.DataFrame(top_passengers)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Chưa có dữ liệu")
            
            except Exception as e:
                st.error(f"Lỗi: {str(e)}")
        
        # ===== THỐNG KÊ CHUYẾN BAY =====
        with sub_col2:
            st.markdown("**Chuyến bay bận nhất:**")
            
            try:
                success, busy_flights = execute_query(
                    connection,
                    """SELECT CB.MACB, COUNT(DV.MAVE) as SO_VE_DAT
                       FROM CHUYEN_BAY CB
                       LEFT JOIN DAT_VE DV ON CB.MACB = DV.MACB
                       GROUP BY CB.MACB
                       ORDER BY SO_VE_DAT DESC
                       FETCH FIRST 10 ROWS ONLY"""
                )
                
                if success and busy_flights:
                    df = pd.DataFrame(busy_flights)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Chưa có dữ liệu")
            
            except Exception as e:
                st.error(f"Lỗi: {str(e)}")
        
        st.markdown("---")
        
        # ===== THỐNG KÊ THEO THÁNG =====
        st.markdown("**Thống kê đặt vé theo tháng:**")
        
        try:
            success, monthly_stats = execute_query(
                connection,
                """SELECT TO_CHAR(NGAYDAT, 'MM/YYYY') as THANG, COUNT(*) as SO_VE
                   FROM DAT_VE
                   GROUP BY TO_CHAR(NGAYDAT, 'MM/YYYY')
                   ORDER BY THANG DESC"""
            )
            
            if success and monthly_stats:
                df = pd.DataFrame(monthly_stats)
                
                fig = px.line(
                    df,
                    x='THANG',
                    y='SO_VE',
                    markers=True,
                    labels={'THANG': 'Tháng', 'SO_VE': 'Số vé'}
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Chưa có dữ liệu")
        
        except Exception as e:
            st.error(f"Lỗi: {str(e)}")
    st.markdown("</div>", unsafe_allow_html=True)
