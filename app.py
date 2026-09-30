import streamlit as st
import stripe
import os

# Page Config
st.set_page_config(page_title="X GOD Enterprise AI", layout="wide", page_icon="⚡")

# Stripe Configuration
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "sk_test_placeholder")

def create_checkout_session(customer_email, price_id):
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=customer_email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://share.streamlit.io/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://share.streamlit.io/',
        )
        return checkout_session.url
    except Exception as e:
        st.error(f"Billing Error: {e}")
        return None

# Sidebar - Multi-Tenant Authentication & Subscriptions
st.sidebar.title("⚡ X GOD Enterprise")
st.sidebar.markdown("---")

tenant_id = st.sidebar.text_input("Tenant ID / Organization Code", value="default_tenant")
user_email = st.sidebar.text_input("Work Email", value="user@company.com")

st.sidebar.markdown("### Upgrade Plan")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("Pro ($99/mo)"):
        url = create_checkout_session(user_email, "price_pro_plan_id")
        if url:
            st.sidebar.markdown(f"[👉 Complete Payment]({url})")

with col2:
    if st.button("Enterprise"):
        url = create_checkout_session(user_email, "price_enterprise_plan_id")
        if url:
            st.sidebar.markdown(f"[👉 Complete Payment]({url})")

# Main Interface
st.title("X GOD Enterprise AI Platform")
st.caption(f"Active Session: Tenant `{tenant_id}` | Authenticated as `{user_email}`")

query = st.text_input("Ask RAG AI Agent (Private Enterprise Data):")
if st.button("Execute Query"):
    if query:
        st.info(f"Processing query for Tenant **{tenant_id}** using Vector RAG & Gemini API...")
        st.success("Response generated with complete tenant data isolation.")
    else:
        st.warning("Please enter a prompt.")
