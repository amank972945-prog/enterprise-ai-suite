import streamlit as st
import json
import os
import uuid
import base64
import subprocess
import tempfile

from groq import Groq

CHAT_MODEL = "llama-3.3-70b-versatile"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
WHISPER_MODEL = "whisper-large-v3-turbo"
CHATS_FILE = "chat_history.json"
MAX_TOKENS = 2048
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
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Groq API key not found. Add GROQ_API_KEY in Secrets, then Reboot.")
    st.stop()

try:
    IS_PREMIUM_ACCOUNT = st.secrets.get("IS_PREMIUM", "false").lower() == "true"
except Exception:
    IS_PREMIUM_ACCOUNT = False

if "message_count" not in st.session_state:
    st.session_state.message_count = 0

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
if "doc_chunks" not in st.session_state:
    st.session_state.doc_chunks = []
if "pending_context" not in st.session_state:
    st.session_state.pending_context = ""

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
            Unlimited messages, faster model, priority support
        </div>
        """, unsafe_allow_html=True)
        st.link_button("👑 Upgrade to Premium", UPGRADE_LINK, use_container_width=True)
    else:
        st.markdown("""
        <div class="upgrade-box">
            👑 <b>Premium Active</b><br>
            Unlimited messages unlocked
        </div>
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

def transcribe_audio_bytes(audio_bytes, filename="audio.wav"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1] or ".wav") as tmp:
        tmp.write(audio_bytes)
        path = tmp.name
    with open(path, "rb") as f:
        result = client.audio.transcriptions.create(file=(filename, f.read()), model=WHISPER_MODEL)
    os.unlink(path)
    return result.text

def extract_audio_from_video(video_bytes, filename="video.mp4"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1] or ".mp4") as tmp_vid:
        tmp_vid.write(video_bytes)
        vid_path = tmp_vid.name
    audio_path = vid_path + ".wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", vid_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", audio_path],
        capture_output=True, timeout=120
    )
    os.unlink(vid_path)
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as f:
            data = f.read()
        os.unlink(audio_path)
        return data
    return None

def analyze_image(image_bytes, question):
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": question or "Describe this image in detail."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content

current_chat = st.session_state.all_chats[st.session_state.current_chat_id]
st.title("✨ Premium AI Assistant")
st.caption(f"Fast answers — {CHAT_MODEL}")

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
        text = None
        if doc_file.name.endswith(".pdf"):
            text = extract_text_from_pdf(raw)
        elif doc_file.name.endswith(".docx"):
            text = extract_text_from_docx(raw)
        if text:
            st.session_state.doc_chunks = chunk_text(text)
            st.success(f"Document indexed ({len(st.session_state.doc_chunks)} sections). Ask questions about it below.")
        else:
            st.warning("Could not read this document — required library missing.")

    video_file = st.file_uploader("🎬 Upload Video (audio will be transcribed)", type=["mp4", "mov", "mkv"], key="vid_up")
    if video_file:
        with st.spinner("Extracting and transcribing audio from video..."):
            audio_data = extract_audio_from_video(video_file.getvalue(), video_file.name)
            if audio_data:
                try:
                    transcript = transcribe_audio_bytes(audio_data)
                    st.session_state.pending_context = f"[Video transcript]: {transcript}"
                    st.success("Video transcribed! Ask your question below.")
                except Exception as e:
                    st.warning(f"Transcription failed: {e}")
            else:
                st.warning("Could not extract audio (ffmpeg missing — add 'ffmpeg' to packages.txt).")

    if MIC_AVAILABLE:
        audio = mic_recorder(start_prompt="🎤 Speak", stop_prompt="⏹ Stop", key="mic_popover")
        if audio:
            with st.spinner("Transcribing..."):
                try:
                    text = transcribe_audio_bytes(audio["bytes"])
                    st.session_state["_pending_voice_text"] = text
                    st.info(f"You said: {text}")
                except Exception as e:
                    st.warning(f"Voice transcription failed: {e}")
    else:
        st.caption("🎤 Voice input needs streamlit-mic-recorder in requirements.txt")

text_input = st.chat_input("Ask anything...", disabled=limit_reached)
voice_text = st.session_state.pop("_pending_voice_text", None)
user_input = text_input or voice_text

if user_input and not limit_reached:
    st.session_state.message_count += 1
    pending_image = st.session_state.pop("_pending_image", None)
    extra_context = st.session_state.pop("pending_context", "")

    current_chat["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if current_chat["title"] == "New Chat":
        current_chat["title"] = user_input[:30] + ("..." if len(user_input) > 30 else "")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            if pending_image:
                full_response = analyze_image(pending_image, user_input)
                placeholder.markdown(full_response)
            else:
                system_prompt = "You are a premium AI assistant. Give fast, clear, thorough answers."
                if code_mode:
                    system_prompt += " Focus on code: give correct, well-commented code with brief explanations."
                if language != "Auto-detect":
                    system_prompt += f" Always reply in {language}."
                else:
                    system_prompt += " Reply in the same language the user writes in."

                doc_context = ""
                if st.session_state.doc_chunks:
                    relevant = find_relevant_chunks(user_input, st.session_state.doc_chunks)
                    doc_context = "\n\nRelevant document excerpts:\n" + "\n---\n".join(relevant)

                full_user_message = user_input + doc_context
                if extra_context:
                    full_user_message += f"\n\n{extra_context}"

                groq_messages = [{"role": "system", "content": system_prompt}]
                for m in current_chat["messages"][-10:-1]:
                    groq_messages.append({"role": m["role"], "content": m["content"]})
                groq_messages.append({"role": "user", "content": full_user_message})

                stream = client.chat.completions.create(
                    model=CHAT_MODEL, messages=groq_messages, stream=True, max_tokens=MAX_TOKENS,
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
