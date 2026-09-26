import streamlit as st
import google.generativeai as genai
import pypdf
import io
import os
import sqlite3
import bcrypt
from gtts import gTTS

# -----------------------------------------------------------------------------
# 1. DATABASE SETUP (FIXED FOR STREAMLIT)
# -----------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect('users.db', timeout=10, check_same_thread=False)
    return conn

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

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(username, password):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute('INSERT INTO users (username, password, plan) VALUES (?, ?, ?)', (username, hashed, 'Free'))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password, plan FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data and check_password(password, data[0]):
        return data[1]
    return None

def upgrade_user_plan(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET plan = ? WHERE username = ?', ('Enterprise', username))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# 2. GEMINI AI ENGINE SETUP
# -----------------------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

# -----------------------------------------------------------------------------
# 3. STREAMLIT PAGE CONFIG & CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Claude Enterprise AI Suite", page_icon="✴️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main .block-container {
        max-width: 950px;
        padding-top: 1.5rem;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 600;
        color: #2D2B2A;
        text-align: center;
        margin-bottom: 1rem;
        font-family: 'Georgia', serif;
    }
    .plan-badge {
        background-color: #FEF3C7;
        color: #D97706;
        padding: 4px 10px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

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
# 4. LOGIN / SIGNUP PORTAL
# -----------------------------------------------------------------------------
if not st.session_state.logged_in:
    st.markdown("<div class='hero-title'>✴️ Enterprise AI Suite Portal</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Log In", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Welcome Back")
        login_user = st.text_input("Username / Email", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Log In", use_container_width=True):
            plan = authenticate_user(login_user, login_pass)
            if plan:
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.session_state.user_plan = plan
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")
                
    with tab2:
        st.subheader("Create an Account")
        signup_user = st.text_input("Choose Username / Email", key="signup_user")
        signup_pass = st.text_input("Choose Password", type="password", key="signup_pass")
        
        if st.button("Sign Up", use_container_width=True):
            if signup_user and signup_pass:
                if register_user(signup_user, signup_pass):
                    st.success("Account created successfully! Please Log In.")
                else:
                    st.error("Username already exists!")
            else:
                st.warning("Please fill all fields.")
    st.stop()

# -----------------------------------------------------------------------------
# 5. SIDEBAR (UPGRADE & TOOLS)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("✴️ Claude AI Suite")
    st.markdown(f"**User:** `{st.session_state.username}`")
    st.markdown(f"**Plan:** <span class='plan-badge'>{st.session_state.user_plan}</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.session_state.user_plan == "Free":
        with st.popover("🚀 Upgrade Plan ($2,400)", use_container_width=True):
            st.markdown("### Enterprise Features Unlocked")
            st.write("• 10,000+ Page PDF & Doc Scanner")
            st.write("• High-speed Code Interpreter")
            st.write("• Multi-lingual Voice Output (TTS)")
            st.write("• Video & Image Intelligence")
            st.markdown("---")
            if st.button("💳 Upgrade Now", type="primary", use_container_width=True):
                upgrade_user_plan(st.session_state.username)
                st.session_state.user_plan = "Enterprise"
                st.success("Upgraded to Enterprise Plan!")
                st.rerun()
                
    st.markdown("---")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# -----------------------------------------------------------------------------
# 6. MAIN CLAUDE SUITE APP (VOICE, DOCS, CODE, CHAT)
# -----------------------------------------------------------------------------
st.markdown(f"<div class='hero-title'>✴️ What's cooking, {st.session_state.username}?</div>", unsafe_allow_html=True)

# TAB NAVIGATION FOR ALL CLAUDE FEATURES
chat_tab, doc_tab, code_tab = st.tabs(["💬 AI Chat & Voice", "📄 10k Page Doc Scanner", "💻 Code Sandbox"])

# --- TAB 1: AI CHAT & VOICE ---
with chat_tab:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Ask anything in any language...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        if not model:
            st.error("API Key Missing in Streamlit Secrets!")
        else:
            with st.chat_message("assistant"):
                try:
                    response = model.generate_content(user_input)
                    reply_text = response.text
                    st.write(reply_text)
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    
                    # Voice synthesis (Audio Output)
                    tts = gTTS(text=reply_text[:300], lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format='audio/mp3')
                except Exception as e:
                    st.error(f"Error: {e}")

# --- TAB 2: 10,000 PAGE PDF / DOC SCANNER ---
with doc_tab:
    st.subheader("📄 Upload Large PDF / Document")
    uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])
    
    if uploaded_file:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
            
        st.success(f"File Uploaded! Extracted {len(pdf_reader.pages)} Pages ({len(text)} characters).")
        doc_query = st.text_input("Ask a question about this document:")
        
        if st.button("Analyze Document"):
            if model and doc_query:
                prompt = f"Document Context:\n{text[:20000]}\n\nUser Question: {doc_query}"
                res = model.generate_content(prompt)
                st.markdown("### 🤖 Analysis Result:")
                st.write(res.text)

# --- TAB 3: CODE MODE / SANDBOX ---
with code_tab:
    st.subheader("💻 AI Code Generator")
    code_prompt = st.text_area("Describe the code you want to build:")
    if st.button("Generate Code"):
        if model and code_prompt:
            res = model.generate_content(f"Write clean, production code for: {code_prompt}")
            st.code(res.text)
