import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import random
import string
import timeimport streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import random
import string
import time

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==============================================================================
st.set_page_config(
    page_title="Hệ thống Quản lý Giải đấu Thể thao",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

ADMIN_PASSWORD = "admin123"

# CSS Tùy chỉnh
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1e3a8a; }
    .edit-form { background-color: #e0f2fe; padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    .success-msg { color: green; font-weight: bold; }
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
            return gspread.authorize(creds)
        else:
            st.error("❌ Chưa cấu hình Secrets!")
            return None
    except Exception as e:
        st.error(f"❌ Lỗi kết nối: {e}")
        return None

client = get_gsheet_client()

# --- HÀM KIỂM TRA VÀ CẬP NHẬT HEADER ---
def sync_headers(ws, sheet_name):
    # Định nghĩa cấu trúc cột cho các bảng
    expected_headers = {
        'config': ['key', 'value'],
        'systems': ['id', 'name', 'createdAt'],
        'age_groups': ['id', 'name', 'description', 'createdAt'],
        'disciplines': ['id', 'code', 'name', 'is_exempt', 'createdAt'],
        'contents': ['id', 'discipline_id', 'name', 'gender', 'createdAt'],
        'units': ['id', 'name', 'manager', 'registrationCode', 'rank', 'createdAt'],
        'registrations': ['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'cccd', 'studentId', 'systemName', 'ageGroup', 'registered_contents', 'rank', 'createdAt']
    }
    
    if sheet_name in expected_headers:
        try:
            current_headers = ws.row_values(1)
            missing_cols = [h for h in expected_headers[sheet_name] if h not in current_headers]
            if missing_cols:
                start_col = len(current_headers) + 1
                for i, header in enumerate(missing_cols):
                    ws.update_cell(1, start_col + i, header)
                time.sleep(0.5)
        except Exception as e:
            print(f"Lỗi sync header: {e}")

# --- HÀM XỬ LÝ DỮ LIỆU ---
def get_worksheet(sheet_name):
    try:
        SPREADSHEET_NAME = "QUAN_LY_GIAI_DAU_PBC" 
        sh = client.open(SPREADSHEET_NAME)
        try:
            worksheet = sh.worksheet(sheet_name)
            sync_headers(worksheet, sheet_name)
        except:
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            sync_headers(worksheet, sheet_name)
        return worksheet
    except Exception as e:
        st.error(f"⚠️ Không tìm thấy file Google Sheet '{SPREADSHEET_NAME}'.")
        st.stop()

def ensure_columns(df, required_cols):
    if df.empty:
        return pd.DataFrame(columns=required_cols)
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" 
    return df

def get_data(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if sheet_name == 'registrations':
            required = ['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'cccd', 'studentId', 'systemName', 'ageGroup', 'registered_contents', 'rank', 'createdAt']
            df = ensure_columns(df, required)
        elif sheet_name == 'units':
            df = ensure_columns(df, ['id', 'name', 'manager', 'registrationCode', 'rank', 'createdAt'])
        elif sheet_name == 'age_groups':
            df = ensure_columns(df, ['id', 'name', 'description', 'createdAt'])
        return df
    except:
        return pd.DataFrame()

def save_data(sheet_name, row_dict):
    try:
        ws = get_worksheet(sheet_name)
        if 'id' not in row_dict:
            row_dict['id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if 'createdAt' not in row_dict:
            row_dict['createdAt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        headers = ws.row_values(1)
        row_to_add = [str(row_dict.get(h, "")) for h in headers]
        ws.append_row(row_to_add)
        return True
    except Exception as e:
        st.error(f"Lỗi lưu: {e}")
        return False

def update_row_data(sheet_name, doc_id, updated_data):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(doc_id))
        if not cell:
            return False
        
        headers = ws.row_values(1)
        row_idx = cell.row
        
        for key, value in updated_data.items():
            if key in headers:
                col_idx = headers.index(key) + 1
                ws.update_cell(row_idx, col_idx, str(value))
        return True
    except Exception as e:
        st.error(f"Lỗi update: {e}")
        return False

def update_cell(sheet_name, doc_id, col_name, new_value):
    return update_row_data(sheet_name, doc_id, {col_name: new_value})

def delete_data(sheet_name, id_to_delete):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(id_to_delete))
        if cell:
            ws.delete_rows(cell.row)
            return True
        return False
    except:
        return False

# --- CONFIG ---
def get_config(key):
    df = get_data('config')
    if not df.empty:
        df = ensure_columns(df, ['key', 'value'])
        row = df[df['key'] == key]
        if not row.empty:
            return row.iloc[0]['value']
    return None

def set_config(key, value):
    ws = get_worksheet('config')
    try:
        cell = ws.find(key)
        if cell:
            ws.update_cell(cell.row, 2, str(value))
        else:
            ws.append_row([key, str(value)])
    except:
        ws.append_row([key, str(value)])


# ==============================================================================
# 2. GIAO DIỆN CHÍNH
# ==============================================================================

def main():
    if not client:
        st.stop()

    if 'role' not in st.session_state:
        st.session_state.role = 'guest'
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    
    if 'editing_athlete' not in st.session_state:
        st.session_state.editing_athlete = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏅 Điều Khiển Giải Đấu")
        
        if st.session_state.role == 'guest':
            with st.expander("🔐 Đăng nhập", expanded=True):
                mode = st.radio("Vai trò:", ["Đơn vị (Lớp)", "Admin"], key="login_role_radio")
                if mode == "Admin":
                    pwd = st.text_input("Mật khẩu", type="password", key="admin_pwd_input")
                    if st.button("Vào trang Admin", key="btn_login_admin"):
                        if pwd == ADMIN_PASSWORD:
                            st.session_state.role = 'admin'
                            st.rerun()
                        else:
                            st.error("Sai mật khẩu")
                else:
                    code = st.text_input("Mã Đăng Ký", max_chars=6, key="unit_code_input").upper()
                    if st.button("Đăng nhập Đơn vị", key="btn_login_unit"):
                        df = get_data('units')
                        if not df.empty:
                            df['registrationCode'] = df['registrationCode'].astype(str)
                            u = df[df['registrationCode'] == code]
                            if not u.empty:
                                st.session_state.role = 'unit'
                                st.session_state.user_info = u.iloc[0].to_dict()
                                st.rerun()
                            else:
                                st.error("Mã không đúng")
                        else:
                            st.error("Chưa có dữ liệu")
        else:
            role_name = "ADMIN" if st.session_state.role == 'admin' else st.session_state.user_info['name']
            st.success(f"Xin chào: **{role_name}**")
            
            if st.button("Đăng xuất", key="logout_btn"):
                st.session_state.role = 'guest'
                st.session_state.user_info = None
                st.session_state.editing_athlete = None
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.role == 'admin':
            menu = st.radio("Chức năng:", [
                "🏠 Tổng quan", 
                "⚙️ Cấu hình Giải đấu", 
                "🏅 Môn & Nội dung thi", 
                "🏢 Quản lý Đơn vị", 
                "🏆 Cập nhật Kết quả",
                "📊 Xuất danh sách thi đấu"
            ], key="menu_admin")
        elif st.session_state.role == 'unit':
            menu = st.radio("Chức năng:", ["🏠 Tổng quan", "📝 Đăng ký thi đấu", "📊 Xuất danh sách"], key="menu_unit")
        else:
            menu = "🏠 Tổng quan"

    # --- ROUTING ---
    
    # 1. TỔNG QUAN
    if menu == "🏠 Tổng quan":
        st.title("🏆 Thông Tin Giải Đấu")
        deadline_str = get_config('deadline')
        tournament_name = get_config('tournament_name') or "Giải Thể Thao Học Đường"
        st.header(tournament_name)
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                days_left = (deadline - date.today()).days
                if days_left >= 0:
                    st.info(f"📅 Hạn đăng ký: **{deadline_str}** (Còn {days_left} ngày)")
                else:
                    st.error(f"🔴 Đã hết hạn đăng ký từ ngày {deadline_str}")
            except: pass
        
        df_reg = get_data('registrations')
        c1, c2, c3 = st.columns(3)
        c1.metric("Vận động viên", len(df_reg))
        c2.metric("Đơn vị tham gia", len(get_data('units')))
        c3.metric("Môn thi đấu", len(get_data('disciplines')))

        if not df_reg.empty:
            st.subheader("Bảng vàng cá nhân")
            winners = df_reg[df_reg['rank'].isin(['Nhất', 'Nhì', 'Ba'])]
            if not winners.empty:
                cols = ['athleteName', 'unitName', 'rank']
                if 'registered_contents' in winners.columns: cols.insert(2, 'registered_contents')
                st.dataframe(winners[cols], use_container_width=True)
        
        # Hiển thị bảng vàng đơn vị (nếu có)
        df_units = get_data('units')
        if not df_units.empty and 'rank' in df_units.columns:
            unit_winners = df_units[df_units['rank'].astype(str).str.len() > 0]
            if not unit_winners.empty:
                st.subheader("Bảng vàng Đơn vị")
                st.dataframe(unit_winners[['name', 'manager', 'rank']], use_container_width=True)

    # 2. CẤU HÌNH (ADMIN)
    elif menu == "⚙️ Cấu hình Giải đấu":
        st.header("⚙️ Thiết lập Chung")
        
        tab1, tab2 = st.tabs(["Thông tin & Quy tắc", "Hệ thi đấu & Lứa tuổi"])
        
        with tab1:
            with st.form("config_form"):
                st.subheader("1. Thông tin chung")
                t_name = st.text_input("Tên giải đấu", value=get_config('tournament_name') or "")
                deadline = st.date_input("Hạn chót đăng ký", value=datetime.today())
                
                st.subheader("2. Quy tắc Đăng ký")
                st.caption("Các quy tắc này sẽ kiểm tra khi đơn vị đăng ký VĐV.")
                max_disc = st.number_input("Số môn tối đa 1 VĐV được tham gia:", min_value=1, value=int(get_config('max_disciplines') or 3))
                max_cont = st.number_input("Số nội dung tối đa 1 VĐV được tham gia (trong 1 môn):", min_value=1, value=int(get_config('max_contents') or 2))
                
                if st.form_submit_button("Lưu Cấu hình"):
                    set_config('tournament_name', t_name)
                    set_config('deadline', str(deadline))
                    set_config('max_disciplines', max_disc)
                    set_config('max_contents', max_cont)
                    st.success("Đã lưu cấu hình!")
                    time.sleep(1)
                    st.rerun()

        with tab2:
            c_sys, c_age = st.columns(2)
            
            with c_sys:
                st.subheader("Hệ thi đấu")
                with st.form("add_sys"):
                    new_sys = st.text_input("Thêm Hệ mới (VD: Phong trào):")
                    if st.form_submit_button("Thêm Hệ"):
                        if new_sys: 
                            save_data('systems', {'name': new_sys})
                            st.rerun()
                
                df_sys = get_data('systems')
                if not df_sys.empty:
                    st.dataframe(df_sys[['name']], use_container_width=True)
                    del_sys = st.selectbox("Xóa Hệ:", df_sys['name'], key="del_sys_sel", index=None)
                    if del_sys and st.button("Xóa Hệ", key="btn_del_sys"):
                        sid = df_sys[df_sys['name']==del_sys].iloc[0]['id']
                        delete_data('systems', sid)
                        st.rerun()

            with c_age:
                st.subheader("Khai báo Lứa tuổi")
                st.caption("Khai báo các nhóm tuổi áp dụng cho các môn thi đấu.")
                with st.form("add_age"):
                    new_age = st.text_input("Tên Lứa tuổi (VD: U15, 16-18):")
                    age_desc = st.text_input("Mô tả (VD: Sinh năm 2008-2010):")
                    if st.form_submit_button("Thêm Lứa tuổi"):
                        if new_age:
                            save_data('age_groups', {'name': new_age, 'description': age_desc})
                            st.rerun()
                
                df_age = get_data('age_groups')
                if not df_age.empty:
                    st.dataframe(df_age[['name', 'description']], use_container_width=True)
                    del_age = st.selectbox("Xóa Lứa tuổi:", df_age['name'], key="del_age_sel", index=None)
                    if del_age and st.button("Xóa Lứa tuổi", key="btn_del_age"):
                        aid = df_age[df_age['name']==del_age].iloc[0]['id']
                        delete_data('age_groups', aid)
                        st.rerun()

    # 3. MÔN & NỘI DUNG (ADMIN)
    elif menu == "🏅 Môn & Nội dung thi":
        st.header("🏅 Quản lý Môn & Nội dung")
        c1, c2 = st.columns([1, 2])
        with c1: 
            st.subheader("1. Thêm Môn thi")
            with st.form("add_disc"):
                d_code = st.text_input("Mã môn (VD: BD)").upper()
                d_name = st.text_input("Tên môn (VD: Bóng đá)")
                d_exempt = st.checkbox("Môn này KHÔNG áp dụng quy tắc giới hạn?")
                if st.form_submit_button("Thêm Môn"):
                    if d_code and d_name:
                        save_data('disciplines', {'code': d_code, 'name': d_name, 'is_exempt': 'True' if d_exempt else 'False'})
                        st.success(f"Đã thêm {d_name}")
                        st.cache_data.clear()
                        st.rerun()
        
        with c2: 
            st.subheader("2. Thêm Nội dung thi đấu")
            df_disc = get_data('disciplines')
            if not df_disc.empty:
                selected_disc_name = st.selectbox("Chọn Môn thi đấu:", df_disc['name'].tolist(), key="sel_disc_setup")
                selected_disc = df_disc[df_disc['name'] == selected_disc_name].iloc[0]
                with st.form("add_content"):
                    c_name = st.text_input(f"Tên nội dung thuộc môn {selected_disc_name}")
                    c_gender = st.selectbox("Dành cho:", ["Nam", "Nữ", "Nam & Nữ"])
                    if st.form_submit_button("Thêm Nội dung"):
                        if c_name:
                            save_data('contents', {'discipline_id': selected_disc['id'], 'name': c_name, 'gender': c_gender})
                            st.success("Đã thêm!")
                            st.cache_data.clear()
                            st.rerun()
                st.write(f"**Nội dung của {selected_disc_name}:**")
                df_contents = get_data('contents')
                if not df_contents.empty:
                    df_contents['discipline_id'] = df_contents['discipline_id'].astype(str)
                    my_contents = df_contents[df_contents['discipline_id'] == str(selected_disc['id'])]
                    if not my_contents.empty:
                        for _, row in my_contents.iterrows():
                            cc1, cc2 = st.columns([4, 1])
                            cc1.text(f"- {row['name']} ({row['gender']})")
                            if cc2.button("Xóa", key=f"dc_{row['id']}"):
                                delete_data('contents', row['id'])
                                st.rerun()
                    else: st.caption("Chưa có nội dung.")
            else: st.warning("Vui lòng tạo môn trước.")

    # 4. QUẢN LÝ ĐƠN VỊ (ADMIN)
    elif menu == "🏢 Quản lý Đơn vị":
        st.header("🏢 Quản lý Đơn vị")
        
        with st.expander("➕ Cấp tài khoản mới", expanded=False):
            u_name = st.text_input("Tên Đơn vị/Lớp", key="new_u_name_inp")
            u_man = st.text_input("Người phụ trách", key="new_u_man_inp")
            if st.button("Tạo", key="btn_create_unit"):
                if u_name:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    save_data('units', {'name': u_name, 'manager': u_man, 'registrationCode': code})
                    st.success(f"Mã: {code}")
                    st.cache_data.clear()
                    st.rerun()
        
        st.divider()
        st.subheader("Danh sách & Thao tác")
        df = get_data('units')
        
        if not df.empty:
            unit_names = df['name'].tolist()
            selected_unit_name = st.selectbox("Chọn đơn vị để sửa/xóa:", ["-- Chọn --"] + unit_names, key="sel_unit_edit")
            
            if selected_unit_name != "-- Chọn --":
                selected_unit = df[df['name'] == selected_unit_name].iloc[0]
                
                with st.container(border=True):
                    st.markdown(f"**Đang thao tác: {selected_unit['name']}** (Mã: `{selected_unit['registrationCode']}`)")
                    
                    c1, c2 = st.columns(2)
                    new_u_name = c1.text_input("Tên Đơn vị", value=selected_unit['name'], key="edit_u_name")
                    new_u_man = c2.text_input("Người phụ trách", value=selected_unit['manager'], key="edit_u_man")
                    
                    col_save, col_del = st.columns([1, 1])
                    
                    if col_save.button("Lưu thay đổi", type="primary", key="save_unit_btn"):
                        if update_row_data('units', selected_unit['id'], {'name': new_u_name, 'manager': new_u_man}):
                            st.success("Đã cập nhật!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    
                    if col_del.button("🗑️ Xóa Đơn vị này", key="del_unit_btn"):
                        if delete_data('units', selected_unit['id']):
                            st.warning("Đã xóa đơn vị.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
            
            st.dataframe(df[['name', 'manager', 'registrationCode']], use_container_width=True)
        else:
            st.info("Chưa có đơn vị nào.")

    # 5. CẬP NHẬT KẾT QUẢ (ADMIN)
    elif menu == "🏆 Cập nhật Kết quả":
        st.header("🏆 Cập nhật Thành tích")
        
        tab_ind, tab_unit = st.tabs(["Cá nhân/Đồng đội", "Toàn Đơn vị"])
        
        # 5.1 Xếp hạng VĐV
        with tab_ind:
            df_reg = get_data('registrations')
            if df_reg.empty:
                st.info("Chưa có dữ liệu đăng ký.")
            else:
                col_search, col_rank = st.columns(2)
                search_txt = col_search.text_input("Tìm tên VĐV/Đơn vị:", key="search_res")
                view_df = df_reg.copy()
                if search_txt:
                    view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)]
                
                st.write("---")
                athlete_opts = []
                for idx, row in view_df.iterrows():
                    cont = row.get('registered_contents', 'N/A')
                    name = row.get('athleteName', 'Unknown')
                    unit = row.get('unitName', 'Unknown')
                    athlete_opts.append(f"{name} ({unit}) - {cont}")

                selected_str = st.selectbox("Chọn VĐV:", athlete_opts, key="sel_athlete_res")
                if selected_str:
                    selected_idx = athlete_opts.index(selected_str)
                    selected_id = view_df.iloc[selected_idx]['id']
                    
                    current_rank = view_df.iloc[selected_idx].get('rank', '')
                    st.write(f"Thành tích hiện tại: **{current_rank or 'Chưa có'}**")
                    
                    new_rank = st.selectbox("Cập nhật Thành tích:", ["", "Nhất", "Nhì", "Ba", "Khuyến Khích", "Hoàn thành"], key="sel_rank_ind")
                    if st.button("Lưu Kết quả Cá nhân", key="btn_save_rank_ind"):
                        if update_cell('registrations', selected_id, 'rank', new_rank):
                            st.success("Đã cập nhật!")
                            st.cache_data.clear()
                            st.rerun()
        
        # 5.2 Xếp hạng Đơn vị
        with tab_unit:
            st.subheader("Cập nhật Thứ hạng cho Đơn vị")
            df_units = get_data('units')
            if df_units.empty:
                st.info("Chưa có đơn vị nào.")
            else:
                unit_names = df_units['name'].tolist()
                sel_unit = st.selectbox("Chọn Đơn vị:", unit_names, key="sel_unit_rank")
                
                if sel_unit:
                    unit_row = df_units[df_units['name'] == sel_unit].iloc[0]
                    cur_u_rank = unit_row.get('rank', '')
                    st.write(f"Thứ hạng hiện tại: **{cur_u_rank or 'Chưa có'}**")
                    
                    new_u_rank = st.selectbox("Xếp hạng Toàn đoàn:", ["", "Nhất", "Nhì", "Ba", "Khuyến Khích"], key="new_u_rank")
                    if st.button("Lưu Kết quả Đơn vị", key="btn_save_rank_unit"):
                        if update_cell('units', unit_row['id'], 'rank', new_u_rank):
                            st.success(f"Đã cập nhật thứ hạng cho {sel_unit}!")
                            st.cache_data.clear()
                            st.rerun()

    # 6. XUẤT DANH SÁCH THI ĐẤU (ADMIN)
    elif menu == "📊 Xuất danh sách thi đấu":
        st.header("📊 Xuất danh sách thi đấu")
        st.caption("Xuất danh sách VĐV theo từng Môn và Nội dung thi đấu.")
        
        df_disc = get_data('disciplines')
        df_cont = get_data('contents')
        df_reg = get_data('registrations')
        
        if df_disc.empty or df_reg.empty:
            st.warning("Chưa có đủ dữ liệu Môn thi hoặc VĐV đăng ký.")
        else:
            # Chọn Môn
            sel_disc_name = st.selectbox("1. Chọn Môn thi đấu:", df_disc['name'].tolist(), key="sel_exp_disc")
            
            # Chọn Nội dung (Lọc theo môn)
            sel_disc_id = str(df_disc[df_disc['name'] == sel_disc_name].iloc[0]['id'])
            df_cont['discipline_id'] = df_cont['discipline_id'].astype(str)
            valid_contents = df_cont[df_cont['discipline_id'] == sel_disc_id]['name'].tolist()
            content_opts = ["-- Tất cả --"] + valid_contents + [f"{sel_disc_name} (Chung)"]
            
            sel_content = st.selectbox("2. Chọn Nội dung:", content_opts, key="sel_exp_cont")
            
            if st.button("Tải danh sách", type="primary", key="btn_load_export"):
                if sel_content == "-- Tất cả --":
                    search_key = f"{sel_disc_name}:" 
                else:
                    search_key = f"{sel_disc_name}: {sel_content}"
                
                filtered_df = df_reg[df_reg['registered_contents'].astype(str).str.contains(search_key, na=False)]
                
                if not filtered_df.empty:
                    st.success(f"Tìm thấy {len(filtered_df)} VĐV.")
                    export_cols = ['athleteName', 'gender', 'dob', 'unitName', 'registered_contents', 'studentId', 'ageGroup']
                    final_cols = [c for c in export_cols if c in filtered_df.columns]
                    csv = filtered_df[final_cols].to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 Tải danh sách {sel_disc_name}.csv",
                        data=csv,
                        file_name=f"danh_sach_{sel_disc_name}_{sel_content}.csv",
                        mime="text/csv"
                    )
                    st.dataframe(filtered_df[final_cols], use_container_width=True)
                else:
                    st.warning("Không tìm thấy VĐV nào đăng ký nội dung này.")

    # 7. ĐĂNG KÝ THI ĐẤU (UNIT)
    elif menu == "📝 Đăng ký thi đấu":
        unit = st.session_state.user_info
        st.header(f"📝 Đăng ký: {unit['name']}")
        
        edit_data = st.session_state.editing_athlete
        is_editing = edit_data is not None
        form_title = "✏️ Cập nhật thông tin VĐV" if is_editing else "➕ Đăng ký VĐV Mới"
        
        df_sys = get_data('systems')
        sys_opts = df_sys['name'].tolist() if not df_sys.empty else ["Mặc định"]
        df_disc = get_data('disciplines')
        df_cont = get_data('contents')
        df_ages = get_data('age_groups')
        age_opts = df_ages['name'].tolist() if not df_ages.empty else ["Tự do"]

        if is_editing:
            st.markdown(f'<div class="edit-form">Đang chỉnh sửa VĐV: <b>{edit_data.get("athleteName")}</b></div>', unsafe_allow_html=True)

        with st.form("reg_form_v2"):
            st.subheader(form_title)
            
            def_name = edit_data.get('athleteName', '') if is_editing else ''
            def_gender_idx = 0 if is_editing and edit_data.get('gender') == 'Nam' else 1 if is_editing and edit_data.get('gender') == 'Nữ' else 0
            try:
                def_dob = datetime.strptime(edit_data.get('dob', '2008-01-01'), '%Y-%m-%d').date() if is_editing else date(2008, 1, 1)
            except: def_dob = date(2008, 1, 1)
            def_cccd = edit_data.get('cccd', '') if is_editing else ''
            def_sid = edit_data.get('studentId', '') if is_editing else ''
            
            def_age_idx = 0
            if is_editing and edit_data.get('ageGroup') in age_opts:
                def_age_idx = age_opts.index(edit_data.get('ageGroup'))
            
            def_sys_idx = 0
            if is_editing and edit_data.get('systemName') in sys_opts:
                def_sys_idx = sys_opts.index(edit_data.get('systemName'))

            c1, c2, c3, c4 = st.columns(4)
            a_name = c1.text_input("Họ tên (*)", value=def_name)
            a_gender = c2.selectbox("Giới tính", ["Nam", "Nữ"], index=def_gender_idx)
            a_dob = c3.date_input("Ngày sinh", value=def_dob, min_value=date(1990, 1, 1))
            a_cccd = c4.text_input("Số CCCD", value=def_cccd)
            
            c5, c6, c7 = st.columns(3)
            a_sid = c5.text_input("Mã học sinh/CCVC", value=def_sid)
            a_age_group = c6.selectbox("Lứa tuổi", age_opts, index=def_age_idx)
            a_system = c7.selectbox("Hệ thi đấu", sys_opts, index=def_sys_idx)
            
            st.divider()
            st.subheader("Nội dung Thi đấu")
            
            selected_contents_text = []
            current_contents = []
            if is_editing and edit_data.get('registered_contents'):
                current_contents = edit_data.get('registered_contents').split('; ')

            max_disc_cfg = int(get_config('max_disciplines') or 100)
            max_cont_cfg = int(get_config('max_contents') or 100)
            count_disc_selected = 0
            error_msg = []

            if not df_disc.empty:
                for _, disc in df_disc.iterrows():
                    with st.expander(f"🏅 Môn {disc['name']}", expanded=is_editing):
                        is_exempt = str(disc.get('is_exempt', 'False')) == 'True'
                        
                        if not df_cont.empty:
                            df_cont['discipline_id'] = df_cont['discipline_id'].astype(str)
                            sub_contents = df_cont[df_cont['discipline_id'] == str(disc['id'])]
                            
                            if not sub_contents.empty:
                                available_opts = sub_contents['name'].tolist()
                                defaults = []
                                if is_editing:
                                    for opt in available_opts:
                                        if f"{disc['name']}: {opt}" in current_contents:
                                            defaults.append(opt)
                                
                                conts = st.multiselect(f"Chọn nội dung {disc['name']}:", available_opts, default=defaults, key=f"m_sel_{disc['id']}")
                                if conts:
                                    if not is_exempt: count_disc_selected += 1
                                    if not is_exempt and len(conts) > max_cont_cfg:
                                        error_msg.append(f"Môn {disc['name']} chỉ được chọn tối đa {max_cont_cfg} nội dung.")
                                    for c in conts: selected_contents_text.append(f"{disc['name']}: {c}")
                            else:
                                st.caption("Chưa có nội dung cụ thể.")
                                is_checked = False
                                if is_editing and f"{disc['name']} (Chung)" in current_contents:
                                    is_checked = True
                                if st.checkbox(f"Đăng ký {disc['name']} (Chung)", key=f"chk_{disc['id']}", value=is_checked):
                                    if not is_exempt: count_disc_selected += 1
                                    selected_contents_text.append(f"{disc['name']} (Chung)")
            
            if count_disc_selected > max_disc_cfg:
                error_msg.append(f"VĐV chỉ được tham gia tối đa {max_disc_cfg} môn thi (không tính môn ngoại lệ).")

            st.info(f"Đang chọn: {', '.join(selected_contents_text)}")
            if error_msg:
                for err in error_msg: st.error(err)
            
            submit_label = "Cập nhật VĐV" if is_editing else "Lưu Đăng Ký"
            c_sub, c_cancel = st.columns([1, 1])
            disabled_btn = bool(error_msg)
            
            submitted = c_sub.form_submit_button(submit_label, type="primary", disabled=disabled_btn)
            if is_editing:
                cancelled = c_cancel.form_submit_button("Hủy bỏ")
                if cancelled:
                    st.session_state.editing_athlete = None
                    st.rerun()

            if submitted:
                if a_name and selected_contents_text:
                    payload = {
                        'unitId': unit['id'],
                        'unitName': unit['name'],
                        'athleteName': a_name,
                        'gender': a_gender,
                        'dob': str(a_dob),
                        'cccd': a_cccd,
                        'studentId': a_sid,
                        'systemName': a_system,
                        'ageGroup': a_age_group,
                        'registered_contents': "; ".join(selected_contents_text)
                    }
                    if is_editing:
                        if update_row_data('registrations', edit_data['id'], payload):
                            st.success("Đã cập nhật thành công!")
                            st.session_state.editing_athlete = None
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    else:
                        save_data('registrations', payload)
                        st.success("Đăng ký thành công!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Thiếu tên hoặc chưa chọn nội dung thi đấu.")

        st.subheader("Danh sách đã đăng ký")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            
            if not my_regs.empty:
                for idx, row in my_regs.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        s_name = row.get('athleteName', 'N/A')
                        s_gender = row.get('gender', '')
                        s_cont = row.get('registered_contents', '')
                        s_age = row.get('ageGroup', '')

                        c1.markdown(f"**{s_name}** ({s_gender}) - {s_age}")
                        c1.caption(f"ID: {row.get('studentId','')} - {row.get('dob','')}")
                        c2.write(f"🎯 {s_cont}")
                        
                        col_edit, col_del = c3.columns(2)
                        if col_edit.button("✏️", key=f"ed_{row['id']}", help="Sửa thông tin VĐV này"):
                            st.session_state.editing_athlete = row.to_dict()
                            st.rerun()
                        if col_del.button("🗑️", key=f"del_{row['id']}", help="Xóa VĐV này"):
                            delete_data('registrations', row['id'])
                            if st.session_state.editing_athlete and st.session_state.editing_athlete['id'] == row['id']:
                                st.session_state.editing_athlete = None
                            st.rerun()

    # 8. XUẤT DANH SÁCH (UNIT)
    elif menu == "📊 Xuất danh sách":
        unit = st.session_state.user_info
        st.title("📊 Xuất dữ liệu")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            if not my_regs.empty:
                cols_order = ['athleteName', 'gender', 'dob', 'studentId', 'cccd', 'systemName', 'ageGroup', 'registered_contents', 'rank']
                final_cols = [c for c in cols_order if c in my_regs.columns]
                st.dataframe(my_regs[final_cols], use_container_width=True)
                csv = my_regs[final_cols].to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 Tải CSV", data=csv, file_name=f"ds_{unit['name']}.csv", mime="text/csv")
            else: st.info("Chưa có dữ liệu.")

if __name__ == "__main__":
    main()

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==============================================================================
st.set_page_config(
    page_title="Hệ thống Quản lý Giải đấu Thể thao",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

ADMIN_PASSWORD = "admin123"

# CSS Tùy chỉnh
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1e3a8a; }
    .edit-form { background-color: #e0f2fe; padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    .success-msg { color: green; font-weight: bold; }
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
            return gspread.authorize(creds)
        else:
            st.error("❌ Chưa cấu hình Secrets!")
            return None
    except Exception as e:
        st.error(f"❌ Lỗi kết nối: {e}")
        return None

client = get_gsheet_client()

# --- HÀM KIỂM TRA VÀ CẬP NHẬT HEADER ---
def sync_headers(ws, sheet_name):
    # Định nghĩa cấu trúc cột cho các bảng
    expected_headers = {
        'config': ['key', 'value'],
        'systems': ['id', 'name', 'createdAt'],
        'age_groups': ['id', 'name', 'description', 'createdAt'], # Thêm bảng Lứa tuổi
        'disciplines': ['id', 'code', 'name', 'is_exempt', 'createdAt'],
        'contents': ['id', 'discipline_id', 'name', 'gender', 'createdAt'],
        'units': ['id', 'name', 'manager', 'registrationCode', 'rank', 'createdAt'], # Thêm cột rank cho đơn vị
        'registrations': ['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'cccd', 'studentId', 'systemName', 'ageGroup', 'registered_contents', 'rank', 'createdAt']
    }
    
    if sheet_name in expected_headers:
        try:
            current_headers = ws.row_values(1)
            missing_cols = [h for h in expected_headers[sheet_name] if h not in current_headers]
            if missing_cols:
                start_col = len(current_headers) + 1
                for i, header in enumerate(missing_cols):
                    ws.update_cell(1, start_col + i, header)
                time.sleep(0.5)
        except Exception as e:
            print(f"Lỗi sync header: {e}")

# --- HÀM XỬ LÝ DỮ LIỆU ---
def get_worksheet(sheet_name):
    try:
        SPREADSHEET_NAME = "QUAN_LY_GIAI_DAU_PBC" 
        sh = client.open(SPREADSHEET_NAME)
        try:
            worksheet = sh.worksheet(sheet_name)
            sync_headers(worksheet, sheet_name)
        except:
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            # Khởi tạo header nếu tạo mới sheet
            sync_headers(worksheet, sheet_name)
        return worksheet
    except Exception as e:
        st.error(f"⚠️ Không tìm thấy file Google Sheet '{SPREADSHEET_NAME}'.")
        st.stop()

def ensure_columns(df, required_cols):
    if df.empty:
        return pd.DataFrame(columns=required_cols)
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" 
    return df

def get_data(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # Đảm bảo các bảng quan trọng luôn đủ cột
        if sheet_name == 'registrations':
            required = ['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'cccd', 'studentId', 'systemName', 'ageGroup', 'registered_contents', 'rank', 'createdAt']
            df = ensure_columns(df, required)
        elif sheet_name == 'units':
            df = ensure_columns(df, ['id', 'name', 'manager', 'registrationCode', 'rank', 'createdAt'])
        elif sheet_name == 'age_groups':
            df = ensure_columns(df, ['id', 'name', 'description', 'createdAt'])
        return df
    except:
        return pd.DataFrame()

def save_data(sheet_name, row_dict):
    try:
        ws = get_worksheet(sheet_name)
        if 'id' not in row_dict:
            row_dict['id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if 'createdAt' not in row_dict:
            row_dict['createdAt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        headers = ws.row_values(1)
        row_to_add = [str(row_dict.get(h, "")) for h in headers]
        ws.append_row(row_to_add)
        return True
    except Exception as e:
        st.error(f"Lỗi lưu: {e}")
        return False

def update_row_data(sheet_name, doc_id, updated_data):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(doc_id))
        if not cell:
            return False
        
        headers = ws.row_values(1)
        row_idx = cell.row
        
        for key, value in updated_data.items():
            if key in headers:
                col_idx = headers.index(key) + 1
                ws.update_cell(row_idx, col_idx, str(value))
        return True
    except Exception as e:
        st.error(f"Lỗi update: {e}")
        return False

def update_cell(sheet_name, doc_id, col_name, new_value):
    return update_row_data(sheet_name, doc_id, {col_name: new_value})

def delete_data(sheet_name, id_to_delete):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(id_to_delete))
        if cell:
            ws.delete_rows(cell.row)
            return True
        return False
    except:
        return False

# --- CONFIG ---
def get_config(key):
    df = get_data('config')
    if not df.empty:
        df = ensure_columns(df, ['key', 'value'])
        row = df[df['key'] == key]
        if not row.empty:
            return row.iloc[0]['value']
    return None

def set_config(key, value):
    ws = get_worksheet('config')
    try:
        cell = ws.find(key)
        if cell:
            ws.update_cell(cell.row, 2, str(value))
        else:
            ws.append_row([key, str(value)])
    except:
        ws.append_row([key, str(value)])


# ==============================================================================
# 2. GIAO DIỆN CHÍNH
# ==============================================================================

def main():
    if not client:
        st.stop()

    if 'role' not in st.session_state:
        st.session_state.role = 'guest'
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    
    if 'editing_athlete' not in st.session_state:
        st.session_state.editing_athlete = None

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏅 Điều Khiển Giải Đấu")
        
        if st.session_state.role == 'guest':
            with st.expander("🔐 Đăng nhập", expanded=True):
                mode = st.radio("Vai trò:", ["Đơn vị (Lớp)", "Admin"])
                if mode == "Admin":
                    pwd = st.text_input("Mật khẩu", type="password")
                    if st.button("Vào trang Admin"):
                        if pwd == ADMIN_PASSWORD:
                            st.session_state.role = 'admin'
                            st.rerun()
                        else:
                            st.error("Sai mật khẩu")
                else:
                    code = st.text_input("Mã Đăng Ký", max_chars=6).upper()
                    if st.button("Đăng nhập Đơn vị"):
                        df = get_data('units')
                        if not df.empty:
                            df['registrationCode'] = df['registrationCode'].astype(str)
                            u = df[df['registrationCode'] == code]
                            if not u.empty:
                                st.session_state.role = 'unit'
                                st.session_state.user_info = u.iloc[0].to_dict()
                                st.rerun()
                            else:
                                st.error("Mã không đúng")
                        else:
                            st.error("Chưa có dữ liệu")
        else:
            role_name = "ADMIN" if st.session_state.role == 'admin' else st.session_state.user_info['name']
            st.success(f"Xin chào: **{role_name}**")
            
            if st.button("Đăng xuất", key="logout_btn"):
                st.session_state.role = 'guest'
                st.session_state.user_info = None
                st.session_state.editing_athlete = None
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.role == 'admin':
            menu = st.radio("Chức năng:", [
                "🏠 Tổng quan", 
                "⚙️ Cấu hình Giải đấu", 
                "🏅 Môn & Nội dung thi", 
                "🏢 Quản lý Đơn vị", 
                "🏆 Cập nhật Kết quả",
                "📊 Xuất danh sách thi đấu" # Mục mới
            ])
        elif st.session_state.role == 'unit':
            menu = st.radio("Chức năng:", ["🏠 Tổng quan", "📝 Đăng ký thi đấu", "📊 Xuất danh sách"])
        else:
            menu = "🏠 Tổng quan"

    # --- ROUTING ---
    
    # 1. TỔNG QUAN
    if menu == "🏠 Tổng quan":
        st.title("🏆 Thông Tin Giải Đấu")
        deadline_str = get_config('deadline')
        tournament_name = get_config('tournament_name') or "Giải Thể Thao Học Đường"
        st.header(tournament_name)
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                days_left = (deadline - date.today()).days
                if days_left >= 0:
                    st.info(f"📅 Hạn đăng ký: **{deadline_str}** (Còn {days_left} ngày)")
                else:
                    st.error(f"🔴 Đã hết hạn đăng ký từ ngày {deadline_str}")
            except: pass
        
        df_reg = get_data('registrations')
        c1, c2, c3 = st.columns(3)
        c1.metric("Vận động viên", len(df_reg))
        c2.metric("Đơn vị tham gia", len(get_data('units')))
        c3.metric("Môn thi đấu", len(get_data('disciplines')))

        if not df_reg.empty:
            st.subheader("Bảng vàng cá nhân")
            winners = df_reg[df_reg['rank'].isin(['Nhất', 'Nhì', 'Ba'])]
            if not winners.empty:
                cols = ['athleteName', 'unitName', 'rank']
                if 'registered_contents' in winners.columns: cols.insert(2, 'registered_contents')
                st.dataframe(winners[cols], use_container_width=True)
        
        # Hiển thị bảng vàng đơn vị (nếu có)
        df_units = get_data('units')
        if not df_units.empty and 'rank' in df_units.columns:
            unit_winners = df_units[df_units['rank'].astype(str).str.len() > 0]
            if not unit_winners.empty:
                st.subheader("Bảng vàng Đơn vị")
                st.dataframe(unit_winners[['name', 'manager', 'rank']], use_container_width=True)

    # 2. CẤU HÌNH (ADMIN)
    elif menu == "⚙️ Cấu hình Giải đấu":
        st.header("⚙️ Thiết lập Chung")
        
        # Tab cấu hình
        tab1, tab2 = st.tabs(["Thông tin & Quy tắc", "Hệ thi đấu & Lứa tuổi"])
        
        with tab1:
            with st.form("config_form"):
                st.subheader("1. Thông tin chung")
                t_name = st.text_input("Tên giải đấu", value=get_config('tournament_name') or "")
                deadline = st.date_input("Hạn chót đăng ký", value=datetime.today())
                
                st.subheader("2. Quy tắc Đăng ký")
                st.caption("Các quy tắc này sẽ kiểm tra khi đơn vị đăng ký VĐV.")
                max_disc = st.number_input("Số môn tối đa 1 VĐV được tham gia:", min_value=1, value=int(get_config('max_disciplines') or 3))
                max_cont = st.number_input("Số nội dung tối đa 1 VĐV được tham gia (trong 1 môn):", min_value=1, value=int(get_config('max_contents') or 2))
                
                if st.form_submit_button("Lưu Cấu hình"):
                    set_config('tournament_name', t_name)
                    set_config('deadline', str(deadline))
                    set_config('max_disciplines', max_disc)
                    set_config('max_contents', max_cont)
                    st.success("Đã lưu cấu hình!")
                    time.sleep(1)
                    st.rerun()

        with tab2:
            c_sys, c_age = st.columns(2)
            
            # Cột Hệ thi đấu
            with c_sys:
                st.subheader("Hệ thi đấu")
                with st.form("add_sys"):
                    new_sys = st.text_input("Thêm Hệ mới (VD: Phong trào):")
                    if st.form_submit_button("Thêm Hệ"):
                        if new_sys: 
                            save_data('systems', {'name': new_sys})
                            st.rerun()
                
                df_sys = get_data('systems')
                if not df_sys.empty:
                    st.dataframe(df_sys[['name']], use_container_width=True)
                    del_sys = st.selectbox("Xóa Hệ:", df_sys['name'], key="del_sys_sel", index=None)
                    if del_sys and st.button("Xóa Hệ"):
                        sid = df_sys[df_sys['name']==del_sys].iloc[0]['id']
                        delete_data('systems', sid)
                        st.rerun()

            # Cột Lứa tuổi (MỚI)
            with c_age:
                st.subheader("Khai báo Lứa tuổi")
                st.caption("Khai báo các nhóm tuổi áp dụng cho các môn thi đấu.")
                with st.form("add_age"):
                    new_age = st.text_input("Tên Lứa tuổi (VD: U15, 16-18):")
                    age_desc = st.text_input("Mô tả (VD: Sinh năm 2008-2010):")
                    if st.form_submit_button("Thêm Lứa tuổi"):
                        if new_age:
                            save_data('age_groups', {'name': new_age, 'description': age_desc})
                            st.rerun()
                
                df_age = get_data('age_groups')
                if not df_age.empty:
                    st.dataframe(df_age[['name', 'description']], use_container_width=True)
                    del_age = st.selectbox("Xóa Lứa tuổi:", df_age['name'], key="del_age_sel", index=None)
                    if del_age and st.button("Xóa Lứa tuổi"):
                        aid = df_age[df_age['name']==del_age].iloc[0]['id']
                        delete_data('age_groups', aid)
                        st.rerun()

    # 3. MÔN & NỘI DUNG (ADMIN)
    elif menu == "🏅 Môn & Nội dung thi":
        st.header("🏅 Quản lý Môn & Nội dung")
        c1, c2 = st.columns([1, 2])
        with c1: 
            st.subheader("1. Thêm Môn thi")
            with st.form("add_disc"):
                d_code = st.text_input("Mã môn (VD: BD)").upper()
                d_name = st.text_input("Tên môn (VD: Bóng đá)")
                d_exempt = st.checkbox("Môn này KHÔNG áp dụng quy tắc giới hạn?")
                if st.form_submit_button("Thêm Môn"):
                    if d_code and d_name:
                        save_data('disciplines', {'code': d_code, 'name': d_name, 'is_exempt': 'True' if d_exempt else 'False'})
                        st.success(f"Đã thêm {d_name}")
                        st.cache_data.clear()
                        st.rerun()
        
        with c2: 
            st.subheader("2. Thêm Nội dung thi đấu")
            df_disc = get_data('disciplines')
            if not df_disc.empty:
                selected_disc_name = st.selectbox("Chọn Môn thi đấu:", df_disc['name'].tolist())
                selected_disc = df_disc[df_disc['name'] == selected_disc_name].iloc[0]
                with st.form("add_content"):
                    c_name = st.text_input(f"Tên nội dung thuộc môn {selected_disc_name}")
                    c_gender = st.selectbox("Dành cho:", ["Nam", "Nữ", "Nam & Nữ"])
                    if st.form_submit_button("Thêm Nội dung"):
                        if c_name:
                            save_data('contents', {'discipline_id': selected_disc['id'], 'name': c_name, 'gender': c_gender})
                            st.success("Đã thêm!")
                            st.cache_data.clear()
                            st.rerun()
                st.write(f"**Nội dung của {selected_disc_name}:**")
                df_contents = get_data('contents')
                if not df_contents.empty:
                    df_contents['discipline_id'] = df_contents['discipline_id'].astype(str)
                    my_contents = df_contents[df_contents['discipline_id'] == str(selected_disc['id'])]
                    if not my_contents.empty:
                        for _, row in my_contents.iterrows():
                            cc1, cc2 = st.columns([4, 1])
                            cc1.text(f"- {row['name']} ({row['gender']})")
                            if cc2.button("Xóa", key=f"dc_{row['id']}"):
                                delete_data('contents', row['id'])
                                st.rerun()
                    else: st.caption("Chưa có nội dung.")
            else: st.warning("Vui lòng tạo môn trước.")

    # 4. QUẢN LÝ ĐƠN VỊ (ADMIN)
    elif menu == "🏢 Quản lý Đơn vị":
        st.header("🏢 Quản lý Đơn vị")
        
        with st.expander("➕ Cấp tài khoản mới", expanded=False):
            u_name = st.text_input("Tên Đơn vị/Lớp")
            u_man = st.text_input("Người phụ trách")
            if st.button("Tạo"):
                if u_name:
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    save_data('units', {'name': u_name, 'manager': u_man, 'registrationCode': code})
                    st.success(f"Mã: {code}")
                    st.cache_data.clear()
                    st.rerun()
        
        st.divider()
        st.subheader("Danh sách & Thao tác")
        df = get_data('units')
        
        if not df.empty:
            unit_names = df['name'].tolist()
            selected_unit_name = st.selectbox("Chọn đơn vị để sửa/xóa:", ["-- Chọn --"] + unit_names)
            
            if selected_unit_name != "-- Chọn --":
                selected_unit = df[df['name'] == selected_unit_name].iloc[0]
                
                with st.container(border=True):
                    st.markdown(f"**Đang thao tác: {selected_unit['name']}** (Mã: `{selected_unit['registrationCode']}`)")
                    
                    c1, c2 = st.columns(2)
                    new_u_name = c1.text_input("Tên Đơn vị", value=selected_unit['name'])
                    new_u_man = c2.text_input("Người phụ trách", value=selected_unit['manager'])
                    
                    col_save, col_del = st.columns([1, 1])
                    
                    if col_save.button("Lưu thay đổi", type="primary", key="save_unit_btn"):
                        if update_row_data('units', selected_unit['id'], {'name': new_u_name, 'manager': new_u_man}):
                            st.success("Đã cập nhật!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    
                    if col_del.button("🗑️ Xóa Đơn vị này", key="del_unit_btn"):
                        if delete_data('units', selected_unit['id']):
                            st.warning("Đã xóa đơn vị.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
            
            st.dataframe(df[['name', 'manager', 'registrationCode']], use_container_width=True)
        else:
            st.info("Chưa có đơn vị nào.")

    # 5. CẬP NHẬT KẾT QUẢ (ADMIN) - ĐÃ CẬP NHẬT
    elif menu == "🏆 Cập nhật Kết quả":
        st.header("🏆 Cập nhật Thành tích")
        
        tab_ind, tab_unit = st.tabs(["Cá nhân/Đồng đội", "Toàn Đơn vị"])
        
        # 5.1 Xếp hạng VĐV
        with tab_ind:
            df_reg = get_data('registrations')
            if df_reg.empty:
                st.info("Chưa có dữ liệu đăng ký.")
            else:
                col_search, col_rank = st.columns(2)
                search_txt = col_search.text_input("Tìm tên VĐV/Đơn vị:", key="search_res")
                view_df = df_reg.copy()
                if search_txt:
                    view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)]
                
                st.write("---")
                athlete_opts = []
                for idx, row in view_df.iterrows():
                    cont = row.get('registered_contents', 'N/A')
                    name = row.get('athleteName', 'Unknown')
                    unit = row.get('unitName', 'Unknown')
                    athlete_opts.append(f"{name} ({unit}) - {cont}")

                selected_str = st.selectbox("Chọn VĐV:", athlete_opts)
                if selected_str:
                    selected_idx = athlete_opts.index(selected_str)
                    selected_id = view_df.iloc[selected_idx]['id']
                    
                    # Hiện trạng thái cũ
                    current_rank = view_df.iloc[selected_idx].get('rank', '')
                    st.write(f"Thành tích hiện tại: **{current_rank or 'Chưa có'}**")
                    
                    new_rank = st.selectbox("Cập nhật Thành tích:", ["", "Nhất", "Nhì", "Ba", "Khuyến Khích", "Hoàn thành"])
                    if st.button("Lưu Kết quả Cá nhân"):
                        if update_cell('registrations', selected_id, 'rank', new_rank):
                            st.success("Đã cập nhật!")
                            st.cache_data.clear()
                            st.rerun()
        
        # 5.2 Xếp hạng Đơn vị (MỚI)
        with tab_unit:
            st.subheader("Cập nhật Thứ hạng cho Đơn vị")
            df_units = get_data('units')
            if df_units.empty:
                st.info("Chưa có đơn vị nào.")
            else:
                unit_names = df_units['name'].tolist()
                sel_unit = st.selectbox("Chọn Đơn vị:", unit_names, key="sel_unit_rank")
                
                if sel_unit:
                    unit_row = df_units[df_units['name'] == sel_unit].iloc[0]
                    cur_u_rank = unit_row.get('rank', '')
                    st.write(f"Thứ hạng hiện tại: **{cur_u_rank or 'Chưa có'}**")
                    
                    new_u_rank = st.selectbox("Xếp hạng Toàn đoàn:", ["", "Nhất", "Nhì", "Ba", "Khuyến Khích"], key="new_u_rank")
                    if st.button("Lưu Kết quả Đơn vị"):
                        if update_cell('units', unit_row['id'], 'rank', new_u_rank):
                            st.success(f"Đã cập nhật thứ hạng cho {sel_unit}!")
                            st.cache_data.clear()
                            st.rerun()

    # 6. XUẤT DANH SÁCH THI ĐẤU (ADMIN - MỚI)
    elif menu == "📊 Xuất danh sách thi đấu":
        st.header("📊 Xuất danh sách thi đấu")
        st.caption("Xuất danh sách VĐV theo từng Môn và Nội dung thi đấu.")
        
        df_disc = get_data('disciplines')
        df_cont = get_data('contents')
        df_reg = get_data('registrations')
        
        if df_disc.empty or df_reg.empty:
            st.warning("Chưa có đủ dữ liệu Môn thi hoặc VĐV đăng ký.")
        else:
            # Chọn Môn
            sel_disc_name = st.selectbox("1. Chọn Môn thi đấu:", df_disc['name'].tolist())
            
            # Chọn Nội dung (Lọc theo môn)
            sel_disc_id = str(df_disc[df_disc['name'] == sel_disc_name].iloc[0]['id'])
            df_cont['discipline_id'] = df_cont['discipline_id'].astype(str)
            valid_contents = df_cont[df_cont['discipline_id'] == sel_disc_id]['name'].tolist()
            # Thêm lựa chọn "Tất cả nội dung" hoặc "Chung"
            content_opts = ["-- Tất cả --"] + valid_contents + [f"{sel_disc_name} (Chung)"]
            
            sel_content = st.selectbox("2. Chọn Nội dung:", content_opts)
            
            if st.button("Tải danh sách", type="primary"):
                # Lọc danh sách đăng ký
                # Logic lọc: cột registered_contents chứa chuỗi "Môn: Nội dung"
                # Ví dụ: "Bóng đá: Nam", "Điền kinh: Chạy 100m"
                
                # Tạo từ khóa tìm kiếm
                if sel_content == "-- Tất cả --":
                    search_key = f"{sel_disc_name}:" # Tìm VĐV có đăng ký môn này
                else:
                    search_key = f"{sel_disc_name}: {sel_content}"
                
                # Lọc
                filtered_df = df_reg[df_reg['registered_contents'].astype(str).str.contains(search_key, na=False)]
                
                if not filtered_df.empty:
                    st.success(f"Tìm thấy {len(filtered_df)} VĐV.")
                    
                    # Chọn cột để xuất
                    export_cols = ['athleteName', 'gender', 'dob', 'unitName', 'registered_contents', 'studentId', 'ageGroup']
                    # Chỉ lấy cột tồn tại
                    final_cols = [c for c in export_cols if c in filtered_df.columns]
                    
                    csv = filtered_df[final_cols].to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 Tải danh sách {sel_disc_name}.csv",
                        data=csv,
                        file_name=f"danh_sach_{sel_disc_name}_{sel_content}.csv",
                        mime="text/csv"
                    )
                    st.dataframe(filtered_df[final_cols], use_container_width=True)
                else:
                    st.warning("Không tìm thấy VĐV nào đăng ký nội dung này.")

    # 7. ĐĂNG KÝ THI ĐẤU (UNIT)
    elif menu == "📝 Đăng ký thi đấu":
        unit = st.session_state.user_info
        st.header(f"📝 Đăng ký: {unit['name']}")
        
        edit_data = st.session_state.editing_athlete
        is_editing = edit_data is not None
        
        form_title = "✏️ Cập nhật thông tin VĐV" if is_editing else "➕ Đăng ký VĐV Mới"
        
        df_sys = get_data('systems')
        sys_opts = df_sys['name'].tolist() if not df_sys.empty else ["Mặc định"]
        df_disc = get_data('disciplines')
        df_cont = get_data('contents')
        
        # Load Lứa tuổi từ DB thay vì text input (MỚI)
        df_ages = get_data('age_groups')
        age_opts = df_ages['name'].tolist() if not df_ages.empty else ["Tự do"]

        if is_editing:
            st.markdown(f'<div class="edit-form">Đang chỉnh sửa VĐV: <b>{edit_data.get("athleteName")}</b></div>', unsafe_allow_html=True)

        with st.form("reg_form_v2"):
            st.subheader(form_title)
            
            def_name = edit_data.get('athleteName', '') if is_editing else ''
            def_gender_idx = 0 if is_editing and edit_data.get('gender') == 'Nam' else 1 if is_editing and edit_data.get('gender') == 'Nữ' else 0
            
            try:
                def_dob = datetime.strptime(edit_data.get('dob', '2008-01-01'), '%Y-%m-%d').date() if is_editing else date(2008, 1, 1)
            except: def_dob = date(2008, 1, 1)
            
            def_cccd = edit_data.get('cccd', '') if is_editing else ''
            def_sid = edit_data.get('studentId', '') if is_editing else ''
            
            # Xử lý default index cho Lứa tuổi
            def_age_idx = 0
            if is_editing and edit_data.get('ageGroup') in age_opts:
                def_age_idx = age_opts.index(edit_data.get('ageGroup'))
            
            def_sys_idx = 0
            if is_editing and edit_data.get('systemName') in sys_opts:
                def_sys_idx = sys_opts.index(edit_data.get('systemName'))

            c1, c2, c3, c4 = st.columns(4)
            a_name = c1.text_input("Họ tên (*)", value=def_name)
            a_gender = c2.selectbox("Giới tính", ["Nam", "Nữ"], index=def_gender_idx)
            a_dob = c3.date_input("Ngày sinh", value=def_dob, min_value=date(1990, 1, 1))
            a_cccd = c4.text_input("Số CCCD", value=def_cccd)
            
            c5, c6, c7 = st.columns(3)
            a_sid = c5.text_input("Mã học sinh/CCVC", value=def_sid)
            # Thay đổi Text Input thành Selectbox cho Lứa tuổi
            a_age_group = c6.selectbox("Lứa tuổi", age_opts, index=def_age_idx)
            a_system = c7.selectbox("Hệ thi đấu", sys_opts, index=def_sys_idx)
            
            st.divider()
            st.subheader("Nội dung Thi đấu")
            
            selected_contents_text = []
            
            current_contents = []
            if is_editing and edit_data.get('registered_contents'):
                current_contents = edit_data.get('registered_contents').split('; ')

            # KIỂM TRA QUY TẮC ĐĂNG KÝ (MỚI)
            max_disc_cfg = int(get_config('max_disciplines') or 100)
            max_cont_cfg = int(get_config('max_contents') or 100)
            
            count_disc_selected = 0
            error_msg = []

            if not df_disc.empty:
                for _, disc in df_disc.iterrows():
                    with st.expander(f"🏅 Môn {disc['name']}", expanded=is_editing):
                        is_exempt = str(disc.get('is_exempt', 'False')) == 'True'
                        
                        if not df_cont.empty:
                            df_cont['discipline_id'] = df_cont['discipline_id'].astype(str)
                            sub_contents = df_cont[df_cont['discipline_id'] == str(disc['id'])]
                            
                            if not sub_contents.empty:
                                available_opts = sub_contents['name'].tolist()
                                defaults = []
                                if is_editing:
                                    for opt in available_opts:
                                        if f"{disc['name']}: {opt}" in current_contents:
                                            defaults.append(opt)
                                
                                conts = st.multiselect(
                                    f"Chọn nội dung {disc['name']}:", 
                                    available_opts,
                                    default=defaults,
                                    key=f"m_sel_{disc['id']}"
                                )
                                if conts:
                                    if not is_exempt: count_disc_selected += 1
                                    # Kiểm tra quy tắc số nội dung/môn
                                    if not is_exempt and len(conts) > max_cont_cfg:
                                        error_msg.append(f"Môn {disc['name']} chỉ được chọn tối đa {max_cont_cfg} nội dung.")
                                    
                                    for c in conts: selected_contents_text.append(f"{disc['name']}: {c}")
                            else:
                                st.caption("Chưa có nội dung cụ thể.")
                                is_checked = False
                                if is_editing and f"{disc['name']} (Chung)" in current_contents:
                                    is_checked = True
                                    
                                if st.checkbox(f"Đăng ký {disc['name']} (Chung)", key=f"chk_{disc['id']}", value=is_checked):
                                    if not is_exempt: count_disc_selected += 1
                                    selected_contents_text.append(f"{disc['name']} (Chung)")
            
            # Kiểm tra quy tắc tổng số môn
            if count_disc_selected > max_disc_cfg:
                error_msg.append(f"VĐV chỉ được tham gia tối đa {max_disc_cfg} môn thi (không tính môn ngoại lệ).")

            st.info(f"Đang chọn: {', '.join(selected_contents_text)}")
            if error_msg:
                for err in error_msg: st.error(err)
            
            submit_label = "Cập nhật VĐV" if is_editing else "Lưu Đăng Ký"
            c_sub, c_cancel = st.columns([1, 1])
            
            # Chỉ cho phép lưu nếu không có lỗi quy tắc
            disabled_btn = bool(error_msg)
            
            submitted = c_sub.form_submit_button(submit_label, type="primary", disabled=disabled_btn)
            if is_editing:
                cancelled = c_cancel.form_submit_button("Hủy bỏ")
                if cancelled:
                    st.session_state.editing_athlete = None
                    st.rerun()

            if submitted:
                if a_name and selected_contents_text:
                    payload = {
                        'unitId': unit['id'],
                        'unitName': unit['name'],
                        'athleteName': a_name,
                        'gender': a_gender,
                        'dob': str(a_dob),
                        'cccd': a_cccd,
                        'studentId': a_sid,
                        'systemName': a_system,
                        'ageGroup': a_age_group,
                        'registered_contents': "; ".join(selected_contents_text)
                    }
                    
                    if is_editing:
                        if update_row_data('registrations', edit_data['id'], payload):
                            st.success("Đã cập nhật thành công!")
                            st.session_state.editing_athlete = None
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    else:
                        save_data('registrations', payload)
                        st.success("Đăng ký thành công!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Thiếu tên hoặc chưa chọn nội dung thi đấu.")

        st.subheader("Danh sách đã đăng ký")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            
            if not my_regs.empty:
                for idx, row in my_regs.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        s_name = row.get('athleteName', 'N/A')
                        s_gender = row.get('gender', '')
                        s_cont = row.get('registered_contents', '')
                        s_age = row.get('ageGroup', '')

                        c1.markdown(f"**{s_name}** ({s_gender}) - {s_age}")
                        c1.caption(f"ID: {row.get('studentId','')} - {row.get('dob','')}")
                        c2.write(f"🎯 {s_cont}")
                        
                        col_edit, col_del = c3.columns(2)
                        
                        if col_edit.button("✏️", key=f"ed_{row['id']}", help="Sửa thông tin VĐV này"):
                            st.session_state.editing_athlete = row.to_dict()
                            st.rerun()
                            
                        if col_del.button("🗑️", key=f"del_{row['id']}", help="Xóa VĐV này"):
                            delete_data('registrations', row['id'])
                            if st.session_state.editing_athlete and st.session_state.editing_athlete['id'] == row['id']:
                                st.session_state.editing_athlete = None
                            st.rerun()

    # 8. XUẤT DANH SÁCH (UNIT)
    elif menu == "📊 Xuất danh sách":
        unit = st.session_state.user_info
        st.title("📊 Xuất dữ liệu")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            if not my_regs.empty:
                cols_order = ['athleteName', 'gender', 'dob', 'studentId', 'cccd', 'systemName', 'ageGroup', 'registered_contents', 'rank']
                final_cols = [c for c in cols_order if c in my_regs.columns]
                st.dataframe(my_regs[final_cols], use_container_width=True)
                csv = my_regs[final_cols].to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 Tải CSV", data=csv, file_name=f"ds_{unit['name']}.csv", mime="text/csv")
            else: st.info("Chưa có dữ liệu.")

if __name__ == "__main__":
    main()

