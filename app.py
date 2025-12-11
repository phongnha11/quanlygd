import streamlit as st
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & KẾT NỐI FIREBASE
# ==============================================================================
st.set_page_config(
    page_title="THPT Phan Bội Châu - Quản Lý Giải Đấu",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS tùy chỉnh để giao diện đẹp hơn ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #2c3e50; }
    .success-msg { color: #155724; background-color: #d4edda; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- Hàm kết nối Firestore (Sử dụng Secrets của Streamlit để bảo mật) ---
@st.cache_resource
def get_db():
    # Kiểm tra xem app đã kết nối Firebase chưa để tránh lỗi init lại
    if not firebase_admin._apps:
        # Lấy thông tin key từ st.secrets (Cấu hình trên Streamlit Cloud)
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Thử kết nối, nếu chưa cấu hình thì hiện hướng dẫn
try:
    db = get_db()
    APP_ID = "thpt-pbc-tournament-2025" # Định danh dự án
except Exception as e:
    st.error("⚠️ Chưa kết nối được Database. Vui lòng cấu hình Secrets trên Streamlit Cloud.")
    st.info(f"Chi tiết lỗi: {e}")
    st.stop()

# ==============================================================================
# 2. CÁC HÀM XỬ LÝ DỮ LIỆU (BACKEND)
# ==============================================================================

def get_collection_data(collection_name):
    """Lấy toàn bộ dữ liệu từ 1 collection về dạng DataFrame"""
    docs = db.collection(f'artifacts/{APP_ID}/public/data/{collection_name}').stream()
    data = [{'id': doc.id, **doc.to_dict()} for doc in docs]
    return pd.DataFrame(data)

def add_document(collection_name, data):
    """Thêm mới dữ liệu"""
    data['createdAt'] = datetime.now().isoformat()
    db.collection(f'artifacts/{APP_ID}/public/data/{collection_name}').add(data)

def delete_document(collection_name, doc_id):
    """Xóa dữ liệu"""
    db.collection(f'artifacts/{APP_ID}/public/data/{collection_name}').document(doc_id).delete()

# ==============================================================================
# 3. GIAO DIỆN CHÍNH (FRONTEND)
# ==============================================================================

def main():
    # --- Sidebar Menu ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2855/2855234.png", width=100)
        st.title("Menu Điều Khiển")
        menu = st.radio("Chọn chức năng:", 
            ["🏠 Tổng quan", "⚙️ Thiết lập (Admin)", "🏢 Quản lý Đơn vị", "📝 Cổng Đăng Ký", "📊 Xem Kết quả"]
        )
        st.markdown("---")
        st.caption("© 2025 THPT Phan Bội Châu")

    # --- 3.1 TRANG TỔNG QUAN ---
    if menu == "🏠 Tổng quan":
        st.title("🏆 Hệ Thống Quản Lý Giải Đấu")
        st.markdown("Chào mừng đến với hệ thống quản lý thể thao trực tuyến.")
        
        # Lấy số liệu thống kê
        try:
            df_mon = get_collection_data('disciplines')
            df_dv = get_collection_data('units')
            df_vdv = get_collection_data('registrations')
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Môn thi đấu", f"{len(df_mon)}")
            col2.metric("Đơn vị tham gia", f"{len(df_dv)}")
            col3.metric("Vận động viên", f"{len(df_vdv)}")
        except:
            st.warning("Đang tải dữ liệu hoặc chưa có dữ liệu...")

    # --- 3.2 TRANG THIẾT LẬP (ADMIN) ---
    elif menu == "⚙️ Thiết lập (Admin)":
        st.header("⚙️ Thiết lập Giải đấu")
        
        tab1, tab2 = st.tabs(["Môn thi đấu", "Lứa tuổi"])
        
        with tab1:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Thêm Môn mới")
                with st.form("add_discipline"):
                    code = st.text_input("Mã môn (VD: BD)").upper()
                    name = st.text_input("Tên môn (VD: Bóng đá)")
                    submitted = st.form_submit_button("Thêm môn")
                    if submitted and code and name:
                        add_document('disciplines', {'code': code, 'name': name})
                        st.success(f"Đã thêm môn {name}")
                        st.rerun()
            
            with c2:
                st.subheader("Danh sách Môn thi")
                df = get_collection_data('disciplines')
                if not df.empty:
                    st.dataframe(df[['code', 'name']], use_container_width=True)
                    # Xóa môn (Demo UI chọn xóa)
                    del_opt = st.selectbox("Chọn môn để xóa:", df['name'].tolist(), index=None, placeholder="Chọn môn...")
                    if del_opt:
                        id_to_del = df[df['name'] == del_opt].iloc[0]['id']
                        if st.button("Xác nhận xóa môn này"):
                            delete_document('disciplines', id_to_del)
                            st.rerun()

        with tab2:
            st.info("Chức năng tương tự cho Lứa tuổi (Đang phát triển thêm...)")

    # --- 3.3 QUẢN LÝ ĐƠN VỊ ---
    elif menu == "🏢 Quản lý Đơn vị":
        st.header("🏢 Quản lý Đơn vị & Cấp Mã")
        
        with st.expander("➕ Thêm Đơn vị / Lớp mới", expanded=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            name = col1.text_input("Tên Đơn vị (VD: 10A1)")
            manager = col2.text_input("Giáo viên phụ trách")
            if col3.button("Tạo Đơn vị", type="primary"):
                if name and manager:
                    import random, string
                    # Tạo mã random 6 ký tự
                    reg_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    add_document('units', {'name': name, 'manager': manager, 'registrationCode': reg_code})
                    st.success(f"Tạo thành công! Mã đăng ký: {reg_code}")
                    st.rerun()
                else:
                    st.error("Vui lòng nhập đủ thông tin.")

        st.subheader("Danh sách Đơn vị & Mã Đăng nhập")
        df = get_collection_data('units')
        if not df.empty:
            # Hiển thị bảng đẹp hơn
            st.dataframe(
                df[['name', 'manager', 'registrationCode']], 
                column_config={
                    "name": "Tên Đơn vị",
                    "manager": "Người phụ trách",
                    "registrationCode": "MÃ ĐĂNG KÝ (Login)"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Chưa có đơn vị nào.")

    # --- 3.4 CỔNG ĐĂNG KÝ ---
    elif menu == "📝 Cổng Đăng Ký":
        st.header("📝 Cổng Đăng Ký Vận Động Viên")
        
        # State Management cho Login
        if 'unit_logged_in' not in st.session_state:
            st.session_state.unit_logged_in = None

        # Giao diện Login
        if not st.session_state.unit_logged_in:
            with st.form("login_form"):
                st.write("Vui lòng nhập Mã Đăng Ký được BTC cấp:")
                input_code = st.text_input("Mã Đăng Ký (6 ký tự)", max_chars=6).upper()
                submit_login = st.form_submit_button("Đăng Nhập")
                
                if submit_login:
                    df_units = get_collection_data('units')
                    # Tìm đơn vị có mã khớp
                    unit = df_units[df_units['registrationCode'] == input_code]
                    if not unit.empty:
                        st.session_state.unit_logged_in = unit.iloc[0].to_dict()
                        st.success(f"Xin chào {unit.iloc[0]['name']}!")
                        st.rerun()
                    else:
                        st.error("Mã đăng ký không chính xác!")
        
        # Giao diện Đăng ký (Sau khi login)
        else:
            unit = st.session_state.unit_logged_in
            st.success(f"Đang làm việc: **{unit['name']}** (GV: {unit['manager']})")
            if st.button("Đăng xuất"):
                st.session_state.unit_logged_in = None
                st.rerun()
            
            st.markdown("---")
            
            # Load dữ liệu cần thiết
            df_disciplines = get_collection_data('disciplines')
            
            with st.form("register_athlete"):
                st.subheader("Đăng ký VĐV Mới")
                c1, c2, c3 = st.columns(3)
                ath_name = c1.text_input("Họ và tên VĐV")
                ath_gender = c2.selectbox("Giới tính", ["Nam", "Nữ"])
                ath_dob = c3.date_input("Ngày sinh", min_value=datetime(2000, 1, 1))
                
                # Chọn môn thi (Multiselect)
                options = df_disciplines['name'].tolist() if not df_disciplines.empty else []
                selected_disciplines = st.multiselect("Chọn môn thi đấu:", options)
                
                submitted = st.form_submit_button("Lưu Đăng Ký", type="primary")
                
                if submitted:
                    if ath_name and selected_disciplines:
                        payload = {
                            'unitId': unit['id'],
                            'unitName': unit['name'],
                            'athleteName': ath_name,
                            'gender': ath_gender,
                            'dob': ath_dob.isoformat(),
                            'disciplines': selected_disciplines
                        }
                        add_document('registrations', payload)
                        st.success("Đã đăng ký thành công!")
                        st.rerun()
                    else:
                        st.error("Thiếu tên hoặc chưa chọn môn thi.")

            # Xem danh sách đã đăng ký
            st.subheader(f"Danh sách VĐV của {unit['name']}")
            df_reg = get_collection_data('registrations')
            if not df_reg.empty:
                # Lọc ra VĐV của đơn vị này
                my_regs = df_reg[df_reg['unitId'] == unit['id']]
                if not my_regs.empty:
                    st.dataframe(my_regs[['athleteName', 'gender', 'disciplines']], use_container_width=True)
                else:
                    st.info("Chưa có VĐV nào được đăng ký.")

    # --- 3.5 XEM KẾT QUẢ ---
    elif menu == "📊 Xem Kết quả":
        st.header("📊 Danh sách Đăng ký Toàn trường")
        df_reg = get_collection_data('registrations')
        if not df_reg.empty:
            st.dataframe(df_reg[['unitName', 'athleteName', 'gender', 'disciplines']], use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")

if __name__ == "__main__":
    main()