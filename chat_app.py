"""
My AI Assistant - Cloud Version (uses Groq API, deployable on Streamlit Cloud)
This version works on mobile/anywhere since the AI runs on Groq's servers, not your device.
Requirements (put these in requirements.txt): streamlit, groq, langchain, langchain-community, chromadb, pypdf
"""

import streamlit as st
import tempfile
import os
import json
import uuid
from groq import Groq

# ---------- CONFIG ----------
MODEL_NAME = "llama-3.1-8b-instant"  # fast, free Groq model. Other option: "llama-3.3-70b-versatile" (smarter, slower)
SYSTEM_PROMPT = "You are a helpful, friendly AI assistant. Respond in the same language the user writes in."
CHATS_FILE = "chat_history.json"

st.set_page_config(page_title="My AI Assistant", page_icon="🤖", layout="wide")

# ---------- GROQ CLIENT (reads API key from Streamlit secrets) ----------
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Groq API key not found. Add GROQ_API_KEY in Streamlit Cloud's Secrets settings.")
    st.stop()

# ---------- LOAD / SAVE CHAT HISTORY ----------
def load_all_chats():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_all_chats(chats):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)

if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats()

if "current_chat_id" not in st.session_state:
    if st.session_state.all_chats:
        st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[-1]
    else:
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
        st.session_state.current_chat_id = new_id

# ---------- SIDEBAR ----------
st.sidebar.title("🤖 My AI Assistant")

if st.sidebar.button("➕ New Chat", use_container_width=True):
    new_id = str(uuid.uuid4())
    st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
    st.session_state.current_chat_id = new_id
    save_all_chats(st.session_state.all_chats)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Chat History")

for chat_id in reversed(list(st.session_state.all_chats.keys())):
    title = st.session_state.all_chats[chat_id]["title"]
    is_active = chat_id == st.session_state.current_chat_id
    label = f"👉 {title}" if is_active else f"💬 {title}"
    if st.sidebar.button(label, key=f"select_{chat_id}", use_container_width=True):
        st.session_state.current_chat_id = chat_id
        st.rerun()

# ---------- MAIN CHAT AREA ----------
current_chat = st.session_state.all_chats[st.session_state.current_chat_id]

st.title("My AI Assistant")
st.caption(f"Cloud-powered by Groq — model: {MODEL_NAME}")

for msg in current_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Message your AI assistant...")

if user_input:
    current_chat["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if current_chat["title"] == "New Chat":
        current_chat["title"] = user_input[:30] + ("..." if len(user_input) > 30 else "")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        # Build message history for context
        groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in current_chat["messages"][-10:]:
            groq_messages.append({"role": m["role"], "content": m["content"]})

        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=groq_messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_response += delta
                placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"Error: {e}"
            placeholder.error(full_response)

    current_chat["messages"].append({"role": "assistant", "content": full_response})
    save_all_chats(st.session_state.all_chats)
