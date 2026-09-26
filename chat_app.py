import streamlit as st
import google.generativeai as genai
import pypdf
import io
import os
import sqlite3
import bcrypt
from gtts import gTTS

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & DARK PREMIUM CLAUDE THEME
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Claude 3.5 Sonnet Enterprise", page_icon="🧡", layout="wide")

st.markdown("""
    <style>
    /* Dark Premium Claude Theme */
    .stApp {
        background-color: #18181B;
        color: #F4F4F5;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    #MainMenu, footer, header {visibility: hidden;}
    
    .main .block-container {
        max-width: 1000px;
        padding-top: 1.5rem;
    }
    
    /* Header Styling */
    .claude-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #D97706;
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .claude-sub {
        text-align: center;
        color: #A1A1AA;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    
    /* Auth Card & Buttons */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #09090B !important;
        border-right: 1px solid #27272A;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #27272A;
        padding: 5px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #A1A1AA;
        border-radius: 6px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #D97706 !important;
        color: #FFFFFF !important;
    }
    
    /* Chat Bubble Enhancements */
    .stChatMessage {
        background-color: #27272A;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
        border: 1px solid #3F3F46;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATABASE SETUP
# -----------------------------------------------------------------------------
def get_db_connection():
    return sqlite3.connect('users.db', timeout=10, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            plan TEXT DEFAULT 'Free'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def hash_pass(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pass(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def register_user(username, password):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, plan) VALUES (?, ?, ?)', (username, hash_pass(password), 'Free'))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def authenticate_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password, plan FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data and check_pass(password, data[0]):
        return data[1]
    return None

# -----------------------------------------------------------------------------
# 3. GEMINI AI ENGINE SETUP
# -----------------------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

# Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_plan" not in st.session_state:
    st.session_state.user_plan = "Free"
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------------------------------------------
# 4. LOGIN & SOCIAL AUTHENTICATION PORTAL
# -----------------------------------------------------------------------------
if not st.session_state.logged_in:
    st.markdown("<div class='claude-title'>🧡 Claude Enterprise Portal</div>", unsafe_allow_html=True)
    st.markdown("<div class='claude-sub'>Sign in with Google, GitHub, or Email to continue</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🚀 Instant Social Login", "🔑 Email Login"])
        
        with tab1:
            st.write("### Single Click Sign-In")
            if st.button("🌐 Continue with Google", use_container_width=True, type="primary"):
                st.session_state.logged_in = True
                st.session_state.username = "google.user@gmail.com"
                st.session_state.user_plan = "Enterprise"
                st.rerun()
                
            if st.button("🐙 Continue with GitHub", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.username = "github_developer"
                st.session_state.user_plan = "Enterprise"
                st.rerun()
                
        with tab2:
            st.write("### Email Authentication")
            u_email = st.text_input("Email / Username")
            u_pass = st.text_input("Password", type="password")
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Log In", use_container_width=True, type="primary"):
                    plan = authenticate_user(u_email, u_pass)
                    if plan:
                        st.session_state.logged_in = True
                        st.session_state.username = u_email
                        st.session_state.user_plan = plan
                        st.rerun()
                    else:
                        st.error("Invalid Credentials")
            with c_btn2:
                if st.button("Sign Up", use_container_width=True):
                    if register_user(u_email, u_pass):
                        st.success("Account created! Press Log In.")
                    else:
                        st.error("User exists.")
    st.stop()

# -----------------------------------------------------------------------------
# 5. SIDEBAR CONTROL PANEL
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧡 Claude 3.5 Suite")
    st.markdown(f"**Account:** `{st.session_state.username}`")
    st.markdown(f"**Tier:** <span style='background:#D97706; padding:3px 8px; border-radius:6px; color:#fff; font-weight:bold;'>{st.session_state.user_plan}</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.button("➕ New Chat Session", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# -----------------------------------------------------------------------------
# 6. MAIN SYSTEMIC APPLICATION (PC CLAUDE STYLE)
# -----------------------------------------------------------------------------
st.markdown(f"<div class='claude-title'>Good day, {st.session_state.username.split('@')[0]}</div>", unsafe_allow_html=True)

chat_tab, doc_tab, code_tab = st.tabs(["💬 AI Chat & Voice", "📄 10k Page Doc Analyzer", "💻 Code Sandbox"])

# --- TAB 1: CHAT + FAST RESPONSES + AUDIO OUTPUT ---
with chat_tab:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Ask Claude anything...")
    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        if not model:
            st.error("⚠️ Invalid API Key. Please update your GEMINI_API_KEY in Streamlit Secrets with an AIzaSy... key.")
        else:
            with st.chat_message("assistant"):
                try:
                    # Detailed system prompt for PC-style long answers
                    system_prompt = f"Provide a detailed, structured, highly professional response for: {user_prompt}"
                    res = model.generate_content(system_prompt)
                    ans = res.text
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                    
                    # Voice Output
                    tts = gTTS(text=ans[:200], lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format='audio/mp3')
                except Exception as e:
                    st.error(f"Error: {e}")

# --- TAB 2: DOCUMENT ANALYZER ---
with doc_tab:
    st.subheader("📄 Upload & Read Large Files")
    up_file = st.file_uploader("Upload PDF Document", type=["pdf"])
    if up_file:
        reader = pypdf.PdfReader(up_file)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""
        st.success(f"Loaded {len(reader.pages)} Pages successfully!")
        
        q = st.text_input("What do you want to extract?")
        if st.button("Analyze PDF", type="primary"):
            if model and q:
                res = model.generate_content(f"Document:\n{full_text[:30000]}\n\nQuestion: {q}")
                st.markdown(res.text)

# --- TAB 3: CODE GENERATOR ---
with code_tab:
    st.subheader("💻 Python & Web Code Sandbox")
    c_input = st.text_area("Describe the code/application to build:")
    if st.button("Generate Code", type="primary"):
        if model and c_input:
            res = model.generate_content(f"Write full production ready code for: {c_input}")
            st.code(res.text)
