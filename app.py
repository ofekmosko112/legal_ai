import os
import streamlit as st
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

# טעינת משתני הסביבה מקובץ ה-.env המקומי
load_dotenv()

# הגדרת העיצוב והמראה של האפליקציה
st.set_page_config(
    page_title="מנתח החוזים לפרילנסרים",
    page_icon="⚡",
    layout="centered"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    h1 {
        color: #f8fafc;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    div[data-testid="stFileUploader"] {
        border: 2px dashed #38bdf8;
        border-radius: 12px;
        padding: 20px;
        background-color: #1e293b;
    }
    .stButton>button {
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 16px;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        box-shadow: 0 6px 16px rgba(56, 189, 248, 0.5);
        transform: translateY(-1px);
    }
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-left: 1px solid #1f2937;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ LegalAI – מנתח החוזים לחכמים")
st.markdown("### פצח את החוזה שלך בשניות וגלה את כל המלכודות הנסתרות לפני שאתה חותם.")
st.markdown("---")

# שליפת מפתח ה-API ישירות ממשתני הסביבה של השרת
api_key = os.getenv("OPENAI_API_KEY")

# אזור העלאת הקובץ
uploaded_file = st.file_uploader("גרור לכאן את קובץ ה-PDF של החוזה שלך", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("🔄 מנתח את מבנה הקובץ ושולף טקסטים..."):
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                extracted_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
        except Exception as e:
            st.error(f"שגיאה בקריאת הקובץ: {e}")
            extracted_text = ""

    if extracted_text.strip():
        st.success("✅ המסמך נקרא בהצלחה ומוכן לניתוח!")

        if st.button("🚀 הפעל ניתוח סיכונים מתקדם"):
            if not api_key:
                st.error("⚠️ מפתח ה-API לא מוגדר בשרת. בדוק את קובץ ה-.env.")
            else:
                try:
                    client = OpenAI(api_key=api_key)

                    system_prompt = (
                        "אתה עורך דין מומחה וממולח שמייצג אך ורק פרילנסרים ועצמאים בישראל. "
                        "תפקידך לנתח את חוזה העבודה המצורף, לאתר סעיפים בעייתיים (כגון שוטף + אשראי מוגזם, בעלות מלאה וגורפת על קניין רוחני טרם תשלום, קנסות יציאה דרקוניים או סעיפי אי-תחרות מוגזמים). "
                        "עליך להחזיר את התשובה במבנה הבא בדיוק:\n"
                        "1. **ציון סיכון כללי (Risk Score)**: מספר מ-1 עד 10 (כאשר 10 זה מסוכן מאוד).\n"
                        "2. **דגלים אדומים (Red Flags)**: רשימה של הסעיפים הבעייתיים ביותר.\n"
                        "3. **תרגום לעברית מדוברת**: הסבר פשוט וקצר של המשמעות של כל סעיף כזה עבור הפרילנסר.\n"
                        "4. **הצעת ניסוח חלופי (Counter-Offer)**: נוסח הוגן ומקובל שניתן לשלוח חזרה ללקוח."
                    )

                    with st.spinner("🤖 ה-AI סורק את הסעיפים המשפטיים..."):
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"להלן טקסט החוזה לניתוח:\n\n{extracted_text}"}
                            ],
                            temperature=0.2
                        )

                        analysis_result = response.choices[0].message.content

                    st.markdown("---")
                    st.subheader("📊 דוח ניתוח משפטי:")
                    st.markdown(analysis_result)

                except Exception as e:
                    st.error(f"שגיאה בתקשורת מול ה-AI: {e}")
    else:
        st.warning("לא זוהה טקסט בקובץ.")