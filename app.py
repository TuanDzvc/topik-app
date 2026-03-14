import streamlit as st
import edge_tts
import asyncio
import os
import json
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Học TOPIK Cùng AI - By Tuân", layout="wide")

# --- TỐI ƯU KẾT NỐI GOOGLE SHEETS (SIÊU TỐC & BẢO MẬT ĐÁM MÂY) ---
@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds", 
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file", 
        "https://www.googleapis.com/auth/drive"
    ]
    # Lấy chìa khóa từ Két sắt bí mật của Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_users = client.open("Database_Topik").worksheet("Users")
    sheet_progress = client.open("Database_Topik").worksheet("Progress")
    return sheet_users, sheet_progress
try:
    sheet_users, sheet_progress = init_gspread()
except Exception as e:
    st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
    st.stop()

# Hàm băm mật khẩu
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- CÁC HÀM XỬ LÝ DATABASE ---
def load_users_db():
    rows = sheet_users.get_all_values()
    db = {}
    for row in rows[1:]:
        if len(row) >= 2:
            db[row[0]] = row[1]
    return db

def save_new_user(username, password_hashed):
    sheet_users.append_row([username, password_hashed])

def load_data(username):
    rows = sheet_progress.get_all_values()
    for row in rows[1:]:
        if len(row) >= 2 and row[0] == username:
            return json.loads(row[1])
    return {}

def save_data(username, data):
    rows = sheet_progress.get_all_values()
    data_str = json.dumps(data, ensure_ascii=False)
    found = False
    for i, row in enumerate(rows):
        if i > 0 and len(row) >= 1 and row[0] == username:
            sheet_progress.update_cell(i + 1, 2, data_str)
            found = True
            break
    if not found:
        sheet_progress.append_row([username, data_str])

# --- XỬ LÝ ĐĂNG NHẬP / ĐĂNG KÝ (DÙNG FORM VÀ HIỆU ỨNG CHỜ) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""

if not st.session_state.authenticated:
    st.title("🔐 Hệ thống Đăng nhập Lớp Học TOPIK")
    
    tab_login, tab_register = st.tabs(["Đăng Nhập 🔑", "Đăng Ký Tài Khoản Mới 📝"])
    
    with tab_login:
        st.subheader("Chào mừng trở lại!")
        with st.form("login_form"):
            login_user = st.text_input("Tài khoản:")
            login_pass = st.text_input("Mật khẩu:", type="password")
            submit_login = st.form_submit_button("Vào Học 🚀")
            
            if submit_login:
                # Hiệu ứng chờ xuất hiện khi bắt đầu gọi Google
                with st.spinner('Đang kết nối máy chủ Google... ⏳'):
                    users_db = load_users_db()
                    if login_user in users_db and users_db[login_user] == hash_password(login_pass):
                        st.session_state.authenticated = True
                        st.session_state.username = login_user
                        st.rerun()
                    else:
                        st.error("❌ Sai tài khoản hoặc mật khẩu!")

    with tab_register:
        st.subheader("Tạo tài khoản học mới")
        with st.form("register_form"):
            reg_user = st.text_input("Tên tài khoản (viết liền không dấu):")
            reg_pass = st.text_input("Mật khẩu:", type="password")
            reg_pass_confirm = st.text_input("Nhập lại mật khẩu:", type="password")
            submit_reg = st.form_submit_button("Tạo Tài Khoản ✨")
            
            if submit_reg:
                # Hiệu ứng chờ xuất hiện khi bắt đầu ghi lên Google
                with st.spinner('Đang tạo tài khoản trên Database... ⏳'):
                    users_db = load_users_db()
                    if not reg_user or not reg_pass:
                        st.warning("⚠️ Vui lòng điền đầy đủ thông tin!")
                    elif reg_user in users_db:
                        st.error("❌ Tên tài khoản này đã có người sử dụng!")
                    elif reg_pass != reg_pass_confirm:
                        st.error("❌ Mật khẩu nhập lại không khớp!")
                    else:
                        save_new_user(reg_user, hash_password(reg_pass))
                        st.success("🎉 Đăng ký thành công! Chuyển qua tab Đăng Nhập để vào học ngay.")
                
    st.stop()

# ==========================================
# BẮT ĐẦU VẼ GIAO DIỆN HỌC
# ==========================================
user_data = load_data(st.session_state.username)

col_header1, col_header2 = st.columns([8, 2])
with col_header1:
    st.title("Bảng Từ Vựng TOPIK - Giọng AI Chuẩn Hàn🚀- By Tuân")
with col_header2:
    st.success(f"👤 Đang học: **{st.session_state.username}**")
    if st.button("Đăng xuất 👋"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

st.markdown("""
    <style>
    a.header-anchor { display: none !important; }
    button[data-baseweb="tab"] { font-size: 20px !important; padding: 10px 20px !important; }
    button[data-baseweb="tab"][aria-selected="true"] {
        font-size: 28px !important; font-weight: 900 !important;
        color: #FFD700 !important; background-color: #2b2b2b !important;
        border-bottom: 4px solid #FFD700 !important;
    }
    .center-text { text-align: center; display: flex; justify-content: center; align-items: center; margin-top: 18px; font-size: 16px; }
    .korean-text { color: #FFD700; font-size: 28px; font-weight: bold; text-align: center; display: flex; justify-content: center; align-items: center; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def get_audio_bytes(text, voice):
    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        return bytes(audio_data)
    return asyncio.run(_generate())

voice_option = st.radio("Tùy chỉnh giọng đọc 🎧:", ("👩 Giọng Nữ (SunHi)", "👨 Giọng Nam (InJoon)"), horizontal=True)
voice_code = "ko-KR-SunHiNeural" if "Nữ" in voice_option else "ko-KR-InJoonNeural"
st.divider()

# --- DATA TỪ VỰNG ---
vocab_data = {
    "Cấp 3": [
        {"stt": 1, "kr": "노력", "vn": "nỗ lực"}, {"stt": 2, "kr": "발전", "vn": "phát triển"},
        {"stt": 3, "kr": "환경", "vn": "môi trường"}, {"stt": 4, "kr": "결과", "vn": "kết quả"}
    ],
    "Cấp 4": [
        {"stt": 1, "kr": "강조하다", "vn": "nhấn mạnh"}, {"stt": 2, "kr": "관련되다", "vn": "có liên quan"}
    ]
}

danh_sach_cap_do = list(vocab_data.keys())
tabs = st.tabs(danh_sach_cap_do)

for idx, tab in enumerate(tabs):
    with tab:
        ten_cap_do = danh_sach_cap_do[idx]
        current_vocab = vocab_data[ten_cap_do]
        
        c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 2, 2.5, 3, 2])
        c1.markdown("<div class='center-text'><b>STT</b></div>", unsafe_allow_html=True)
        c2.markdown("<div class='center-text'><b>Tiếng Hàn</b></div>", unsafe_allow_html=True)
        c3.markdown("<div class='center-text'><b>Nghĩa Tiếng Việt</b></div>", unsafe_allow_html=True)
        c4.markdown("<div class='center-text'><b>Nghe (Inline)</b></div>", unsafe_allow_html=True)
        c5.markdown("<div class='center-text'><b>Ôn Tập Viết</b></div>", unsafe_allow_html=True)
        c6.markdown("<div class='center-text'><b>Check Var</b></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        for word in current_vocab:
            c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 2, 2.5, 3, 2])
            
            c1.markdown(f"<div class='center-text'>{word['stt']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='korean-text'>{word['kr']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='center-text'>{word['vn']}</div>", unsafe_allow_html=True)
            
            audio_bytes = get_audio_bytes(word["kr"], voice_code)
            c4.audio(audio_bytes, format='audio/mp3')
            
            word_key = f"{ten_cap_do}_{word['stt']}"
            saved_answer = user_data.get(word_key, "")
            
            current_input = c5.text_input("Gõ lại", value=saved_answer, key=f"input_{word_key}", label_visibility="collapsed")
            
            if current_input != saved_answer:
                user_data[word_key] = current_input
                save_data(st.session_state.username, user_data)
            
            if current_input:
                if current_input.strip() == word["kr"]:
                    c6.success("CHUẨN CMNR✅")
                else:
                    c6.error("PHÍ TIỀN ĂN HỌC❌")
