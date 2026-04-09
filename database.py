import oracledb
from typing import Optional
import streamlit as st

# ==================== CẤU HÌNH ORACLEDB THIN MODE ====================
# Sử dụng Thin Mode - không cần Oracle Client
oracledb.defaults.config_dir = None

# ==================== THÔNG SỐ KẾT NỐI MẶC ĐỊNH ====================
DB_CONFIG = {
    "host": "localhost",
    "port": 1521,
    "sid": "xe",
    "username": "NHOM3_AIRLINE",
    "password": "123456"
}

# ==================== HÀM KẾT NỐI AN TOÀN ====================
def get_db_connection(
    host: str = DB_CONFIG["host"],
    port: int = DB_CONFIG["port"],
    sid: str = DB_CONFIG["sid"],
    username: str = DB_CONFIG["username"],
    password: str = DB_CONFIG["password"]
) -> Optional[oracledb.Connection]:
    """
    Kết nối an toàn đến Oracle Database sử dụng oracledb Thin Mode.
    
    Args:
        host: Địa chỉ server Oracle (mặc định: localhost)
        port: Cổng kết nối (mặc định: 1521)
        sid: SID hoặc Service Name (mặc định: xe)
        username: Tên người dùng (mặc định: NHOM3_AIRLINE)
        password: Mật khẩu (mặc định: 123456)
    
    Returns:
        oracledb.Connection object nếu thành công
    
    Raises:
        Exception: Nếu kết nối thất bại
    """
    try:
        # Tạo DSN (Data Source Name) từ thông số
        dsn = oracledb.makedsn(
            host=host,
            port=port,
            sid=sid
        )
        
        # Kết nối đến Oracle Database
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=dsn
        )
        
        return connection
    
    except oracledb.DatabaseError as db_error:
        error_msg = str(db_error)
        raise Exception(f"❌ Lỗi Database: {error_msg}")
    
    except oracledb.InterfaceError as if_error:
        error_msg = str(if_error)
        raise Exception(f"❌ Lỗi kết nối: {error_msg}")
    
    except Exception as e:
        raise Exception(f"❌ Lỗi không xác định: {str(e)}")

# ==================== HÀM KIỂM TRA KẾT NỐI ====================
def test_connection(
    host: str = DB_CONFIG["host"],
    port: int = DB_CONFIG["port"],
    sid: str = DB_CONFIG["sid"],
    username: str = DB_CONFIG["username"],
    password: str = DB_CONFIG["password"]
) -> tuple[bool, str]:
    """
    Kiểm tra kết nối đến Oracle Database.
    
    Args:
        host, port, sid, username, password: Thông số kết nối
    
    Returns:
        Tuple (success: bool, message: str)
    """
    try:
        connection = get_db_connection(host, port, sid, username, password)
        connection.close()
        return True, "✅ Kết nối thành công!"
    except Exception as e:
        return False, str(e)

# ==================== HÀM ĐÓNG KẾT NỐI ====================
def close_db_connection(connection: oracledb.Connection) -> None:
    """
    Đóng kết nối Oracle Database an toàn.
    
    Args:
        connection: oracledb.Connection object cần đóng
    """
    try:
        if connection:
            connection.close()
    except Exception as e:
        if st:
            st.error(f"Lỗi khi đóng kết nối: {str(e)}")
        else:
            print(f"Lỗi khi đóng kết nối: {str(e)}")

# ==================== HÀM EXECUTE PROCEDURE ====================
def call_procedure(
    connection: oracledb.Connection,
    procedure_name: str,
    parameters: list = None
) -> dict:
    """
    Gọi Procedure Oracle và trả về kết quả.
    
    Args:
        connection: oracledb.Connection object
        procedure_name: Tên procedure (ví dụ: 'PKG_QUAN_LY_DAT_VE.SP_DAT_VE')
        parameters: Danh sách tham số
    
    Returns:
        Dict chứa kết quả hoặc lỗi
    """
    cursor = None
    try:
        cursor = connection.cursor()
        
        if parameters is None:
            parameters = []
        
        cursor.callproc(procedure_name, parameters)
        connection.commit()
        
        return {
            "success": True,
            "message": "Procedure thực thi thành công",
            "output": parameters
        }
    
    except oracledb.DatabaseError as db_error:
        connection.rollback()
        error_code = db_error.args[0].code if hasattr(db_error.args[0], 'code') else None
        return {
            "success": False,
            "error_code": error_code,
            "message": str(db_error),
            "output": None
        }
    except Exception as e:
        connection.rollback()
        return {
            "success": False,
            "message": f"Lỗi: {str(e)}",
            "output": None
        }
    finally:
        cursor.close()

# ==================== HÀM QUERY DATA ====================
def execute_query(
    connection: oracledb.Connection,
    query: str,
    params: tuple = None
) -> tuple[bool, list | str]:
    """
    Thực thi câu SELECT từ Database.
    
    Args:
        connection: oracledb.Connection object
        query: SQL SELECT statement
        params: Tuple của tham số (nếu có)
    
    Returns:
        Tuple (success: bool, data: list hoặc error message: str)
    """
    try:
        cursor = connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        # Chuyển đổi sang danh sách dictionary
        data = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        return True, data
    
    except Exception as e:
        return False, str(e)

# ==================== HÀM INSERT/UPDATE/DELETE ====================
def execute_update(
    connection: oracledb.Connection,
    query: str,
    params: tuple = None
) -> tuple[bool, str]:
    """
    Thực thi câu INSERT/UPDATE/DELETE từ Database.
    
    Args:
        connection: oracledb.Connection object
        query: SQL INSERT/UPDATE/DELETE statement
        params: Tuple của tham số
    
    Returns:
        Tuple (success: bool, message: str)
    """
    try:
        cursor = connection.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        connection.commit()
        rows_affected = cursor.rowcount
        
        return True, f"Thành công! Ảnh hưởng {rows_affected} dòng"
    
    except oracledb.IntegrityError as ie:
        connection.rollback()
        return False, f"Lỗi dữ liệu: {str(ie)}"
    except oracledb.DatabaseError as db_error:
        connection.rollback()
        return False, f"Lỗi Database: {str(db_error)}"
    except Exception as e:
        connection.rollback()
        return False, f"Lỗi: {str(e)}"
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except oracledb.InterfaceError:
                pass
