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
    .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .badge-success { background-color: #d1fae5; color: #065f46; }
    .badge-warning { background-color: #fef3c7; color: #92400e; }
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

# --- HÀM XỬ LÝ DỮ LIỆU ---
def get_worksheet(sheet_name):
    try:
        SPREADSHEET_NAME = "QUAN_LY_GIAI_DAU_PBC" 
        sh = client.open(SPREADSHEET_NAME)
        try:
            worksheet = sh.worksheet(sheet_name)
        except:
            # Tự động tạo sheet nếu chưa có và thêm header chuẩn
            worksheet = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            headers = {
                'config': ['key', 'value'],
                'systems': ['id', 'name', 'createdAt'],
                'disciplines': ['id', 'code', 'name', 'is_exempt', 'createdAt'], # is_exempt: môn không áp dụng quy tắc
                'contents': ['id', 'discipline_id', 'name', 'gender', 'createdAt'], # Nội dung thi đấu (hạng cân, tuổi...)
                'units': ['id', 'name', 'manager', 'registrationCode', 'createdAt'],
                'registrations': ['id', 'unitId', 'unitName', 'athleteName', 'gender', 'dob', 'cccd', 'studentId', 'systemName', 'ageGroup', 'registered_contents', 'rank', 'createdAt']
            }
            if sheet_name in headers:
                worksheet.append_row(headers[sheet_name])
        return worksheet
    except Exception as e:
        st.error(f"⚠️ Không tìm thấy file Google Sheet '{SPREADSHEET_NAME}'.")
        st.stop()

def get_data(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
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

def update_cell(sheet_name, doc_id, col_name, new_value):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(doc_id))
        if cell:
            # Tìm index của cột
            headers = ws.row_values(1)
            try:
                col_idx = headers.index(col_name) + 1
                ws.update_cell(cell.row, col_idx, str(new_value))
                return True
            except:
                st.error(f"Không tìm thấy cột {col_name}")
        return False
    except Exception as e:
        st.error(f"Lỗi cập nhật: {e}")
        return False

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

# --- HÀM CẤU HÌNH (CONFIG) ---
def get_config(key):
    df = get_data('config')
    if not df.empty:
        row = df[df['key'] == key]
        if not row.empty:
            return row.iloc[0]['value']
    return None

def set_config(key, value):
    ws = get_worksheet('config')
    cell = ws.find(key)
    if cell:
        ws.update_cell(cell.row, 2, str(value))
    else:
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

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏅 Điều Khiển Giải Đấu")
        
        # ĐĂNG NHẬP
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
            if st.button("Đăng xuất"):
                st.session_state.role = 'guest'
                st.session_state.user_info = None
                st.rerun()
        
        st.markdown("---")
        
        # MENU
        if st.session_state.role == 'admin':
            menu = st.radio("Chức năng:", ["🏠 Tổng quan", "⚙️ Cấu hình Giải đấu", "🏅 Môn & Nội dung thi", "🏢 Quản lý Đơn vị", "🏆 Cập nhật Kết quả"])
        elif st.session_state.role == 'unit':
            menu = st.radio("Chức năng:", ["🏠 Tổng quan", "📝 Đăng ký thi đấu", "📊 Xuất danh sách"])
        else:
            menu = "🏠 Tổng quan"

    # --- LOGIC CÁC TRANG ---
    
    # 1. TỔNG QUAN
    if menu == "🏠 Tổng quan":
        st.title("🏆 Thông Tin Giải Đấu")
        
        # Lấy thông tin cấu hình
        deadline_str = get_config('deadline')
        tournament_name = get_config('tournament_name') or "Giải Thể Thao Học Đường"
        
        st.header(tournament_name)
        if deadline_str:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            days_left = (deadline - date.today()).days
            if days_left >= 0:
                st.info(f"📅 Hạn đăng ký: **{deadline_str}** (Còn {days_left} ngày)")
            else:
                st.error(f"🔴 Đã hết hạn đăng ký từ ngày {deadline_str}")
        
        df_reg = get_data('registrations')
        c1, c2, c3 = st.columns(3)
        c1.metric("Vận động viên", len(df_reg))
        c2.metric("Đơn vị tham gia", len(get_data('units')))
        c3.metric("Môn thi đấu", len(get_data('disciplines')))

        # Bảng xếp hạng sơ bộ (theo số lượng huy chương - demo)
        if not df_reg.empty and 'rank' in df_reg.columns:
            st.subheader("Bảng vàng thành tích")
            winners = df_reg[df_reg['rank'].isin(['Nhất', 'Nhì', 'Ba'])]
            if not winners.empty:
                st.dataframe(winners[['athleteName', 'unitName', 'registered_contents', 'rank']], use_container_width=True)
            else:
                st.caption("Chưa có kết quả thi đấu.")

    # 2. CẤU HÌNH (ADMIN)
    elif menu == "⚙️ Cấu hình Giải đấu":
        st.header("⚙️ Thiết lập Chung")
        
        with st.form("config_form"):
            t_name = st.text_input("Tên giải đấu", value=get_config('tournament_name') or "")
            deadline = st.date_input("Hạn chót đăng ký", value=datetime.today())
            
            st.subheader("Hệ thống tổ chức (Hệ thi đấu)")
            st.caption("Ví dụ: Hệ Phong trào, Hệ Nâng cao, Hệ Chuyên nghiệp...")
            
            # Quản lý Hệ thi đấu
            new_sys = st.text_input("Thêm Hệ thi đấu mới (Nhập tên):")
            
            submit = st.form_submit_button("Lưu Cấu hình")
            
            if submit:
                set_config('tournament_name', t_name)
                set_config('deadline', str(deadline))
                if new_sys:
                    save_data('systems', {'name': new_sys})
                st.success("Đã lưu cấu hình!")
                st.cache_data.clear()
                st.rerun()

        st.divider()
        st.subheader("Danh sách Hệ thi đấu")
        df_sys = get_data('systems')
        if not df_sys.empty:
            for i, row in df_sys.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.write(f"• {row['name']}")
                if c2.button("Xóa", key=f"del_sys_{row['id']}"):
                    delete_data('systems', row['id'])
                    st.rerun()

    # 3. MÔN & NỘI DUNG (ADMIN) - QUAN TRỌNG
    elif menu == "🏅 Môn & Nội dung thi":
        st.header("🏅 Quản lý Môn & Nội dung")
        st.info("Ví dụ: Môn 'Điền kinh' có nội dung 'Chạy 100m Nam', 'Chạy 100m Nữ'...")
        
        c1, c2 = st.columns([1, 2])
        
        with c1: # Cột trái: Thêm môn
            st.subheader("1. Thêm Môn thi")
            with st.form("add_disc"):
                d_code = st.text_input("Mã môn (VD: BD)").upper()
                d_name = st.text_input("Tên môn (VD: Bóng đá)")
                d_exempt = st.checkbox("Môn này KHÔNG giới hạn số lượng ĐK?", help="Check nếu môn này là ngoại lệ (VD: Kéo co)")
                if st.form_submit_button("Thêm Môn"):
                    if d_code and d_name:
                        save_data('disciplines', {'code': d_code, 'name': d_name, 'is_exempt': 'True' if d_exempt else 'False'})
                        st.success(f"Đã thêm {d_name}")
                        st.cache_data.clear()
                        st.rerun()
        
        with c2: # Cột phải: Thêm nội dung cho môn
            st.subheader("2. Thêm Nội dung thi đấu")
            df_disc = get_data('disciplines')
            
            if not df_disc.empty:
                # Chọn môn để thêm nội dung
                selected_disc_name = st.selectbox("Chọn Môn thi đấu:", df_disc['name'].tolist())
                selected_disc = df_disc[df_disc['name'] == selected_disc_name].iloc[0]
                
                with st.form("add_content"):
                    c_name = st.text_input(f"Tên nội dung thuộc môn {selected_disc_name} (VD: Hạng cân < 50kg)")
                    c_gender = st.selectbox("Dành cho:", ["Nam", "Nữ", "Nam & Nữ"])
                    if st.form_submit_button("Thêm Nội dung"):
                        if c_name:
                            save_data('contents', {
                                'discipline_id': selected_disc['id'],
                                'name': c_name,
                                'gender': c_gender
                            })
                            st.success("Đã thêm nội dung!")
                            st.cache_data.clear()
                            st.rerun()
                
                # Hiển thị danh sách nội dung hiện có
                st.write(f"**Danh sách nội dung của {selected_disc_name}:**")
                df_contents = get_data('contents')
                if not df_contents.empty:
                    # Lọc nội dung theo môn
                    # Lưu ý: cần convert về string để so sánh an toàn
                    df_contents['discipline_id'] = df_contents['discipline_id'].astype(str)
                    my_contents = df_contents[df_contents['discipline_id'] == str(selected_disc['id'])]
                    
                    if not my_contents.empty:
                        for _, row in my_contents.iterrows():
                            cc1, cc2 = st.columns([4, 1])
                            cc1.text(f"- {row['name']} ({row['gender']})")
                            if cc2.button("Xóa", key=f"del_c_{row['id']}"):
                                delete_data('contents', row['id'])
                                st.rerun()
                    else:
                        st.caption("Chưa có nội dung nào.")
            else:
                st.warning("Vui lòng tạo môn thi đấu trước.")

    # 4. QUẢN LÝ ĐƠN VỊ (ADMIN)
    elif menu == "🏢 Quản lý Đơn vị":
        st.header("🏢 Danh sách Đơn vị")
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
        
        df = get_data('units')
        if not df.empty:
            st.dataframe(df[['name', 'manager', 'registrationCode']], use_container_width=True)

    # 5. CẬP NHẬT KẾT QUẢ (ADMIN)
    elif menu == "🏆 Cập nhật Kết quả":
        st.header("🏆 Cập nhật Thành tích")
        
        df_reg = get_data('registrations')
        if df_reg.empty:
            st.info("Chưa có dữ liệu đăng ký.")
        else:
            # Filter
            col_search, col_rank = st.columns(2)
            search_txt = col_search.text_input("Tìm tên VĐV/Đơn vị:")
            
            # View data
            view_df = df_reg.copy()
            if search_txt:
                view_df = view_df[view_df.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)]
            
            # Form cập nhật
            st.write("---")
            st.subheader("Cập nhật giải thưởng")
            
            # Chọn VĐV để sửa
            athlete_opts = view_df.apply(lambda x: f"{x['athleteName']} ({x['unitName']}) - {x['registered_contents']}", axis=1).tolist()
            selected_str = st.selectbox("Chọn VĐV để cập nhật:", athlete_opts)
            
            if selected_str:
                # Tìm ID của VĐV được chọn (Logic hơi thô sơ dựa trên index, thực tế nên dùng ID ẩn)
                # Để chính xác, ta map lại user choice với ID
                selected_idx = athlete_opts.index(selected_str)
                selected_id = view_df.iloc[selected_idx]['id']
                
                new_rank = st.selectbox("Thành tích:", ["", "Nhất", "Nhì", "Ba", "Khuyến Khích", "Hoàn thành"])
                
                if st.button("Lưu Kết quả"):
                    if update_cell('registrations', selected_id, 'rank', new_rank):
                        st.success(f"Đã cập nhật thành tích cho {selected_str}")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

    # 6. ĐĂNG KÝ THI ĐẤU (UNIT)
    elif menu == "📝 Đăng ký thi đấu":
        unit = st.session_state.user_info
        st.header(f"📝 Đăng ký: {unit['name']}")
        
        # KIỂM TRA HẠN CHÓT
        deadline_str = get_config('deadline')
        if deadline_str:
            deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if date.today() > deadline_date:
                st.error(f"⛔ Đã hết hạn đăng ký ({deadline_str}). Bạn chỉ có thể xem danh sách.")
                st.stop()
        
        with st.form("reg_form_v2"):
            st.subheader("Thông tin Vận động viên")
            c1, c2, c3, c4 = st.columns(4)
            a_name = c1.text_input("Họ tên (*)")
            a_gender = c2.selectbox("Giới tính", ["Nam", "Nữ"])
            a_dob = c3.date_input("Ngày sinh", value=date(2008, 1, 1), min_value=date(1990, 1, 1))
            a_cccd = c4.text_input("Số CCCD")
            
            c5, c6, c7 = st.columns(3)
            a_sid = c5.text_input("Mã học sinh/CCVC")
            a_age_group = c6.text_input("Lứa tuổi (VD: 16-18)", value="Tự do")
            
            # Chọn Hệ thi đấu
            df_sys = get_data('systems')
            sys_opts = df_sys['name'].tolist() if not df_sys.empty else ["Mặc định"]
            a_system = c7.selectbox("Hệ thi đấu", sys_opts)
            
            st.divider()
            st.subheader("Nội dung Thi đấu")
            
            # Chọn Môn trước -> Sau đó hiện Nội dung của môn đó
            df_disc = get_data('disciplines')
            df_cont = get_data('contents')
            
            selected_contents_text = []
            
            if not df_disc.empty:
                # Hiển thị môn dạng Expanders để chọn nội dung bên trong
                for _, disc in df_disc.iterrows():
                    with st.expander(f"🏅 Môn {disc['name']}", expanded=False):
                        # Lọc nội dung của môn này
                        if not df_cont.empty:
                            df_cont['discipline_id'] = df_cont['discipline_id'].astype(str)
                            sub_contents = df_cont[df_cont['discipline_id'] == str(disc['id'])]
                            
                            if not sub_contents.empty:
                                # Multiselect nội dung
                                conts = st.multiselect(
                                    f"Chọn nội dung {disc['name']}:", 
                                    sub_contents['name'].tolist(),
                                    key=f"m_sel_{disc['id']}"
                                )
                                if conts:
                                    # Format: "Bóng đá: Nam"
                                    for c in conts:
                                        selected_contents_text.append(f"{disc['name']}: {c}")
                            else:
                                st.caption("Chưa có nội dung cụ thể (Admin chưa cấu hình).")
                                # Fallback nếu chưa cấu hình nội dung: cho phép chọn môn chung
                                if st.checkbox(f"Đăng ký {disc['name']} (Chung)", key=f"chk_{disc['id']}"):
                                    selected_contents_text.append(f"{disc['name']} (Chung)")
            
            st.info(f"Đang chọn: {', '.join(selected_contents_text)}")
            
            submit = st.form_submit_button("Lưu Đăng Ký", type="primary")
            
            if submit:
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
                    save_data('registrations', payload)
                    st.success("Đăng ký thành công!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Thiếu tên hoặc chưa chọn nội dung thi đấu.")

        # Xem danh sách
        st.subheader("Danh sách đã đăng ký")
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            
            if not my_regs.empty:
                for idx, row in my_regs.iterrows():
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.markdown(f"**{row['athleteName']}** - {row['gender']} ({row['dob']})")
                        c1.caption(f"ID: {row['studentId']} | CCCD: {row['cccd']}")
                        c2.write(f"🎯 {row['registered_contents']}")
                        c2.caption(f"Hệ: {row['systemName']}")
                        
                        if c3.button("Xóa", key=f"del_reg_{row['id']}"):
                            delete_data('registrations', row['id'])
                            st.rerun()
                        st.divider()

    # 7. XUẤT DANH SÁCH (UNIT)
    elif menu == "📊 Xuất danh sách":
        unit = st.session_state.user_info
        st.title("📊 Xuất dữ liệu")
        
        df_reg = get_data('registrations')
        if not df_reg.empty:
            df_reg['unitId'] = df_reg['unitId'].astype(str)
            my_regs = df_reg[df_reg['unitId'] == str(unit['id'])]
            
            if not my_regs.empty:
                st.dataframe(my_regs)
                
                # Convert to CSV
                csv = my_regs.to_csv(index=False).encode('utf-8-sig')
                
                st.download_button(
                    label="📥 Tải danh sách (CSV)",
                    data=csv,
                    file_name=f"danh_sach_thi_dau_{unit['name']}.csv",
                    mime="text/csv",
                )
            else:
                st.info("Chưa có dữ liệu để xuất.")

if __name__ == "__main__":
    main()
