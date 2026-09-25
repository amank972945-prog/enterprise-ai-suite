import streamlit as st
import os
import re
import io
import sys
import google.generativeai as genai
from pypdf import PdfReader

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

# Code Extraction & Execution Sandbox
def extract_python_code(text):
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else None

def execute_python_code(code):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    exec_error = None
    try:
        exec(code, {})
    except Exception as e:
        exec_error = str(e)
    finally:
        sys.stdout = old_stdout
    return redirected_output.getvalue(), exec_error

# Speech Output (Browser Voice API)
def speak_text(text):
    clean_text = re.sub(r'[*_#`]', '', text).replace('"', "'").replace('\n', ' ')[:400]
    js_code = f"""
        <script>
            window.speechSynthesis.cancel();
            var msg = new SpeechSynthesisUtterance("{clean_text}");
            window.speechSynthesis.speak(msg);
        </script>
    """
    st.components.v1.html(js_code, height=0)

# Authentication
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

# Sidebar
st.sidebar.title(f"👤 User: {st.session_state['username']}")
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Settings")
target_language = st.sidebar.selectbox("Response Language", ["English", "Hindi", "Hinglish", "Marathi", "Spanish", "French", "German"])
enable_voice = st.sidebar.checkbox("🔊 Enable Voice Output", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Document Scanner")
uploaded_file = st.sidebar.file_uploader("Upload Document (PDF, TXT, MD)", type=["pdf", "txt", "md"])

scanned_doc_text = ""
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    scanned_doc_text += text + "\n"
            st.sidebar.success(f"PDF Scanned! ({len(reader.pages)} Pages)")
        else:
            scanned_doc_text = uploaded_file.read().decode("utf-8")
            st.sidebar.success("Document Attached!")
    except Exception as e:
        st.sidebar.error(f"File Read Error: {e}")

# Main Chat + Live Code Sandbox
st.title("🤖 Enterprise AI Suite Pro")
chat_col, artifact_col = st.columns([2, 1])

with chat_col:
    st.markdown("### 💬 Executive Assistant Chat")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a question, analyze doc, or generate Python code...")

    if prompt:
        if not GEMINI_API_KEY:
            st.error("Gemini API Key missing! Set GEMINI_API_KEY in Streamlit Secrets.")[span_4](start_span)[span_4](end_span)
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    genai.configure(api_key=GEMINI_API_KEY.strip())
                    
                    # Updated supported model names list to prevent 404 errors
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash')
                    except Exception:
                        model = genai.GenerativeModel('gemini-2.5-flash')

                    full_prompt = f"System Instruction: Respond in {target_language}.\n"
                    if scanned_doc_text:
                        full_prompt += f"Document Context:\n{scanned_doc_text[:12000]}\n\n"
                    full_prompt += f"User Query: {prompt}"

                    response = model.generate_content(full_prompt)
                    full_response = response.text

                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                    if enable_voice:
                        speak_text(full_response)

                    code_found = extract_python_code(full_response)
                    if code_found:
                        st.session_state["active_artifact"] = code_found
                        st.rerun()

                except Exception as e:
                    st.error(f"API Error: {e}")

with artifact_col:
    st.markdown("### 🛠️ Live Code Sandbox")
    if st.session_state.get("active_artifact"):
        curr_code = st.session_state["active_artifact"]
        edited_code = st.text_area("Python Interactive Editor", value=curr_code, height=320, key="editor_area")
        if st.button("▶️ Run Code", type="primary"):
            out_res, err_res = execute_python_code(edited_code)
            if err_res:
                st.error(f"Execution Error: {err_res}")
            else:
                st.success("Execution Output:")
                st.code(out_res if out_res else "Code executed successfully with no print output.")
