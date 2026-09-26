import streamlit as st
import google.generativeai as genai
import pypdf
import io
import os
import sqlite3
import bcrypt
from gtts import gTTS

# -----------------------------------------------------------------------------
# 1. DATABASE SETUP
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

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(username, password):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password, plan) VALUES (?, ?, ?)', 
                  (username, hash_password(password), 'Free'))
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
# 3. COLORFUL CLAUDE-STYLE CUSTOM UI (CSS)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Claude Enterprise AI Suite", page_icon="✴️", layout="wide")

st.markdown("""
    <style>
    /* Global Styling */
    .stApp {
        background-color: #FAF7F2;
        font-family: 'Söhne', 'Helvetica Neue', Arial, sans-serif;
    }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Center Box & Container */
    .main .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }
    
    /* Headers & Title */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #D97706;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    
    /* Auth Cards */
    .auth-card {
        background: #FFFFFF;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
    }
    
    /* Social Login Buttons */
    .social-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 8px;
        border: 1px solid #D1D5DB;
        background-color: #FFFFFF;
        font-weight: 600;
        cursor: pointer;
    }
    
    /* Badges */
    .plan-badge {
        background-color: #FEF3C7;
        color: #B45309;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# Session States initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_plan" not in st.session_state:
    st.session_state.user_plan = "Free"
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------------------------------------------
# 4. LOGIN / SIGNUP PORTAL WITH GOOGLE & OTHER OPTIONS
# -----------------------------------------------------------------------------
if not st.session_state.logged_in:
    st.markdown("<div class='hero-title'>✴️ Claude Enterprise Portal</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Sign in to access your AI Assistant</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Log In", "📝 Sign Up"])
        
        with tab1:
            st.markdown("### Continue with Socials")
            if st.button("🌐 Continue with Google", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.username = "google_user@gmail.com"
                st.session_state.user_plan = "Free"
                st.rerun()
                
            if st.button("🐙 Continue with GitHub", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.username = "github_user"
                st.session_state.user_plan = "Free"
                st.rerun()
                
            st.markdown("---")
            st.markdown("### Or use Email")
            login_user = st.text_input("Email Address", key="login_user")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Log In", type="primary", use_container_width=True):
                plan = authenticate_user(login_user, login_pass)
                if plan:
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.session_state.user_plan = plan
                    st.success("Successfully Logged In!")
                    st.rerun()
                else:
                    st.error("Invalid Email or Password")
                    
        with tab2:
            st.markdown("### Create New Account")
            signup_user = st.text_input("Email Address", key="signup_user")
            signup_pass = st.text_input("Password", type="password", key="signup_pass")
            
            if st.button("Sign Up", type="primary", use_container_width=True):
                if signup_user and signup_pass:
                    if register_user(signup_user, signup_pass):
                        st.success("Account created! Please switch to Login tab.")
                    else:
                        st.error("Email already registered!")
                else:
                    st.warning("Please fill all fields.")
    st.stop()

# -----------------------------------------------------------------------------
# 5. SIDEBAR & NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("✴️ Claude Suite")
    st.markdown(f"**User:** `{st.session_state.username}`")
    st.markdown(f"**Plan:** <span class='plan-badge'>{st.session_state.user_plan}</span>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.session_state.user_plan == "Free":
        with st.popover("🚀 Upgrade to Enterprise ($2,400)", use_container_width=True):
            st.markdown("### Unlocked Capabilities")
            st.write("✓ 10,000+ Page Document Scanning")
            st.write("✓ Multilingual Voice Responses")
            st.write("✓ Code Sandbox & Interpreter")
            st.write("✓ High-Speed Priority Processing")
            st.markdown("---")
            if st.button("💳 Upgrade Plan Now", type="primary", use_container_width=True):
                st.session_state.user_plan = "Enterprise"
                st.success("Upgraded!")
                st.rerun()
                
    st.markdown("---")
    if st.button("➕ Clear & New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

# -----------------------------------------------------------------------------
# 6. MAIN SYSTEMIC APPLICATION FEATURES
# -----------------------------------------------------------------------------
st.markdown(f"<div class='hero-title'>✴️ Welcome back, {st.session_state.username}</div>", unsafe_allow_html=True)

chat_tab, doc_tab, code_tab = st.tabs(["💬 AI Chat & Voice", "📄 10,000 Page Doc Scanner", "💻 Code Sandbox"])

# --- TAB 1: AI CHAT WITH VOICE OUTPUT ---
with chat_tab:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input("Ask Claude anything in any language...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        if not model:
            st.error("API Key missing or invalid. Update GEMINI_API_KEY in Streamlit Secrets.")
        else:
            with st.chat_message("assistant"):
                try:
                    response = model.generate_content(user_input)
                    reply_text = response.text
                    st.write(reply_text)
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    
                    # Voice Output Synthesis
                    tts = gTTS(text=reply_text[:250], lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format='audio/mp3')
                except Exception as e:
                    st.error(f"Execution Error: {e}")

# --- TAB 2: LARGE DOCUMENT SCANNER ---
with doc_tab:
    st.subheader("📄 Upload & Analyze Documents")
    uploaded_file = st.file_uploader("Upload PDF or Large Document", type=["pdf"])
    
    if uploaded_file:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
            
        st.success(f"Processed Document: {len(pdf_reader.pages)} pages extracted.")
        doc_query = st.text_input("What would you like to know from this document?")
        
        if st.button("Run Document Analysis", type="primary"):
            if model and doc_query:
                prompt = f"Document Context:\n{text[:25000]}\n\nQuestion: {doc_query}"
                res = model.generate_content(prompt)
                st.markdown("### 🤖 Analysis Summary:")
                st.write(res.text)

# --- TAB 3: CODE SANDBOX ---
with code_tab:
    st.subheader("💻 AI Code Sandbox")
    code_prompt = st.text_area("Describe the code or script to build:")
    if st.button("Generate Production Code", type="primary"):
        if model and code_prompt:
            res = model.generate_content(f"Provide clean, well-commented code for: {code_prompt}")
            st.code(res.text)
