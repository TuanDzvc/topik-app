import streamlit as st
import edge_tts
import asyncio
import json
import hashlib
import gspread
from datetime import datetime, timezone, timedelta

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
    /* Ẩn header bảng trên mobile */
    @media (max-width: 768px) {
        .table-header { display: none !important; }
    }
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
    db = {}
    for r in rows[1:]:
        if len(r) >= 2:
            db[r[0]] = {"pw": r[1], "name": r[2] if len(r) >= 3 else r[0]}
    return db

def save_new_user(username, pw_hash, display_name):
    sheet_users.append_row([username, pw_hash, display_name])

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

# --- Khôi phục session từ URL (fix Safari iOS mất WebSocket) ---
if not st.session_state.authenticated:
    params = st.query_params
    if "user" in params:
        saved_user = params["user"]
        try:
            users_db = load_users_db()
            if saved_user in users_db:
                st.session_state.authenticated = True
                st.session_state.username = saved_user
                st.session_state.display_name = users_db[saved_user]["name"]
        except:
            pass

if not st.session_state.authenticated:
    st.title("🔐 Hệ thống Đăng nhập Lớp Học TOPIK - By Tuân")
    tab_login, tab_register = st.tabs(["Đăng Nhập 🔑", "Đăng Ký Tài Khoản Mới 📝"])

    with tab_login:
        st.subheader("Chào mừng trở lại!")

        def do_login():
            users_db = load_users_db()
            u = st.session_state.get("_login_user", "")
            p = st.session_state.get("_login_pass", "")
            if u in users_db and users_db[u]["pw"] == hash_password(p):
                st.session_state.authenticated = True
                st.session_state.username = u
                st.session_state.display_name = users_db[u]["name"]
                st.session_state._login_error = False
                st.query_params["user"] = u
            else:
                st.session_state._login_error = True

        with st.form("login_form"):
            st.text_input("Tài khoản:", key="_login_user")
            st.text_input("Mật khẩu:", type="password", key="_login_pass")
            st.form_submit_button("Vào Học 🚀", on_click=do_login)

        if st.session_state.get("_login_error"):
            st.error("❌ Sai tài khoản hoặc mật khẩu!")

    with tab_register:
        st.subheader("Tạo tài khoản học mới")
        with st.form("register_form"):
            reg_name = st.text_input("Họ và Tên:")
            reg_user = st.text_input("Tên tài khoản (viết liền không dấu):")
            reg_pass = st.text_input("Mật khẩu:", type="password")
            reg_pass2 = st.text_input("Nhập lại mật khẩu:", type="password")
            submit_reg = st.form_submit_button("Tạo Tài Khoản ✨")
            if submit_reg:
                with st.spinner('Đang tạo tài khoản... ⏳'):
                    users_db = load_users_db()
                    if not reg_user or not reg_pass or not reg_name:
                        st.warning("⚠️ Điền đầy đủ thông tin!")
                    elif reg_user in users_db:
                        st.error("❌ Tên tài khoản đã tồn tại!")
                    elif reg_pass != reg_pass2:
                        st.error("❌ Mật khẩu không khớp!")
                    else:
                        save_new_user(reg_user, hash_password(reg_pass), reg_name)
                        st.success("🎉 Đăng ký thành công! Đang chuyển sang đăng nhập...")
                        st.session_state.authenticated = False
                        components.html("""<script>
                            setTimeout(function(){
                                var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                                if(tabs[0]) tabs[0].click();
                            }, 500);
                        </script>""", height=0)
    st.stop()

# ==========================================
# GIAO DIỆN HỌC (SAU KHI ĐĂNG NHẬP)
# ==========================================



# --- Load data ---
user_data = load_data(st.session_state.username)
vocab_data = get_vocab()
display_name = st.session_state.get("display_name", st.session_state.username)

# --- Anchor đầu trang ---
st.markdown("<div id='page-top'></div>", unsafe_allow_html=True)

# --- Đồng hồ VN / KR ---
vn_tz = timezone(timedelta(hours=7))
kr_tz = timezone(timedelta(hours=9))
vn_time = datetime.now(vn_tz).strftime("%H:%M")
kr_time = datetime.now(kr_tz).strftime("%H:%M")

# --- Header ---
st.title("Bảng Từ Vựng TOPIK - Giọng AI Chuẩn Hàn🚀- By Tuân")
c1, c2, c3, c4 = st.columns([4, 2.5, 2.5, 1.5])
with c1:
    st.markdown(f"### 👋 Chào mừng <span style='color:#FFD700;'>{display_name}</span> đã quay trở lại!", unsafe_allow_html=True)
with c2:
    st.info(f"🇻🇳 Việt Nam: **{vn_time}** &nbsp; | &nbsp; 🇰🇷 Hàn Quốc: **{kr_time}**")
with c3:
    st.success(f"👤 **{st.session_state.username}**")
with c4:
    def do_logout():
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.display_name = ""
        st.query_params.clear()
    st.button("Đăng xuất 👋", on_click=do_logout)

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

        # --- Header bảng (ẩn trên mobile) ---
        st.markdown("""<div class='table-header' style='display:flex; gap:5px; padding:10px 0; border-bottom:2px solid #444;'>
            <div style='flex:1; text-align:center; font-weight:bold;'>STT</div>
            <div style='flex:1.5; text-align:center; font-weight:bold;'>Tiếng Hàn</div>
            <div style='flex:2; text-align:center; font-weight:bold;'>Nghĩa TV</div>
            <div style='flex:2.5; text-align:center; font-weight:bold;'>Nghe</div>
            <div style='flex:3; text-align:center; font-weight:bold;'>Ôn Tập Viết</div>
            <div style='flex:2; text-align:center; font-weight:bold;'>Kết Quả</div>
        </div>""", unsafe_allow_html=True)

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
            current_input = c5.text_input("Gõ lại", value=saved, key=f"input_{word_key}", label_visibility="collapsed", placeholder="Điền từ vựng tiếng Hàn...")

            if current_input != saved:
                user_data[word_key] = current_input
                save_data(st.session_state.username, user_data)

            if current_input:
                if current_input.strip() == word["kr"]:
                    c6.success("CHUẨN ✅")
                else:
                    c6.error("SAI ❌")

        # --- Cuối danh sách ---
        st.markdown("---")
        st.markdown(f"### 🎉 Hết danh sách {ten}!")

    # --- Scroll JS khi bấm "Xem học đến đâu" ---
    if scroll_clicked and last_stt > 0:
        components.html(f"""<script>
            var el = window.parent.document.getElementById('word_{ten}_{last_stt}');
            if (el) el.scrollIntoView({{behavior:'smooth', block:'center'}});
        </script>""", height=0)

# --- BOTTOM NAV BAR + Nút TOP ---
components.html("""
<style>
.bnav{position:fixed;bottom:0;left:0;right:0;z-index:10000;background:linear-gradient(135deg,#0e1117,#1a1a2e);padding:8px 0;display:flex;justify-content:center;gap:15px;border-top:2px solid #FFD700;box-shadow:0 -4px 15px rgba(0,0,0,0.5)}
.bnav button{background:linear-gradient(135deg,#e67e22,#f39c12);color:#fff;border:none;padding:10px 28px;border-radius:25px;font-weight:900;font-size:14px;cursor:pointer;transition:all .3s}
.bnav button:hover{background:linear-gradient(135deg,#d35400,#e67e22);transform:scale(1.08)}
</style>
<div class="bnav">
    <button onclick="parent.document.querySelectorAll('button[data-baseweb=\\'tab\\']')[0].click();parent.document.querySelector('.main').scrollTo({top:0,behavior:'smooth'})">📗 Cấp 3</button>
    <button onclick="parent.document.querySelectorAll('button[data-baseweb=\\'tab\\']')[1].click();parent.document.querySelector('.main').scrollTo({top:0,behavior:'smooth'})">📘 Cấp 4</button>
    <button onclick="parent.document.querySelectorAll('button[data-baseweb=\\'tab\\']')[2].click();parent.document.querySelector('.main').scrollTo({top:0,behavior:'smooth'})">📕 Cấp 5</button>
</div>
<script>
var pdoc = parent.document;
var old = pdoc.getElementById('topBtnFixed');
if(old) old.remove();
var btn = pdoc.createElement('button');
btn.id = 'topBtnFixed';
btn.innerHTML = '🔝';
btn.title = 'Lên đầu trang';
btn.style.cssText = 'position:fixed;bottom:70px;right:20px;z-index:10001;background:linear-gradient(135deg,#2ecc71,#27ae60);color:#fff;border:none;width:55px;height:55px;border-radius:50%;font-size:22px;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.4);transition:all 0.3s;';
btn.onmouseover = function(){this.style.transform='scale(1.15)'};
btn.onmouseout = function(){this.style.transform='scale(1)'};
btn.onclick = function(){
    var anchor = pdoc.getElementById('page-top');
    if(anchor){ anchor.scrollIntoView({behavior:'smooth'}); }
    else { parent.scrollTo(0,0); }
};
pdoc.body.appendChild(btn);
</script>
""", height=55)
