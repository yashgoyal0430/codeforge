import streamlit as st
import os
import views

# --- Page Configuration ---
st.set_page_config(
    page_title="EmailHunter & Drafter",
    page_icon="📧",
    layout="wide"
)

# --- Sidebar ---
st.sidebar.title("Navigation")
# Added "Email Validator" to the options
app_mode = st.sidebar.radio("Go to", ["Email Permutator & Verifier", "Cold Email Drafter", "Email Validator"])

st.sidebar.divider()
st.sidebar.subheader("LLM Configuration")
llm_provider = st.sidebar.selectbox("Select LLM Provider", ["OpenAI", "Groq"])

selected_model = ""
api_key = None

if llm_provider == "OpenAI":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
    selected_model = st.sidebar.selectbox("Select Model", [
        "gpt-4o", 
        "gpt-4-turbo", 
        "gpt-3.5-turbo"
    ])

elif llm_provider == "Groq":
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        api_key = st.sidebar.text_input("Enter Groq API Key", type="password")
    selected_model = st.sidebar.selectbox("Select Model", [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile", 
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ])

# --- Main App Logic ---
if app_mode == "Email Permutator & Verifier":
    views.render_permutator_verifier()

elif app_mode == "Cold Email Drafter":
    views.render_cold_email_drafter(llm_provider, api_key, selected_model)

elif app_mode == "Email Validator":
    views.render_email_validator()
