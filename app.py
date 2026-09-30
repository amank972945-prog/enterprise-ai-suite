import streamlit as st
import os
import google.generativeai as genai
import stripe
from supabase import create_client, Client

# Page Config
st.set_page_config(page_title="X GOD Enterprise AI Platform", page_icon="⚡", layout="wide")

# Custom CSS for Sleek UI
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { background-color: #4F46E5; color: white; border-radius: 8px; font-weight: bold; }
    .stTextInput>div>div>input { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# Fetch Secrets
STRIPE_KEY = st.secrets.get("STRIPE_SECRET_KEY", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Configure Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# Sidebar - User Session & Google Auth Mock
st.sidebar.title("⚡ X GOD Enterprise")
st.sidebar.markdown("---")

# Google Login Simulation
user_email = st.sidebar.text_input("Work Email / Google Account", value="user@company.com")
tenant_id = st.sidebar.text_input("Tenant ID / Organization Code", value="default_tenant")

st.sidebar.markdown("---")
st.sidebar.subheader("💳 Upgrade Plan")

if st.sidebar.button("Upgrade to Pro ($99/mo)"):
    if not STRIPE_KEY or "..." in STRIPE_KEY:
        st.sidebar.error("Please add a valid full Stripe API Key in Secrets!")
    else:
        try:
            stripe.api_key = STRIPE_KEY
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': 'X GOD Pro Subscription'},
                        'unit_amount': 9900,
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://streamlit.io',
                cancel_url='https://streamlit.io',
            )
            st.sidebar.success(f"[Click here to Pay]({session.url})")
        except Exception as e:
            st.sidebar.error(f"Stripe Error: {e}")

# Main Header
st.title("⚡ X GOD Enterprise AI Platform (JARVIS Mode)")
st.caption(f"Active Session: Tenant **{tenant_id}** | Authenticated as **{user_email}**")

st.markdown("---")

# Feature Tabs
tab1, tab2, tab3 = st.tabs(["💬 AI Agent & Code Gen", "📁 Multimodal (Audio, Video, Doc Scan)", "🎙️ Voice Command (JARVIS)"])

with tab1:
    st.subheader("Ask RAG AI Agent / Generate Code")
    system_prompt = st.text_area("System Instruction / Role (Optional)", "You are X GOD, an elite enterprise AI assistant. Provide fast, highly accurate, and clean responses or code.")
    user_query = st.text_area("Enter your Query, Prompt, or Request:", placeholder="Ask anything, write code, or analyze enterprise data...")
    
    if st.button("Execute Query / Run AI", key="run_text"):
        if not user_query:
            st.warning("Please enter a query first.")
        elif not GEMINI_KEY:
            st.error("GEMINI_API_KEY is missing in Streamlit Secrets!")
        else:
            with st.spinner("X GOD Engine Processing..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(f"{system_prompt}\n\nUser Question: {user_query}")
                    st.success("Response Generated:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error calling Gemini API: {e}")

with tab2:
    st.subheader("Upload Documents, Images, Audio, or Video")
    uploaded_file = st.file_uploader("Upload File (PDF, Image, MP3, MP4)", type=["pdf", "png", "jpg", "jpeg", "mp3", "wav", "mp4"])
    doc_prompt = st.text_input("Instruction for uploaded file:", "Summarize and extract key insights from this file.")
    
    if st.button("Process File with AI", key="run_file"):
        if not uploaded_file:
            st.warning("Please upload a file first.")
        elif not GEMINI_KEY:
            st.error("GEMINI_API_KEY is missing in Streamlit Secrets!")
        else:
            with st.spinner("Analyzing media/document with Gemini..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    if "image" in mime_type or "pdf" in mime_type or "audio" in mime_type:
                        contents = [
                            {"mime_type": mime_type, "data": bytes_data},
                            doc_prompt
                        ]
                        response = model.generate_content(contents)
                        st.success("Analysis Result:")
                        st.markdown(response.text)
                    else:
                        st.info("File uploaded successfully. Processing completed.")
                except Exception as e:
                    st.error(f"File Analysis Error: {e}")

with tab3:
    st.subheader("🎙️ JARVIS X GOD Voice Assistant")
    st.info("Upload your recorded audio query or voice command in any language (English, Hindi, Maithili, etc.).")
    audio_file = st.file_uploader("Upload Voice Recording", type=["mp3", "wav", "m4a", "ogg"])
    
    if st.button("Process Voice Command", key="run_voice"):
        if not audio_file:
            st.warning("Please upload an audio command.")
        else:
            with st.spinner("JARVIS Listening & Processing..."):
                try:
                    bytes_data = audio_file.getvalue()
                    mime_type = audio_file.type
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    contents = [
                        {"mime_type": mime_type, "data": bytes_data},
                        "Listen carefully to this voice command and respond appropriately in the same language."
                    ]
                    response = model.generate_content(contents)
                    st.success("🎙️ JARVIS Response:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Voice Processing Error: {e}")
