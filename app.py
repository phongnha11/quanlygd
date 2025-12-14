import streamlit as st
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
    expected_headers = {
        'config': ['key', 'value'],
        'systems': ['id', 'name', 'createdAt'],
        'disciplines': ['id', 'code', 'name', 'is_exempt', 'createdAt'],
        'contents': ['id', 'discipline_id', 'name', 'gender', 'createdAt'],
        'units': ['id', 'name', 'manager', 'registrationCode', 'createdAt'],
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
            headers = {
                'config': ['key', 'value'],
                'systems': ['id', 'name', 'createdAt'],
                'disciplines': ['id', 'code', 'name', 'is_exempt', 'createdAt'],
                'contents': ['id', 'discipline_id', 'name', 'gender', 'createdAt'],
                'units': ['id', 'name', 'manager', 'registrationCode', 'createdAt'],
                'registrations': ['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'cccd', 'studentId', 'systemName', 'ageGroup', 'registered_contents', 'rank', 'createdAt']
            }
            if sheet_name in headers:
                worksheet.append_row(headers[sheet_name])
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
            df = ensure_columns(df, ['id', 'name', 'manager', 'registrationCode', 'createdAt'])
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
            
            # --- FIX LỖI DUPLICATE ELEMENT ID ---
            # Quan trọng: Thêm key="logout_btn" để tránh lỗi khi render lại
            if st.button("Đăng xuất", key="logout_btn"):
                st.session_state.role = 'guest'
                st.session_state.user_info = None
                st.session_state.editing_athlete = None
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.role == 'admin':
            menu = st.radio("Chức năng:", ["🏠 Tổng quan", "⚙️ Cấu hình Giải đấu", "🏅 Môn & Nội dung thi", "🏢 Quản lý Đơn vị", "🏆 Cập nhật Kết quả"])
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
            st.subheader("Bảng vàng thành tích")
            winners = df_reg[df_reg['rank'].isin(['Nhất', 'Nhì', 'Ba'])]
            if not winners.empty:
                cols = ['athleteName', 'unitName', 'rank']
                if 'registered_contents' in winners.columns: cols.insert(2, 'registered_contents')
                st.dataframe(winners[cols], use_container_width=True)

    # 2. CẤU HÌNH (ADMIN)
    elif menu == "⚙️ Cấu hình Giải đấu":
        st.header("⚙️ Thiết lập Chung")
        with st.form("config_form"):
            t_name = st.text_input("Tên giải đấu", value=get_config('tournament_name') or "")
            deadline = st.date_input("Hạn chót đăng ký", value=datetime.today())
            st.subheader("Hệ thống tổ chức (Hệ thi đấu)")
            new_sys = st.text_input("Thêm Hệ thi đấu mới (Nhập tên):")
            if st.form_submit_button("Lưu Cấu hình"):
                set_config('tournament_name', t_name)
                set_config('deadline', str(deadline))
                if new_sys: save_data('systems', {'name': new_sys})
                st.success("Đã lưu!")
                st.cache_data.clear()
                st.rerun()
        
        st.divider()
        st.subheader("Danh sách Hệ thi đấu")
        df_sys = get_data('systems')
        if not df_sys.empty:
            for i, row in df_sys.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.write(f"• {row['name']}")
                if c2.button("Xóa", key=f"ds_{row['id']}"):
                    delete_data('systems', row['id'])
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
                d_exempt = st.checkbox("Không giới hạn số lượng ĐK?")
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
                    
                    # Thêm key để tránh lỗi DuplicateElementId
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
        df_reg = get_data('registrations')
        if df_reg.empty:
            st.info("Chưa có dữ liệu.")
        else:
            col_search, col_rank = st.columns(2)
            search_txt = col_search.text_input("Tìm tên VĐV/Đơn vị:")
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
                new_rank = st.selectbox("Thành tích:", ["", "Nhất", "Nhì", "Ba", "Khuyến Khích", "Hoàn thành"])
                if st.button("Lưu Kết quả"):
                    if update_cell('registrations', selected_id, 'rank', new_rank):
                        st.success("Đã cập nhật!")
                        st.cache_data.clear()
                        st.rerun()

    # 6. ĐĂNG KÝ THI ĐẤU (UNIT)
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
            def_age = edit_data.get('ageGroup', 'Tự do') if is_editing else 'Tự do'
            
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
            a_age_group = c6.text_input("Lứa tuổi", value=def_age)
            a_system = c7.selectbox("Hệ thi đấu", sys_opts, index=def_sys_idx)
            
            st.divider()
            st.subheader("Nội dung Thi đấu")
            
            selected_contents_text = []
            
            current_contents = []
            if is_editing and edit_data.get('registered_contents'):
                current_contents = edit_data.get('registered_contents').split('; ')

            if not df_disc.empty:
                for _, disc in df_disc.iterrows():
                    with st.expander(f"🏅 Môn {disc['name']}", expanded=is_editing):
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
                                    for c in conts: selected_contents_text.append(f"{disc['name']}: {c}")
                            else:
                                st.caption("Chưa có nội dung cụ thể.")
                                is_checked = False
                                if is_editing and f"{disc['name']} (Chung)" in current_contents:
                                    is_checked = True
                                    
                                if st.checkbox(f"Đăng ký {disc['name']} (Chung)", key=f"chk_{disc['id']}", value=is_checked):
                                    selected_contents_text.append(f"{disc['name']} (Chung)")
            
            st.info(f"Đang chọn: {', '.join(selected_contents_text)}")
            
            submit_label = "Cập nhật VĐV" if is_editing else "Lưu Đăng Ký"
            c_sub, c_cancel = st.columns([1, 1])
            
            submitted = c_sub.form_submit_button(submit_label, type="primary")
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

                        c1.markdown(f"**{s_name}** ({s_gender})")
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

    # 7. XUẤT DANH SÁCH (UNIT)
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
