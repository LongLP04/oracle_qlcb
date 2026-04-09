# 🛫 Airline Management System - Python + Streamlit

## 📋 Mô tả dự án
Ứng dụng quản lý đặt vé máy bay với giao diện Streamlit, kết nối Oracle Database thông qua thư viện `oracledb`.

## 🏗️ Cấu trúc dự án

```
Airline_Project/
├── main.py                 # Ứng dụng chính Streamlit
├── database.py             # Hàm kết nối và thao tác Database
├── requirements.txt        # Các thư viện cần cài đặt
├── pages/                  # Các trang ứng dụng
│   ├── __init__.py
│   ├── home.py            # Trang chủ (thống kê tổng quan)
│   ├── booking.py         # Trang đặt vé (gọi SP_DAT_VE)
│   └── report.py          # Trang báo cáo (View dữ liệu)
└── README.md
```

## 🔧 Cài đặt

### 1. Cài đặt các thư viện
```bash
pip install -r requirements.txt
```

### 2. Cấu hình Oracle Client (nếu cần)
Nếu bạn chưa cài Oracle Client, uncomment dòng này trong `database.py`:
```python
oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_21_13")
```

### 3. Chạy ứng dụng
```bash
streamlit run main.py
```

## 📦 Thư viện chính

- **streamlit**: Framework giao diện web
- **oracledb**: Driver kết nối Oracle Database (Python)
- **pandas**: Xử lý dữ liệu bảng

## 🎯 Chức năng

### 🏠 Menu 1: Trang Chủ
- Hiển thị thống kê tổng quan (tổng chuyến bay, hành khách, vé)
- Danh sách máy bay trong hệ thống

### 🎫 Menu 2: Đặt Vé
- Chọn hành khách từ HANH_KHACH
- Chọn chuyến bay từ CHUYEN_BAY
- Nhập số ghế
- **Gọi Procedure**: `PKG_QUAN_LY_DAT_VE.SP_DAT_VE(p_MaHK, p_MaCB, p_SoGhe, p_KetQua)`
- **Xử lý lỗi**: Hiển thị `st.error()` nếu có lỗi ORA-20001 từ Trigger `TRG_MAX_9_VE`
- Danh sách vé đã đặt gần đây

### 📊 Menu 3: Báo Cáo
- **Tab 1**: Top doanh thu từ View `VW_TOP_DOANH_THU` (+ biểu đồ)
- **Tab 2**: Chuyến bay khả thi từ View `VW_CHUYEN_BAY_KHA_THI`
- **Tab 3**: Thống kê chi tiết
  - Hành khách đặt nhiều vé nhất
  - Chuyến bay bận nhất
  - Thống kê theo tháng (biểu đồ)

## 🔐 Bảo mật

### Hàm kết nối an toàn (database.py)
```python
def get_db_connection(host, port, service_name, user, password):
    dsn = oracledb.makedsn(host, port, service_name)
    connection = oracledb.connect(user=user, password=password, dsn=dsn, threaded=True)
    return connection
```

### Xử lý lỗi
- Catch `oracledb.DatabaseError` để xử lý lỗi từ Database
- Rollback transaction nếu lỗi
- Hiển thị thông báo lỗi chi tiết cho người dùng qua `st.error()`

## 🚀 Sử dụng

### Kết nối Database
1. Nhấp vào "Cài đặt Oracle" ở sidebar
2. Nhập thông tin kết nối (Host, Port, Service, User, Password)
3. Nhấp "Kết nối"
4. Nếu thành công, sẽ hiển thị "🟢 Đã kết nối Database"

### Đặt vé
1. Chọn "🎫 Đặt vé" từ menu
2. Chọn hành khách và chuyến bay
3. Nhập số ghế
4. Nhấp "✅ Đặt Vé"
5. Nếu đặt vé thành công, sẽ hiển thị thông báo `st.success()`
6. Nếu lỗi ORA-20001, sẽ hiển thị `st.error("❌ LỖI: Không được đặt quá 9 vé!")`

### Xem báo cáo
1. Chọn "📊 Báo cáo" từ menu
2. Xem các tab khác nhau (doanh thu, chuyến bay, thống kê)

## 📝 Ghi chú

- Tất cả thao tác với Database sử dụng `connection.commit()` và `connection.rollback()`
- Session state Streamlit lưu trữ kết nối Database (`st.session_state.connection`)
- Sidebar cập nhật trạng thái kết nối real-time

## 🔄 Kế tiếp

Khi bạn yêu cầu viết từng chức năng cụ thể, hãy nêu:
- Tên Procedure/View chính xác
- Tên cột trong bảng
- Quy tắc validate (nếu có)

**Tôi sẽ tuân thủ đúng tên và cập nhật code!**
