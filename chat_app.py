import streamlit as st
import json
import os
import uuid
import tempfile
import time
import google.generativeai as genai
from supabase import create_client

MODEL_NAME = "gemini-1.5-flash"
FREE_DAILY_MESSAGE_LIMIT = 15
UPGRADE_LINK = "https://rzp.io/l/your-payment-link-here"

st.set_page_config(page_title="Premium AI Assistant", page_icon="✨", layout="wide")

MIC_AVAILABLE = False
SKLEARN_AVAILABLE = False
PDF_AVAILABLE = False
DOCX_AVAILABLE = False

try:
    from streamlit_mic_recorder import mic_recorder
    MIC_AVAILABLE = True
except Exception:
    pass
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    pass
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except Exception:
    pass
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except Exception:
    pass

st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%); }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #16162a 0%, #0f0f1a 100%);
        border-right: 1px solid #2a2a45;
    }
    .stChatMessage { border-radius: 14px; border: 1px solid #2a2a45; }
    .stButton button { border-radius: 10px; border: 1px solid #6c5ce7; }
    .stButton button:hover { border-color: #a29bfe; color: #a29bfe; }
    h1, h2, h3 { color: #e0e0ff; }
    .premium-badge {
        background: linear-gradient(90deg, #6c5ce7, #a29bfe);
        color: white; padding: 4px 14px; border-radius: 20px;
        font-size: 13px; font-weight: 600; display: inline-block;
    }
    .upgrade-box {
        background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
        padding: 16px; border-radius: 14px; color: white; text-align: center;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<span class="premium-badge">✨ PREMIUM ACCESS</span>', unsafe_allow_html=True)
    st.title("Sign in")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        try:
            correct_user = st.secrets["APP_USERNAME"]
            correct_pass = st.secrets["APP_PASSWORD"]
        except Exception:
            st.error("Login not configured. Add APP_USERNAME and APP_PASSWORD in Secrets.")
            st.stop()
        if username == correct_user and password == correct_pass:
            st.session_state.logged_in = True
            st.session_state.user_name = username
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    st.stop()

name = st.session_state.get("user_name", "User")

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(MODEL_NAME)
except Exception:
    st.error("Gemini API key not found. Add GEMINI_API_KEY in Secrets, then Reboot.")
    st.stop()

DB_AVAILABLE = False
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    DB_AVAILABLE = True
except Exception:
    st.sidebar.warning("Persistent history unavailable — check SUPABASE_URL/SUPABASE_KEY in Secrets.")

def load_all_chats():
    if DB_AVAILABLE:
        try:
            res = supabase.table("user_chats").select("data").eq("username", name).execute()
            if res.data:
                return res.data[0]["data"]
            return {}
        except Exception as e:
            st.sidebar.warning(f"Could not load history: {e}")
            return {}
    return {}

def save_all_chats(chats):
    if DB_AVAILABLE:
        try:
            supabase.table("user_chats").upsert({"username": name, "data": chats}).execute()
        except Exception as e:
            st.sidebar.warning(f"Could not save history: {e}")

try:
    IS_PREMIUM_ACCOUNT = st.secrets.get("IS_PREMIUM", "false").lower() == "true"
except Exception:
    IS_PREMIUM_ACCOUNT = False

if "message_count" not in st.session_state:
    st.session_state.message_count = 0

if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats()
if "current_chat_id" not in st.session_state:
    if st.session_state.all_chats:
        st.session_state.current_chat_id = list(st.session_state.all_chats.keys())[-1]
    else:
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
        st.session_state.current_chat_id = new_id
if "doc_chunks" not in st.session_state:
    st.session_state.doc_chunks = []

with st.sidebar:
    badge_text = "👑 PREMIUM" if IS_PREMIUM_ACCOUNT else "✨ FREE PLAN"
    st.markdown(f'<span class="premium-badge">{badge_text}</span>', unsafe_allow_html=True)
    st.title(f"Welcome, {name}")
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")

    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": "New Chat", "messages": []}
        st.session_state.current_chat_id = new_id
        st.session_state.doc_chunks = []
        save_all_chats(st.session_state.all_chats)
        st.rerun()

    st.caption("Chat History")
    for chat_id in reversed(list(st.session_state.all_chats.keys())):
        title = st.session_state.all_chats[chat_id]["title"]
        is_active = chat_id == st.session_state.current_chat_id
        label = f"👉 {title}" if is_active else f"💬 {title}"
        if st.button(label, key=f"select_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()

    st.markdown("---")
    language = st.selectbox(
        "🌐 Reply Language",
        ["Auto-detect", "English", "Hindi", "Hinglish", "Spanish", "French", "Arabic"],
    )
    code_mode = st.toggle("💻 Code Mode (detailed technical answers)")

    st.markdown("---")
    if not IS_PREMIUM_ACCOUNT:
        remaining = max(0, FREE_DAILY_MESSAGE_LIMIT - st.session_state.message_count)
        st.markdown(f"""
        <div class="upgrade-box">
            <b>Free Plan</b><br>
            {remaining} messages left this session<br><br>
            <b>Premium unlocks:</b><br>
            Unlimited messages, priority support
        </div>
        """, unsafe_allow_html=True)
        st.link_button("👑 Upgrade to Premium", UPGRADE_LINK, use_container_width=True)
    else:
        st.markdown("""
        <div class="upgrade-box">👑 <b>Premium Active</b><br>Unlimited messages unlocked</div>
        """, unsafe_allow_html=True)

def extract_text_from_pdf(file_bytes):
    if not PDF_AVAILABLE:
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        path = tmp.name
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    os.unlink(path)
    return text

def extract_text_from_docx(file_bytes):
    if not DOCX_AVAILABLE:
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        path = tmp.name
    doc = DocxDocument(path)
    text = "\n".join(p.text for p in doc.paragraphs)
    os.unlink(path)
    return text

def chunk_text(text, chunk_size=800):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

def find_relevant_chunks(question, chunks, top_k=3):
    if not SKLEARN_AVAILABLE or not chunks:
        return chunks[:top_k]
    vectorizer = TfidfVectorizer().fit(chunks + [question])
    chunk_vecs = vectorizer.transform(chunks)
    q_vec = vectorizer.transform([question])
    scores = cosine_similarity(q_vec, chunk_vecs)[0]
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [c for c, s in ranked[:top_k]]

def upload_to_gemini(file_bytes, suffix, mime_type):
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        path = tmp.name
    gfile = genai.upload_file(path=path, mime_type=mime_type)
    while gfile.state.name == "PROCESSING":
        time.sleep(2)
        gfile = genai.get_file(gfile.name)
    os.unlink(path)
    if gfile.state.name == "FAILED":
        raise Exception("Gemini could not process this file.")
    return gfile

current_chat = st.session_state.all_chats[st.session_state.current_chat_id]
st.title("✨ Premium AI Assistant")
st.caption(f"Powered by Google Gemini — {MODEL_NAME}")

for msg in current_chat["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

limit_reached = (not IS_PREMIUM_ACCOUNT) and (st.session_state.message_count >= FREE_DAILY_MESSAGE_LIMIT)
if limit_reached:
    st.warning("You've used all your free messages for this session. Upgrade to Premium for unlimited access (see sidebar).")

with st.popover("➕ Add", disabled=limit_reached):
    st.caption("Add to your message")

    img_file = st.file_uploader("🖼️ Upload Image", type=["jpg", "jpeg", "png"], key="img_up")
    if img_file:
        st.session_state["_pending_image"] = img_file.getvalue()
        st.success("Image attached — ask your question below.")

    doc_file = st.file_uploader("📄 Upload Document (PDF/DOCX)", type=["pdf", "docx"], key="doc_up")
    if doc_file:
        raw = doc_file.getvalue()
        text = extract_text_from_pdf(raw) if doc_file.name.endswith(".pdf") else extract_text_from_docx(raw)
        if text:
            st.session_state.doc_chunks = chunk_text(text)
            st.success(f"Document indexed ({len(st.session_state.doc_chunks)} sections). Ask questions below.")
        else:
            st.warning("Could not read this document — required library missing.")

    video_file = st.file_uploader("🎬 Upload Video", type=["mp4", "mov", "mkv"], key="vid_up")
    if video_file:
        st.session_state["_pending_video"] = (video_file.getvalue(), video_file.name)
        st.success("Video attached — ask your question below.")

    if MIC_AVAILABLE:
        audio = mic_recorder(start_prompt="🎤 Speak", stop_prompt="⏹ Stop", key="mic_popover")
        if audio:
            st.session_state["_pending_audio"] = audio["bytes"]
            st.success("Voice recorded — ask your question below, or just press send.")
    else:
        st.caption("🎤 Voice input needs streamlit-mic-recorder in requirements.txt")

user_input = st.chat_input("Ask anything...", disabled=limit_reached)

if user_input and not limit_reached:
    st.session_state.message_count += 1
    pending_image = st.session_state.pop("_pending_image", None)
    pending_video = st.session_state.pop("_pending_video", None)
    pending_audio = st.session_state.pop("_pending_audio", None)

    current_chat["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if current_chat["title"] == "New Chat":
        current_chat["title"] = user_input[:30] + ("..." if len(user_input) > 30 else "")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            system_instruction = "You are a premium AI assistant. Give fast, clear, thorough answers."
            if code_mode:
                system_instruction += " Focus on code: give correct, well-commented code with brief explanations."
            if language != "Auto-detect":
                system_instruction += f" Always reply in {language}."
            else:
                system_instruction += " Reply in the same language the user writes in."

            content_parts = [system_instruction, user_input]

            if pending_image:
                from PIL import Image
                import io
                content_parts.append(Image.open(io.BytesIO(pending_image)))

            if pending_video:
                with st.spinner("Processing video (this can take a minute)..."):
                    gfile = upload_to_gemini(pending_video[0], os.path.splitext(pending_video[1])[1] or ".mp4", "video/mp4")
                    content_parts.append(gfile)

            if pending_audio:
                with st.spinner("Processing voice..."):
                    gfile = upload_to_gemini(pending_audio, ".wav", "audio/wav")
                    content_parts.append(gfile)

            if st.session_state.doc_chunks:
                relevant = find_relevant_chunks(user_input, st.session_state.doc_chunks)
                content_parts.append("\n\nRelevant document excerpts:\n" + "\n---\n".join(relevant))

            response = model.generate_content(content_parts, stream=True)
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)

        except Exception as e:
            full_response = f"Error: {e}"
            placeholder.error(full_response)

    current_chat["messages"].append({"role": "assistant", "content": full_response})
    save_all_chats(st.session_state.all_chats)
