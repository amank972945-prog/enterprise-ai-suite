import streamlit as st
import google.generativeai as genai
import pypdf
import sys
import io
import sqlite3
import bcrypt
from gtts import gTTS

# -----------------------------------------------------------------------------
# 1. DATABASE SETUP (USERS & SUBSCRIPTIONS)
# -----------------------------------------------------------------------------
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        plan TEXT DEFAULT 'Free'
    )
''')
conn.commit()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(username, password):
    try:
        hashed = hash_password(password)
        c.execute('INSERT INTO users (username, password, plan) VALUES (?, ?, ?)', (username, hashed, 'Free'))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    c.execute('SELECT password, plan FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    if data and check_password(password, data[0]):
        return data[1] # Returns plan ('Free' or 'Enterprise')
    return None

def upgrade_user_plan(username):
    c.execute('UPDATE users SET plan = ? WHERE username = ?', ('Enterprise', username))
    conn.commit()

# -----------------------------------------------------------------------------
# 2. PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Enterprise AI Suite", page_icon="✴️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 500;
        color: #2D2B2A;
        text-align: center;
        margin-bottom: 1.5rem;
        font-family: 'Georgia', serif;
    }
    .plan-badge {
        background-color: #FEF3C7;
        color: #D97706;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# Session State Initializations
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_plan" not in st.session_state:
    st.session_state.user_plan = "Free"

# -----------------------------------------------------------------------------
# 3. AUTHENTICATION UI (LOGIN / SIGNUP)
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
                st.success(f"Logged in as {login_user}")
                st.rerun()
            else:
                st.error("Invalid Username or Password")
                
    with tab2:
        st.subheader("Create a New Account")
        signup_user = st.text_input("Choose Username / Email", key="signup_user")
        signup_pass = st.text_input("Choose Password", type="password", key="signup_pass")
        
        if st.button("Sign Up", use_container_width=True):
            if signup_user and signup_pass:
                if register_user(signup_user, signup_pass):
                    st.success("Account created successfully! Please log in.")
                else:
                    st.error("Username already exists. Try logging in.")
            else:
                st.warning("Please fill out all fields.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. LOGGED-IN SIDEBAR & UPGRADE SYSTEM
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("✴️ Enterprise AI")
    st.markdown(f"**User:** `{st.session_state.username}`")
    st.markdown(f"**Plan:** <span class='plan-badge'>{st.session_state.user_plan}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # UPGRADE BUTTON FOR FREE USERS
    if st.session_state.user_plan == "Free":
        with st.popover("🚀 Upgrade Plan", use_container_width=True):
            st.markdown("### Enterprise Plan Upgrade")
            st.write("• Unlimited 1000+ Page PDF Scanning")
            st.write("• Priority Gemini 3.8 Flash Engine")
            st.write("• Live Python Sandbox Code Execution")
            st.write("• Multi-lingual Voice Synthesis")
            st.markdown("---")
            st.markdown("**Price: $2,400 / One-time Buyout**")
            
            # Simulated Payment Gateway Button (Integrate Razorpay / Stripe Link Here)
            payment_confirmed = st.button("💳 Pay via Stripe / UPI", type="primary")
            if payment_confirmed:
                upgrade_user_plan(st.session_state.username)
                st.session_state.user_plan = "Enterprise"
                st.success("🎉 Upgrade Successful! Enterprise Unlocked.")
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
# 5. MAIN AI CHAT INTERFACE
# -----------------------------------------------------------------------------
st.markdown(f"<div class='hero-title'>✴️ What's cooking, {st.session_state.username}?</div>", unsafe_allow_html=True)

# Rest of AI Chat Logic (Gemini API Call & PDF Scanner)
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_input = st.chat_input("How can I help you today?")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
        
    with st.chat_message("assistant"):
        st.write("Gemini AI Response executing for logged-in user...")
