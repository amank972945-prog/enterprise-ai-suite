import os
import urllib.parse
import streamlit as st
import pandas as pd
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="X GOD PRO - Jarvis Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Jarvis UI Styling
st.markdown("""
<style>
    body, .stApp { background-color: #0b0c10; color: #c5c6c7; }
    .stTextInput input, .stTextArea textarea {
        background-color: #1f2833 !important;
        color: #66fcf1 !important;
        border-radius: 12px !important;
        border: 1px solid #45a29e !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #45a29e 0%, #66fcf1 100%);
        color: #0b0c10; border-radius: 10px; border: none; font-weight: bold;
    }
    .jarvis-card {
        padding: 15px; background-color: #1f2833; border-radius: 12px;
        border-left: 5px solid #66fcf1; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ X GOD PRO - Autonomous Jarvis AI Engine")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Jarvis Core Settings")
    api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    selected_mode = st.selectbox("Engine Mode", [
        "Jarvis Voice & Actions", 
        "General Chat & Coding", 
        "Excel & Data Automation", 
        "Document Scanner", 
        "24/7 Background Task Queue"
    ])
    st.divider()
    st.info("System Status: Jarvis Voice & Automation Active")

# Session State Initializations
if "messages" not in st.session_state:
    st.session_state.messages = []

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🤖 Command Center")
    
    # Jarvis Speech Web API Script Integration
    st.markdown("""
    <div class="jarvis-card">
        <h4>🎙️ Voice Assistant (Web Speech)</h4>
        <p>Click below and speak: <i>"Play Tum Se Hi on YouTube"</i> or <i>"Send WhatsApp to 91XXXXXXXXXX Message Hello"</i></p>
        <button onclick="startConverting()" style="padding: 10px 20px; background: #66fcf1; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">🔴 Start Voice Command</button>
        <p id="speechResult" style="margin-top: 10px; color: #66fcf1; font-weight: bold;"></p>
    </div>

    <script>
        function startConverting() {
            if('webkitSpeechRecognition' in window) {
                var speechRecognizer = new webkitSpeechRecognition();
                speechRecognizer.continuous = false;
                speechRecognizer.interimResults = false;
                speechRecognizer.lang = 'en-US';
                speechRecognizer.start();

                var speechResult = document.getElementById('speechResult');
                speechResult.innerHTML = "Listening...";

                speechRecognizer.onresult = function(event) {
                    var transcript = event.results[0][0].transcript;
                    speechResult.innerHTML = "Recognized: " + transcript;
                    
                    // Set input value
                    var inputEl = window.parent.document.querySelector('textarea[aria-label="Command X GOD PRO..."]');
                    if(inputEl) {
                        inputEl.value = transcript;
                    }
                };

                speechRecognizer.onerror = function(event) {
                    speechResult.innerHTML = "Error: " + event.error;
                };
            } else {
                alert("Web Speech API not supported in this browser.");
            }
        }
    </script>
    """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Command X GOD PRO...")

with col2:
    st.subheader("🛠️ Action & Workspace Preview")
    
    if selected_mode == "Excel & Data Automation":
        uploaded_excel = st.file_uploader("Upload Excel / CSV File", type=["xlsx", "csv"])
        if uploaded_excel:
            df = pd.read_csv(uploaded_excel) if uploaded_excel.name.endswith('.csv') else pd.read_excel(uploaded_excel)
            st.write("📊 Data Preview:")
            st.dataframe(df.head(10))

    elif selected_mode == "Document Scanner":
        uploaded_doc = st.file_uploader("Upload Document (PDF/TXT)", type=["pdf", "txt"])
        if uploaded_doc and uploaded_doc.name.endswith(".pdf"):
            reader = PdfReader(uploaded_doc)
            st.success(f"PDF Loaded ({len(reader.pages)} Pages)")

# Voice & Intent Action Processing
if user_prompt:
    with col1:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            if not api_key:
                response_text = "⚠️ Gemini API Key enter karein!"
            else:
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    
                    prompt_lower = user_prompt.lower()
                    
                    # 1. YouTube Intent Action
                    if "play" in prompt_lower and "youtube" in prompt_lower:
                        song_name = prompt_lower.replace("play", "").replace("on youtube", "").replace("youtube", "").strip()
                        yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(song_name)}"
                        response_text = f"▶️ Opening YouTube to play: **{song_name}**\n\n[Click here to play on YouTube]({yt_url})"
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={yt_url}">', unsafe_allow_html=True)
                    
                    # 2. WhatsApp Action Trigger
                    elif "whatsapp" in prompt_lower or "send message" in prompt_lower:
                        encoded_msg = urllib.parse.quote(user_prompt)
                        wa_url = f"https://api.whatsapp.com/send?text={encoded_msg}"
                        response_text = f"📲 Directing to WhatsApp to send message:\n\n[Open WhatsApp to Send Message]({wa_url})"
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={wa_url}">', unsafe_allow_html=True)
                    
                    else:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=f"You are Jarvis, an advanced assistant. Respond concisely to: {user_prompt}"
                        )
                        response_text = response.text

                except Exception as e:
                    response_text = f"❌ Error: {str(e)}"

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
