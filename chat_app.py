import streamlit as st
import pandas as pd
import datetime
import re
from langchain_google_genai import ChatGoogleGenerativeAI

# App Configuration
st.set_page_config(
    page_title="Enterprise AI Suite",
    page_icon="🤖",
    layout="wide"
)

# = Replace with your actual Gemini API Ke "AQ.Ab8RN6Jt4vly2R6HFn8Doxq02oyxR1JKqjttD7SIUz2c6gkIQ"
Starts with AIzaSy...)
GEMINI_API_KEY = "AQ.Ab8RN6Jt4vly2R6HFn8Doxq02oyxR1JKqjttD7SIUz2c6gkIQ


# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "query_count" not in st.session_state:
    st.session_state["query_count"] = 0
if "active_artifact" not in st.session_state:
    st.session_state["active_artifact"] = None

def extract_python_code(text):
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else None

def execute_python_code(code):
    import sys
    import io
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

# Login Logic
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
target_language = st.sidebar.selectbox("Response Language", ["English", "Hindi", "Hinglish", "Marathi"])
uploaded_doc = st.sidebar.file_uploader("Upload Context Document (.txt, .md)", type=["txt", "md"])

doc_text = ""
if uploaded_doc is not None:
    doc_text = uploaded_doc.read().decode("utf-8")
    st.sidebar.success("Document attached!")

# Main App
st.title("🤖 Enterprise AI Suite")

chat_col, artifact_col = st.columns([2, 1])

with chat_col:
    st.markdown("### 💬 Executive Assistant Chat")
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask structured questions or request python code...")

    if prompt:
        st.session_state.query_count += 1
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=GEMINI_API_KEY
                )
                
                if doc_text:
                    full_prompt = f"System: Provide response in {target_language}. Context: {doc_text}\nUser: {prompt}"
                else:
                    full_prompt = f"System: Provide response in {target_language}.\nUser: {prompt}"

                response = llm.invoke(full_prompt)
                full_response = response.content
                
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

                code_found = extract_python_code(full_response)
                if code_found:
                    st.session_state["active_artifact"] = code_found
                    st.rerun()

            except Exception as e:
                st.error(f"API Error: {e}")

with artifact_col:
    st.markdown("### 🛠️ Code Sandbox")
    if "active_artifact" in st.session_state and st.session_state["active_artifact"]:
        curr_code = st.session_state["active_artifact"]
        edited_code = st.text_area("Interactive Code Editor", value=curr_code, height=300, key="editor_area")
        
        if st.button("▶️ Run Code", type="primary"):
            output, error = execute_python_code(edited_code)
            if error:
                st.error(f"Error: {error}")
            else:
                st.success("Execution Output:")
                st.code(output)
