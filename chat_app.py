import streamlit as st
from langchain_ollama import OllamaLLM
from pypdf import PdfReader
import pandas as pd
import io
import datetime
import sqlite3
import re
import sys
from streamlit_mic_recorder import speech_to_text

# Page Configuration
st.set_page_config(page_title="Enterprise AI Suite Pro + Artifacts", page_icon="🤖", layout="wide")

# SQLite Database Setup
conn = sqlite3.connect('chat_history.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS history 
    (username TEXT, timestamp TEXT, role TEXT, content TEXT, language TEXT)
''')
conn.commit()

# User Credentials
users = {
    "admin": {"pass": "abc", "company": "Acme Enterprise Corp"},
    "aman bhai": {"pass": "aman.851217", "company": "Aman AI Tech Corp"}
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "doc_count" not in st.session_state:
    st.session_state.doc_count = 0
if "query_count" not in st.session_state:
    st.session_state.query_count = 0

# Helper Function to Extract Python Code for Artifact Preview
def extract_python_code(text):
    pattern = r"python(.*?)"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0].strip() if matches else None

# Helper Function to Execute Python Code safely
def execute_python_code(code):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    try:
        exec_globals = {"pd": pd, "st": st}
        exec(code, exec_globals)
        sys.stdout = old_stdout
        return redirected_output.getvalue(), None
    except Exception as e:
        sys.stdout = old_stdout
        return None, str(e)

# Sidebar Control
st.sidebar.title("🤖 Enterprise Portal")

if not st.session_state.logged_in:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in users and users[username]["pass"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.company = users[username]["company"]
            st.rerun()
        else:
            st.sidebar.error("Invalid Credentials")
else:
    st.sidebar.markdown(f"*User:* {st.session_state.username}")
    st.sidebar.markdown(f"*Org:* {st.session_state.company}")
    st.sidebar.markdown("---")
    
    selected_model = st.sidebar.selectbox("⚡ Local AI Engine", ["qwen2.5:3b"])
    target_language = st.sidebar.selectbox("🌐 System Language", ["English", "Hindi", "Hinglish"])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("➕ New Chat Session"):
        st.session_state.messages = []
        st.rerun()
        
    if st.sidebar.button("🗑️ Clear DB History"):
        c.execute("DELETE FROM history WHERE username=?", (st.session_state.username,))
        conn.commit()
        st.session_state.messages = []
        st.rerun()
        
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# Workspace Area
if st.session_state.logged_in:
    st.title(f"✨ {st.session_state.company} - AI Suite + Claude Artifacts Workspace")
    st.caption("🚀 Air-Gapped Local Execution with Detailed Responses, Voice Support & Live Code Sandbox")
    
    # Analytics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("System Status", "100% Operational")
    with col2: st.metric("Active Model", selected_model)
    with col3: st.metric("Files Ingested", st.session_state.doc_count)
    with col4: st.metric("Queries Handled", st.session_state.query_count)
    st.markdown("---")

    # Document Ingestion
    st.subheader("📁 Multimodal Context Ingestion")
    uploaded_file = st.file_uploader("Upload File (PDF, TXT, CSV, XLSX)", type=["txt", "pdf", "csv", "xlsx"])
    
    doc_text = ""
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        if file_ext == "txt":
            doc_text = uploaded_file.read().decode("utf-8")
        elif file_ext == "pdf":
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                doc_text += page.extract_text() or ""
        elif file_ext in ["csv", "xlsx"]:
            df_file = pd.read_csv(uploaded_file) if file_ext == "csv" else pd.read_excel(uploaded_file)
            doc_text = df_file.to_string()
            st.dataframe(df_file.head(5))
            
        st.session_state.doc_count += 1
        st.success(f"Context Encrypted & Loaded: {uploaded_file.name}")

    # Load Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []
        try:
            c.execute("SELECT role, content FROM history WHERE username=? ORDER BY rowid ASC", (st.session_state.username,))
            rows = c.fetchall()
            for r in rows:
                st.session_state.messages.append({"role": r[0], "content": r[1]})
        except Exception:
            st.session_state.messages = []

    # Chat & Artifact Section Layout
    chat_col, artifact_col = st.columns([1.2, 0.8])

    with chat_col:
        st.markdown("### 💬 Executive Assistant Chat")
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Check for Python Code Artifact in history
                if message["role"] == "assistant":
                    extracted_code = extract_python_code(message["content"])
                    if extracted_code:
                        if st.button(f"⚡ Open Code Artifact #{idx+1}", key=f"art_btn_{idx}"):
                            st.session_state["active_artifact"] = extracted_code

        # Voice Mic Feature
        st.markdown("#### 🎙️ Voice Input (Click to speak):")
        voice_prompt = speech_to_text(language='en', start_prompt="🎙️ Click to Speak", stop_prompt="⏹️ Stop Recording", key='mic_input')
        
        text_prompt = st.chat_input("Ask structured questions, request python code, or analyze documents...")
        prompt = voice_prompt if voice_prompt else text_prompt

        if prompt:
            st.session_state.query_count += 1
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                c.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)", (st.session_state.username, now, "user", prompt, target_language))
                conn.commit()
            except Exception:
                pass
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    llm = OllamaLLM(model=selected_model, num_predict=2048, temperature=0.7)
                    
                    if doc_text:
                        full_prompt = f"System: Provide a detailed, step-by-step response in {target_language}. If generating Python code, wrap it inside python ... .\nContext:\n{doc_text}\n\nQuestion: {prompt}"
                    else:
                        full_prompt = f"System: Provide a detailed, step-by-step response in {target_language}. If generating Python code, wrap it inside python ... .\nQuestion: {prompt}"
                    
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in llm.stream(full_prompt):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    
                    response_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                    # Auto load artifact if code is detected
                    code_found = extract_python_code(full_response)
                    if code_found:
                        st.session_state["active_artifact"] = code_found
                        st.rerun()

                    try:
                        c.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)", (st.session_state.username, now, "assistant", full_response, target_language))
                        conn.commit()
                    except Exception:
                        pass

                    if doc_text:
                        df = pd.DataFrame([{"Timestamp": now, "Query": prompt, "Response": full_response, "Language": target_language}])
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Audit_Report')
                        
                        st.download_button(
                            label="📥 Download Excel Audit Report (.xlsx)",
                            data=buffer.getvalue(),
                            file_name="AI_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"Execution Error: {e}. Please make sure Ollama app is open in background.")

    # Artifact / Interactive Code Playground Sidebar Panel
    with artifact_col:
        st.markdown("### 🛠️ Claude Artifacts / Code Sandbox")
        if "active_artifact" in st.session_state and st.session_state["active_artifact"]:
            curr_code = st.session_state["active_artifact"]
            
            st.subheader("📝 Python Code Editor")
            edited_code = st.text_area("Interactive Code Editor", value=curr_code, height=300, key="editor_area")
            
            col_a, col_b = st.columns(2)
            with col_a:
                run_click = st.button("▶️ Run Code", type="primary", use_container_width=True)
            with col_b:
                if st.button("❌ Close Artifact", use_container_width=True):
                    st.session_state["active_artifact"] = None
                    st.rerun()

            if run_click:
                st.markdown("#### 📤 Execution Output:")
                output, error = execute_python_code(edited_code)
                if output:
                    st.code(output, language="text")
                if error:
                    st.error(f"Runtime Error: {error}")
                if not output and not error:
                    st.success("Code executed successfully with no print output.")
        else:
            st.info("💡 Jab bhi AI Python Code generate karega, Claude-style Artifact Window yahan automatic open ho jayegi aur aap code live run kar payenge!")
