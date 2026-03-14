import streamlit as st
import edge_tts
import asyncio
import json
import hashlib
import gspread
import time as time_module
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
from vocab_data import get_vocab

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Học TOPIK Cùng AI - By Tuân", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""<style>
    a.header-anchor { display: none !important; }
    button[data-baseweb="tab"] { font-size: 20px !important; padding: 10px 20px !important; }
    button[data-baseweb="tab"][aria-selected="true"] {
        font-size: 28px !important; font-weight: 900 !important;
        color: #FFD700 !important; background-color: #2b2b2b !important;
        border-bottom: 4px solid #FFD700 !important;
    }
    /* Sticky tabs - luôn hiện khi cuộn */
    div[data-testid="stTabs"] > div:first-child {
        position: sticky; top: 0; z-index: 999;
        background: #0e1117; padding-top: 5px;
        border-bottom: 2px solid #333;
    }
    .center-text { text-align:center; display:flex; justify-content:center; align-items:center; margin-top:18px; font-size:16px; }
    .korean-text { color:#FFD700; font-size:28px; font-weight:bold; text-align:center; display:flex; justify-content:center; align-items:center; margin-top:10px; }
    .progress-box { background: linear-gradient(135deg, #1a1a2e, #16213e); border:1px solid #FFD700; border-radius:10px; padding:10px 15px; text-align:center; }
    .progress-box h3 { color:#FFD700; margin:0; }
    .progress-box p { color:white; margin:5px 0 0 0; font-size:14px; }
    /* Padding dưới cho bottom nav */
    .main .block-container { padding-bottom: 80px !important; }
</style>""", unsafe_allow_html=True)

# --- KẾT NỐI GOOGLE SHEETS ---
@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
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

# --- HÀM TIỆN ÍCH ---
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users_db():
    rows = sheet_users.get_all_values()
    return {r[0]: r[1] for r in rows[1:] if len(r) >= 2}

def save_new_user(username, pw_hash):
    sheet_users.append_row([username, pw_hash])

def load_data(username):
    rows = sheet_progress.get_all_values()
    for row in rows[1:]:
        if len(row) >= 2 and row[0] == username:
            return json.loads(row[1])
    return {}

def save_data(username, data):
    rows = sheet_progress.get_all_values()
    data_str = json.dumps(data, ensure_ascii=False)
    for i, row in enumerate(rows):
        if i > 0 and len(row) >= 1 and row[0] == username:
            sheet_progress.update_cell(i + 1, 2, data_str)
            return
    sheet_progress.append_row([username, data_str])

# --- ĐĂNG NHẬP / ĐĂNG KÝ ---
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
                with st.spinner('Đang kết nối... ⏳'):
                    users_db = load_users_db()
                    if login_user in users_db and users_db[login_user] == hash_password(login_pass):
                        st.session_state.authenticated = True
                        st.session_state.username = login_user
                        st.session_state.study_start = time_module.time()
                        st.rerun()
                    else:
                        st.error("❌ Sai tài khoản hoặc mật khẩu!")

    with tab_register:
        st.subheader("Tạo tài khoản học mới")
        with st.form("register_form"):
            reg_user = st.text_input("Tên tài khoản (viết liền không dấu):")
            reg_pass = st.text_input("Mật khẩu:", type="password")
            reg_pass2 = st.text_input("Nhập lại mật khẩu:", type="password")
            submit_reg = st.form_submit_button("Tạo Tài Khoản ✨")
            if submit_reg:
                with st.spinner('Đang tạo tài khoản... ⏳'):
                    users_db = load_users_db()
                    if not reg_user or not reg_pass:
                        st.warning("⚠️ Điền đầy đủ thông tin!")
                    elif reg_user in users_db:
                        st.error("❌ Tên tài khoản đã tồn tại!")
                    elif reg_pass != reg_pass2:
                        st.error("❌ Mật khẩu không khớp!")
                    else:
                        save_new_user(reg_user, hash_password(reg_pass))
                        st.success("🎉 Đăng ký thành công! Chuyển qua tab Đăng Nhập.")
    st.stop()

# ==========================================
# GIAO DIỆN HỌC (SAU KHI ĐĂNG NHẬP)
# ==========================================

# --- Timer ---
if "study_start" not in st.session_state:
    st.session_state.study_start = time_module.time()
elapsed = int(time_module.time() - st.session_state.study_start)

# --- Load data ---
user_data = load_data(st.session_state.username)
vocab_data = get_vocab()

# --- Header ---
c1, c2, c3, c4 = st.columns([5, 2, 2, 1.5])
with c1:
    st.title("Bảng Từ Vựng TOPIK 🚀 - By Tuân")
with c2:
    st.info(f"⏱️ Đã học: **{elapsed//60}p{elapsed%60:02d}s**")
with c3:
    st.success(f"👤 **{st.session_state.username}**")
with c4:
    if st.button("Đăng xuất 👋"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

# --- Tiến độ tổng quan ---
pc1, pc2, pc3 = st.columns(3)
for col, level_name in zip([pc1, pc2, pc3], ["Cấp 3", "Cấp 4", "Cấp 5"]):
    words = vocab_data[level_name]
    done = sum(1 for w in words if user_data.get(f"{level_name}_{w['stt']}", "").strip())
    pct = int(done / len(words) * 100) if words else 0
    with col:
        st.markdown(f"""<div class="progress-box">
            <h3>{level_name}</h3>
            <p>✅ {done}/{len(words)} từ ({pct}%)</p>
        </div>""", unsafe_allow_html=True)

st.divider()

# --- Giọng đọc ---
@st.cache_data
def get_audio_bytes(text, voice):
    async def _gen():
        comm = edge_tts.Communicate(text, voice)
        data = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                data.extend(chunk["data"])
        return bytes(data)
    return asyncio.run(_gen())

voice_opt = st.radio("Giọng đọc 🎧:", ("👩 Nữ (SunHi)", "👨 Nam (InJoon)"), horizontal=True)
voice_code = "ko-KR-SunHiNeural" if "Nữ" in voice_opt else "ko-KR-InJoonNeural"
st.divider()

# --- TABS ---
danh_sach = list(vocab_data.keys())
tabs = st.tabs(danh_sach)

for idx, tab in enumerate(tabs):
    with tab:
        ten = danh_sach[idx]
        current_vocab = vocab_data[ten]

        # --- Nút "Xem học đến đâu" ---
        last_stt = 0
        for w in current_vocab:
            if user_data.get(f"{ten}_{w['stt']}", "").strip():
                last_stt = w['stt']

        btn_col1, btn_col2 = st.columns([1, 5])
        with btn_col1:
            scroll_clicked = st.button(f"📍 Học đến đâu?", key=f"scroll_{ten}")
        with btn_col2:
            if last_stt > 0:
                st.caption(f"Đã học đến từ **#{last_stt}** / {len(current_vocab)}")
            else:
                st.caption("Chưa bắt đầu học cấp này")

        # --- Header bảng ---
        h1, h2, h3, h4, h5, h6 = st.columns([1, 1.5, 2, 2.5, 3, 2])
        h1.markdown("<div class='center-text'><b>STT</b></div>", unsafe_allow_html=True)
        h2.markdown("<div class='center-text'><b>Tiếng Hàn</b></div>", unsafe_allow_html=True)
        h3.markdown("<div class='center-text'><b>Nghĩa TV</b></div>", unsafe_allow_html=True)
        h4.markdown("<div class='center-text'><b>Nghe</b></div>", unsafe_allow_html=True)
        h5.markdown("<div class='center-text'><b>Ôn Tập Viết</b></div>", unsafe_allow_html=True)
        h6.markdown("<div class='center-text'><b>Kết Quả</b></div>", unsafe_allow_html=True)
        st.markdown("---")

        # --- Danh sách từ ---
        for word in current_vocab:
            word_key = f"{ten}_{word['stt']}"
            # Anchor HTML để scroll tới
            st.markdown(f"<div id='word_{word_key}'></div>", unsafe_allow_html=True)

            c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 2, 2.5, 3, 2])
            c1.markdown(f"<div class='center-text'>{word['stt']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='korean-text'>{word['kr']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='center-text'>{word['vn']}</div>", unsafe_allow_html=True)

            audio_bytes = get_audio_bytes(word["kr"], voice_code)
            c4.audio(audio_bytes, format='audio/mp3')

            saved = user_data.get(word_key, "")
            current_input = c5.text_input("Gõ lại", value=saved, key=f"input_{word_key}", label_visibility="collapsed")

            if current_input != saved:
                user_data[word_key] = current_input
                save_data(st.session_state.username, user_data)

            if current_input:
                if current_input.strip() == word["kr"]:
                    c6.success("CHUẨN ✅")
                else:
                    c6.error("SAI ❌")

        # --- Nút chuyển cấp ở CUỐI mỗi tab ---
        st.markdown("---")
        st.markdown(f"### 🎉 Hết danh sách {ten}! Chuyển sang cấp khác:")
        nav1, nav2, nav3 = st.columns(3)
        other_levels = [l for l in danh_sach if l != ten]
        for nav_col, lv in zip([nav1, nav2], other_levels):
            with nav_col:
                if st.button(f"👉 Chuyển sang {lv}", key=f"nav_{ten}_{lv}"):
                    # Inject JS to click target tab
                    target_idx = danh_sach.index(lv)
                    components.html(f"""<script>
                        var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                        if (tabs[{target_idx}]) tabs[{target_idx}].click();
                    </script>""", height=0)

    # --- Scroll JS khi bấm "Xem học đến đâu" ---
    if scroll_clicked and last_stt > 0:
        components.html(f"""<script>
            var el = window.parent.document.getElementById('word_{ten}_{last_stt}');
            if (el) el.scrollIntoView({{behavior:'smooth', block:'center'}});
        </script>""", height=0)

# --- BOTTOM NAV BAR (luôn hiện ở dưới cùng) ---
components.html("""
<style>
.bnav{position:fixed;bottom:0;left:0;right:0;z-index:10000;background:linear-gradient(135deg,#0e1117,#1a1a2e);padding:8px 0;display:flex;justify-content:center;gap:15px;border-top:2px solid #FFD700;box-shadow:0 -4px 15px rgba(0,0,0,0.5)}
.bnav button{background:linear-gradient(135deg,#e67e22,#f39c12);color:#fff;border:none;padding:10px 28px;border-radius:25px;font-weight:900;font-size:14px;cursor:pointer;transition:all .3s}
.bnav button:hover{background:linear-gradient(135deg,#d35400,#e67e22);transform:scale(1.08)}
</style>
<div class="bnav">
    <button onclick="parent.document.querySelectorAll('button[data-baseweb=\\'tab\\']')[0].click();parent.scrollTo({top:0,behavior:'smooth'})">📗 Cấp 3</button>
    <button onclick="parent.document.querySelectorAll('button[data-baseweb=\\'tab\\']')[1].click();parent.scrollTo({top:0,behavior:'smooth'})">📘 Cấp 4</button>
    <button onclick="parent.document.querySelectorAll('button[data-baseweb=\\'tab\\']')[2].click();parent.scrollTo({top:0,behavior:'smooth'})">📕 Cấp 5</button>
</div>
""", height=55)
