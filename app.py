import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import random
import string

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & KẾT NỐI GOOGLE SHEETS
# ==============================================================================
st.set_page_config(
    page_title="THPT Phan Bội Châu - Phan Thiết - Quản Lý Giải Đấu",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS làm đẹp
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI GOOGLE SHEETS ---
@st.cache_resource
def get_gsheet_client():
    try:
        # Lấy thông tin từ Secrets
        if "gcp_service_account" in st.secrets:
            key_dict = json.loads(st.secrets["gcp_service_account"])
            
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
            client = gspread.authorize(creds)
            return client
        else:
            st.error("❌ Chưa cấu hình Secrets cho Google Sheets!")
            return None
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Google API: {e}")
        return None

# Kết nối Client
client = get_gsheet_client()

# --- HÀM XỬ LÝ DỮ LIỆU ---

def get_worksheet(sheet_name):
    """Lấy Worksheet, nếu chưa có thì tạo mới (Yêu cầu đã share quyền cho email service account)"""
    try:
        # TÊN FILE GOOGLE SHEET CỦA BẠN (Phải tạo trước và share quyền)
        SPREADSHEET_NAME = "QUAN_LY_GIAI_DAU_PBC" 
        
        sh = client.open(SPREADSHEET_NAME)
        try:
            worksheet = sh.worksheet(sheet_name)
        except:
            # Nếu chưa có sheet con thì tạo mới và thêm header
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            if sheet_name == 'disciplines':
                worksheet.append_row(['id', 'code', 'name', 'createdAt'])
            elif sheet_name == 'units':
                worksheet.append_row(['id', 'name', 'manager', 'registrationCode', 'createdAt'])
            elif sheet_name == 'registrations':
                worksheet.append_row(['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'disciplines', 'createdAt'])
        return worksheet
    except Exception as e:
        st.error(f"⚠️ Không tìm thấy file Google Sheet tên là 'QUAN_LY_GIAI_DAU_PBC'. Hãy tạo file này và share quyền cho service account email.")
        st.stop()

def get_data(sheet_name):
    """Đọc dữ liệu từ Sheet về DataFrame"""
    try:
        ws = get_worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")
        return pd.DataFrame()

def save_data(sheet_name, row_dict):
    """Thêm dòng mới"""
    try:
        ws = get_worksheet(sheet_name)
        
        # Tự tạo ID và Time
        if 'id' not in row_dict:
            row_dict['id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if 'createdAt' not in row_dict:
            row_dict['createdAt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        # Chuyển dict thành list theo đúng thứ tự cột (đơn giản hóa cho demo)
        # Cách an toàn hơn là append dict nhưng gspread cũ hỗ trợ list tốt hơn
        # Ở đây ta dùng list values() nhưng cần đảm bảo thứ tự.
        # Để an toàn, ta lấy header và map value
        headers = ws.row_values(1)
        row_to_add = [row_dict.get(h, "") for h in headers]
        
        ws.append_row(row_to_add)
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu: {e}")
        return False

def delete_data(sheet_name, id_to_delete):
    """Xóa dòng theo ID"""
    try:
        ws = get_worksheet(sheet_name)
        # Tìm dòng chứa ID (cell)
        cell = ws.find(str(id_to_delete))
        if cell:
            ws.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"Lỗi khi xóa: {e}")
        return False

# ==============================================================================
# 3. GIAO DIỆN CHÍNH
# ==============================================================================

def main():
    if not client:
        st.stop()

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2855/2855234.png", width=80)
        st.title("Menu Điều Khiển")
        
        if st.button("🔄 Làm mới dữ liệu"):
            st.cache_data.clear()
            st.rerun()

        menu = st.radio("Chọn chức năng:", 
            ["🏠 Tổng quan", "⚙️ Thiết lập (Admin)", "🏢 Quản lý Đơn vị", "📝 Cổng Đăng Ký", "📊 Xem Kết quả"]
        )
        st.markdown("---")
        st.caption("Backend: Google Sheets")

    # --- 3.1 TỔNG QUAN ---
    if menu == "🏠 Tổng quan":
        st.title("🏆 Hệ Thống Quản Lý Giải Đấu Thể Thao - Phan Bội Châu - Phan Thiết")
        
        df_mon = get_data('disciplines')
        df_dv = get_data('units')
        df_vdv = get_data('registrations')
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Môn thi đấu", f"{len(df_mon)}")
        c2.metric("Đơn vị tham gia", f"{len(df_dv)}")
        c3.metric("Vận động viên", f"{len(df_vdv)}")

    # --- 3.2 THIẾT LẬP ---
    elif menu == "⚙️ Thiết lập (Admin)":
        st.header("⚙️ Thiết lập Giải đấu")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Thêm Môn mới")
            with st.form("add_discipline"):
                code = st.text_input("Mã môn (VD: BD)").upper()
                name = st.text_input("Tên môn (VD: Bóng đá)")
                if st.form_submit_button("Thêm môn"):
                    if code and name:
                        save_data('disciplines', {'code': code, 'name': name})
                        st.success(f"Đã thêm {name}")
                        st.cache_data.clear()
                        st.rerun()
        
        with c2:
            st.subheader("Danh sách Môn thi")
            df = get_data('disciplines')
            if not df.empty:
                st.dataframe(df[['code', 'name']], use_container_width=True)
                del_opt = st.selectbox("Xóa môn:", df['name'].tolist(), index=None)
                if del_opt and st.button("Xác nhận xóa"):
                    id_del = df[df['name'] == del_opt].iloc[0]['id']
                    delete_data('disciplines', id_del)
                    st.cache_data.clear()
                    st.rerun()

    # --- 3.3 QUẢN LÝ ĐƠN VỊ ---
    elif menu == "🏢 Quản lý Đơn vị":
        st.header("🏢 Quản lý Đơn vị")
        
        with st.expander("➕ Thêm Đơn vị / Lớp mới", expanded=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            name = c1.text_input("Tên Đơn vị (VD: 10A1)")
            manager = c2.text_input("Giáo viên phụ trách")
            if c3.button("Tạo Đơn vị", type="primary"):
                if name and manager:
                    reg_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    save_data('units', {'name': name, 'manager': manager, 'registrationCode': reg_code})
                    st.success(f"Mã đăng ký: {reg_code}")
                    st.cache_data.clear()
                    st.rerun()

        st.subheader("Danh sách Đơn vị")
        df = get_data('units')
        if not df.empty:
            st.dataframe(df[['name', 'manager', 'registrationCode']], use_container_width=True)

    # --- 3.4 CỔNG ĐĂNG KÝ ---
    elif menu == "📝 Cổng Đăng Ký":
        st.header("📝 Cổng Đăng Ký Vận Động Viên")
        
        if 'unit_logged_in' not in st.session_state:
            st.session_state.unit_logged_in = None

        if not st.session_state.unit_logged_in:
            code = st.text_input("Nhập Mã Đăng Ký:", max_chars=6).upper()
            if st.button("Đăng nhập"):
                df_units = get_data('units')
                # Chuyển đổi registrationCode sang string để so sánh
                df_units['registrationCode'] = df_units['registrationCode'].astype(str)
                unit = df_units[df_units['registrationCode'] == code]
                if not unit.empty:
                    st.session_state.unit_logged_in = unit.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Mã không đúng!")
        else:
            unit = st.session_state.unit_logged_in
            st.success(f"Đang nhập liệu cho: **{unit['name']}**")
            if st.button("Thoát"):
                st.session_state.unit_logged_in = None
                st.rerun()
            
            with st.form("reg_form"):
                c1, c2, c3 = st.columns(3)
                ath_name = c1.text_input("Họ tên VĐV")
                ath_gender = c2.selectbox("Giới tính", ["Nam", "Nữ"])
                ath_dob = c3.date_input("Ngày sinh", min_value=datetime(2000, 1, 1))
                
                df_disc = get_data('disciplines')
                opts = df_disc['name'].tolist() if not df_disc.empty else []
                selected = st.multiselect("Chọn môn thi:", opts)
                
                if st.form_submit_button("Lưu"):
                    if ath_name and selected:
                        save_data('registrations', {
                            'unitId': unit['id'],
                            'unitName': unit['name'],
                            'athleteName': ath_name,
                            'gender': ath_gender,
                            'dob': str(ath_dob),
                            'disciplines': ", ".join(selected)
                        })
                        st.success("Đã lưu!")
                        st.cache_data.clear()
                        st.rerun()
            
            st.subheader("Danh sách đã đăng ký")
            df_reg = get_data('registrations')
            if not df_reg.empty:
                # Đảm bảo cột unitId là string để so sánh
                df_reg['unitId'] = df_reg['unitId'].astype(str)
                my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
                st.dataframe(my_regs[['athleteName', 'gender', 'disciplines']], use_container_width=True)

    # --- 3.5 KẾT QUẢ ---
    elif menu == "📊 Xem Kết quả":
        st.header("📊 Danh sách Toàn trường")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            st.dataframe(df_reg[['unitName', 'athleteName', 'gender', 'disciplines']], use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")

if __name__ == "__main__":
    main()

