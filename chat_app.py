import streamlit as st
import pandas as pd
import datetime
import re
import os
import PyPDF2
from gTTS import gTTS
import base64
from langchain_google_genai import ChatGoogleGenerativeAI

# Page Configuration
st.set_page_config(page_title="Enterprise AI Suite Pro", page_icon="🤖", layout="wide")

# API Key Retrieval
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# Initialize Session States
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "active_artifact" not in st.session_state:
    st.session_state["active_artifact"] = None

# Helper Functions
def extract_python_code(text):
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else None

def execute_python_code(code):
    import sys, io
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    error = None
    try:
        exec(code, {})
    except Exception as e:
        error = str(e)
    finally:
        sys.stdout = old_stdout
    return redirected_output.getvalue(), error

def text_to_audio(text, lang_code='en'):
    try:
        clean_text = re.sub(r'[*_#`]', '', text)[:300]
        tts = gTTS(text=clean_text, lang=lang_code, slow=False)
        tts.save("response.mp3")
        with open("response.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f'<audio autoplay controls><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.markdown(md, unsafe_allow_html=True)
    except Exception:
        pass

# Authentication Logic
if not st.session_state["authenticated"]:
    st.title("🔐 Enterprise AI Suite Login")
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    if st.button("Login"):
        if username_input == "admin" and password_input == "abc":
            st.session_state["authenticated"] = True
            st.session_state["username"] = username_input
            st.rerun()
        else:
            st.error("Invalid credentials! Use admin / abc")
    st.stop()

# Sidebar Layout
st.sidebar.title(f"👤 User: {st.session_state['username']}")
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Settings")
target_language = st.sidebar.selectbox("Response Language", ["English", "Hindi", "Hinglish", "Marathi", "Spanish", "French", "German"])
lang_map = {"English": "en", "Hindi": "hi", "Hinglish": "hi", "Marathi": "mr", "Spanish": "es", "French": "fr", "German": "de"}
enable_voice = st.sidebar.checkbox("🔊 Enable Voice Response", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Document Scanner")
uploaded_file = st.sidebar.file_uploader("Upload PDF or TXT", type=["pdf", "txt", "md"])

scanned_doc_text = ""
if uploaded_file is not None:
    if uploaded_file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            scanned_doc_text += page.extract_text() or ""
        st.sidebar.success(f"PDF Scanned! ({len(pdf_reader.pages)} pages)")
    else:
        scanned_doc_text = uploaded_file.read().decode("utf-8")
        st.sidebar.success("Text File Attached!")

# Main UI Split (Chat + Code Sandbox)
st.title("🤖 Enterprise AI Suite Pro")
chat_col, artifact_col = st.columns([2, 1])

with chat_col:
    st.markdown("### 💬 Executive Assistant Chat")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a question, analyze scanned doc, or request code...")

    if prompt:
        if not GEMINI_API_KEY:
            st.error("Gemini API Key missing! Set GEMINI_API_KEY in Streamlit Secrets.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY, temperature=0.3)
                    if scanned_doc_text:
                        full_prompt = f"System: Respond in {target_language}. Document Context: {scanned_doc_text[:10000]}\nUser: {prompt}"
                    else:
                        full_prompt = f"System: Respond in {target_language}.\nUser: {prompt}"

                    response = llm.invoke(full_prompt)
                    full_response = response.content
                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                    if enable_voice:
                        text_to_audio(full_response, lang_map.get(target_language, 'en'))

                    code_found = extract_python_code(full_response)
                    if code_found:
                        st.session_state["active_artifact"] = code_found
                        st.rerun()
                except Exception as e:
                    st.error(f"API Error: {e}")

with artifact_col:
    st.markdown("### 🛠️ Code Sandbox")
    if st.session_state.get("active_artifact"):
        curr_code = st.session_state["active_artifact"]
        edited_code = st.text_area("Interactive Python Editor", value=curr_code, height=320, key="editor_area")
        if st.button("▶️ Run Code", type="primary"):
            output, error = execute_python_code(edited_code)
            if error:
                st.error(f"Execution Error: {error}")
            else:
                st.success("Output:")
                st.code(output)
