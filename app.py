import hashlib
import io
import re
import time
from datetime import datetime, timedelta
import pandas as pd
import pdfplumber
import streamlit as st
from docx import Document
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from ics import Calendar, Event
import openpyxl

st.set_page_config(
    page_title="Enterprise Legal AI Pro - Ultimate Edition",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# אתחול Session State
if "user_plan" not in st.session_state: st.session_state.user_plan = "Free"
if "free_docs_used" not in st.session_state: st.session_state.free_docs_used = 1
if "pro_docs_used" not in st.session_state: st.session_state.pro_docs_used = 5
if "audit_trail" not in st.session_state: st.session_state.audit_trail = []
if "team_comments" not in st.session_state: st.session_state.team_comments = []

with st.sidebar:
    st.title("🛡️ Legal AI Executive")
    st.markdown(f"**מסלול:** `{'Pro' if st.session_state.user_plan == 'Pro' else 'Free'}`")
    
    st.subheader("⚙️ מנוע עיבוד (LLM)")
    engine_mode = st.radio("בחר תשתית:", ["ענן (OpenAI Cloud API)", "מקומי (Ollama)"])
    
    if "מקומי" in engine_mode:
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        actual_model = "llama3"
    else:
        # מפתח מוטמע ישירות למניעת שגיאות ענן
        client = OpenAI(api_key="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")
        actual_model = "gpt-4o"
        st.caption("☁️ מחובר ל-OpenAI API")

st.title("⚖️ Legal AI Pro - Executive Suite")
st.write("מערכת משפטית ארגונית פועלת בהצלחה.")

uploaded_files = st.file_uploader("העלה מסמכים (PDF, DOCX):", type=["pdf", "docx"], accept_multiple_files=True)

if uploaded_files:
    all_text = ""
    for file in uploaded_files:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: all_text += t + "\n"
                
    st.success(, f"הקבצים נטענו בהצלחה! סך הכל תווים: {len(all_text)})
    if st.button("הפק ניתוח מהיר"):
        resp = client.chat.completions.create(
            model=actual_model,
            messages=[{"role": "user", "content": f"נתח את החוזה הבא בתמציתיות: {all_text[:3000]}"}]
        )
        st.markdown(resp.choices[0].message.content)
else:
    st.warning("אנא העלה קבצים כדי להתחיל.")
