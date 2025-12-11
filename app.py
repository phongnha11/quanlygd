import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import random
import string
import time

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & KẾT NỐI GOOGLE SHEETS
# ==============================================================================
st.set_page_config(
    page_title="THPT Phan Bội Châu - Quản Lý Giải Đấu",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mật khẩu Admin mặc định (Bạn nên đổi mật khẩu này)
ADMIN_PASSWORD = "admin123"

# CSS làm đẹp
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #2c3e50; }
    div[data-testid="stExpander"] details summary p { font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- KẾT NỐI GOOGLE SHEETS ---
@st.cache_resource
def get_gsheet_client():
    try:
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

client = get_gsheet_client()

# --- HÀM XỬ LÝ DỮ LIỆU ---
def get_worksheet(sheet_name):
    try:
        SPREADSHEET_NAME = "QUAN_LY_GIAI_DAU_PBC" 
        sh = client.open(SPREADSHEET_NAME)
        try:
            worksheet = sh.worksheet(sheet_name)
        except:
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            if sheet_name == 'disciplines':
                worksheet.append_row(['id', 'code', 'name', 'createdAt'])
            elif sheet_name == 'units':
                worksheet.append_row(['id', 'name', 'manager', 'registrationCode', 'createdAt'])
            elif sheet_name == 'registrations':
                worksheet.append_row(['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'disciplines', 'createdAt'])
        return worksheet
    except Exception as e:
        st.error(f"⚠️ Không tìm thấy file Google Sheet '{SPREADSHEET_NAME}'.")
        st.stop()

def get_data(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Lỗi đọc dữ liệu: {e}")
        return pd.DataFrame()

def save_data(sheet_name, row_dict):
    try:
        ws = get_worksheet(sheet_name)
        if 'id' not in row_dict:
            row_dict['id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if 'createdAt' not in row_dict:
            row_dict['createdAt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        headers = ws.row_values(1)
        row_to_add = [row_dict.get(h, "") for h in headers]
        ws.append_row(row_to_add)
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu: {e}")
        return False

def delete_data(sheet_name, id_to_delete):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(id_to_delete))
        if cell:
            ws.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"Lỗi khi xóa: {e}")
        return False

# ==============================================================================
# 3. GIAO DIỆN CHÍNH (LOGIC PHÂN QUYỀN)
# ==============================================================================

def main():
    if not client:
        st.stop()

    # --- KHỞI TẠO SESSION STATE CHO ĐĂNG NHẬP ---
    if 'role' not in st.session_state:
        st.session_state.role = 'guest' # Các role: 'guest', 'admin', 'unit'
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None

    # --- SIDEBAR: ĐIỀU KHIỂN & ĐĂNG NHẬP ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2855/2855234.png", width=80)
        st.title("Hệ Thống Giải Đấu")
        
        # --- KHU VỰC ĐĂNG NHẬP ---
        if st.session_state.role == 'guest':
            st.info("👋 Bạn đang xem với tư cách Khách.")
            with st.expander("🔐 Đăng nhập Hệ thống", expanded=True):
                login_mode = st.radio("Đối tượng:", ["Quản trị viên (Admin)", "Đơn vị (Lớp)"])
                
                if login_mode == "Quản trị viên (Admin)":
                    pwd = st.text_input("Mật khẩu Admin", type="password")
                    if st.button("Đăng nhập Admin"):
                        if pwd == ADMIN_PASSWORD:
                            st.session_state.role = 'admin'
                            st.success("Đăng nhập thành công!")
                            st.rerun()
                        else:
                            st.error("Sai mật khẩu!")
                
                else: # Đăng nhập Đơn vị
                    code_input = st.text_input("Mã Đăng Ký (6 ký tự)", max_chars=6).upper()
                    if st.button("Đăng nhập Đơn vị"):
                        df_units = get_data('units')
                        if not df_units.empty:
                            df_units['registrationCode'] = df_units['registrationCode'].astype(str)
                            unit_found = df_units[df_units['registrationCode'] == code_input]
                            if not unit_found.empty:
                                st.session_state.role = 'unit'
                                st.session_state.user_info = unit_found.iloc[0].to_dict()
                                st.success(f"Chào {unit_found.iloc[0]['name']}!")
                                st.rerun()
                            else:
                                st.error("Mã không đúng!")
                        else:
                            st.error("Chưa có đơn vị nào.")

        else:
            # ĐÃ ĐĂNG NHẬP
            if st.session_state.role == 'admin':
                st.success("👤 **ADMINISTRATOR**")
            elif st.session_state.role == 'unit':
                u_name = st.session_state.user_info['name']
                st.success(f"👤 Đơn vị: **{u_name}**")
            
            if st.button("Đăng xuất"):
                st.session_state.role = 'guest'
                st.session_state.user_info = None
                st.rerun()
        
        st.markdown("---")
        
        # --- MENU ĐỘNG THEO VAI TRÒ ---
        menu_options = ["🏠 Tổng quan", "📊 Xem Kết quả"] # Menu mặc định cho Guest
        
        if st.session_state.role == 'admin':
            menu_options = ["🏠 Tổng quan", "⚙️ Thiết lập (Admin)", "🏢 Quản lý Đơn vị", "📊 Xem Kết quả"]
        elif st.session_state.role == 'unit':
            menu_options = ["🏠 Tổng quan", "📝 Đăng ký thi đấu", "📊 Xem Kết quả"]
            
        menu = st.radio("Chọn chức năng:", menu_options)
        
        if st.session_state.role == 'admin':
            if st.button("🔄 Refresh Data"):
                st.cache_data.clear()
                st.rerun()

    # ==========================================================================
    # ROUTING (ĐIỀU HƯỚNG TRANG)
    # ==========================================================================

    # --- 1. TỔNG QUAN (Ai cũng xem được) ---
    if menu == "🏠 Tổng quan":
        st.title("🏆 Tổng Quan Giải Đấu")
        
        df_mon = get_data('disciplines')
        df_dv = get_data('units')
        df_vdv = get_data('registrations')
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Môn thi đấu", f"{len(df_mon)}")
        c2.metric("Đơn vị tham gia", f"{len(df_dv)}")
        c3.metric("Vận động viên", f"{len(df_vdv)}")
        
        if st.session_state.role == 'guest':
            st.info("💡 Đăng nhập để thực hiện các chức năng quản lý hoặc đăng ký thi đấu.")

    # --- 2. THIẾT LẬP (Chỉ Admin) ---
    elif menu == "⚙️ Thiết lập (Admin)":
        if st.session_state.role != 'admin':
            st.error("Bạn không có quyền truy cập trang này.")
            st.stop()
            
        st.header("⚙️ Thiết lập Hệ thống")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Thêm Môn mới")
            with st.form("add_discipline"):
                code = st.text_input("Mã môn (VD: BD)").upper()
                name = st.text_input("Tên môn (VD: Bóng đá)")
                if st.form_submit_button("Thêm môn", type="primary"):
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

    # --- 3. QUẢN LÝ ĐƠN VỊ (Chỉ Admin) ---
    elif menu == "🏢 Quản lý Đơn vị":
        if st.session_state.role != 'admin':
            st.error("Bạn không có quyền truy cập trang này.")
            st.stop()

        st.header("🏢 Quản lý Đơn vị & Cấp Mã")
        
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

    # --- 4. ĐĂNG KÝ THI ĐẤU (Chỉ Đơn vị) ---
    elif menu == "📝 Đăng ký thi đấu":
        if st.session_state.role != 'unit':
            st.error("Vui lòng đăng nhập bằng Mã Đơn vị để truy cập.")
            st.stop()
            
        unit = st.session_state.user_info
        st.header(f"📝 Cổng Đăng Ký: {unit['name']}")
        st.caption(f"Phụ trách: {unit['manager']}")
        
        with st.form("reg_form"):
            st.subheader("Nhập thông tin VĐV")
            c1, c2, c3 = st.columns(3)
            ath_name = c1.text_input("Họ tên VĐV")
            ath_gender = c2.selectbox("Giới tính", ["Nam", "Nữ"])
            ath_dob = c3.date_input("Ngày sinh", min_value=datetime(2000, 1, 1))
            
            df_disc = get_data('disciplines')
            opts = df_disc['name'].tolist() if not df_disc.empty else []
            if not opts:
                st.warning("Chưa có môn thi nào được tạo bởi Admin.")
                
            selected = st.multiselect("Chọn môn thi:", opts)
            
            if st.form_submit_button("Lưu Đăng Ký", type="primary"):
                if ath_name and selected:
                    save_data('registrations', {
                        'unitId': unit['id'],
                        'unitName': unit['name'],
                        'athleteName': ath_name,
                        'gender': ath_gender,
                        'dob': str(ath_dob),
                        'disciplines': ", ".join(selected)
                    })
                    st.success("Đã lưu thành công!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Vui lòng nhập tên và chọn ít nhất 1 môn.")
        
        st.divider()
        st.subheader(f"Danh sách VĐV của {unit['name']}")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            if not my_regs.empty:
                st.dataframe(my_regs[['athleteName', 'gender', 'dob', 'disciplines']], use_container_width=True)
            else:
                st.info("Chưa có VĐV nào được đăng ký.")
        else:
            st.info("Chưa có dữ liệu.")

    # --- 5. XEM KẾT QUẢ (Ai cũng xem được) ---
    elif menu == "📊 Xem Kết quả":
        st.header("📊 Danh sách Đăng ký Toàn trường")
        
        # Bộ lọc tìm kiếm
        search = st.text_input("🔍 Tìm kiếm VĐV hoặc Đơn vị:", placeholder="Nhập tên...")
        
        df_reg = get_data('registrations')
        if not df_reg.empty:
            view_df = df_reg[['unitName', 'athleteName', 'gender', 'disciplines']]
            
            if search:
                mask = view_df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
                view_df = view_df[mask]
                
            st.dataframe(view_df, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")

if __name__ == "__main__":
    main()
