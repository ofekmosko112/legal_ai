import io
import os
import pdfplumber
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# טעינת מפתח ה-API (תומך גם ב-Streamlit Secrets וגם בקובץ .env מקומי)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

client = OpenAI(api_key=api_key)

st.set_page_config(
    page_title="Legal AI Pro - מערכת מתקדמת לניתוח מסמכים",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ Legal AI Pro - מערכת משפטית חכמה")
st.write(
    "העלה מסמכים משפטיים, בצע ניתוח מעמיק, חלץ טבלאות, נהל שיחת המשך והפק"
    " דוחות מקצועיים."
)

# Sidebar - הגדרות ותפעול
with st.sidebar:
    st.header("הגדרות מערכת")
    model_choice = st.selectbox(
        "בחר מנון AI:", ["gpt-4o", "gpt-4o-mini"], index=0
    )
    temperature = st.slider("רמת יצירתיות (Temperature)", 0.0, 1.0, 0.1, 0.1)

    st.markdown("---")
    st.info("💡 טיפ: ניתן להעלות במסמך מספר חוזים או נספחים במקביל.")


# פונקציית חילוץ טקסט וטבלאות מ-PDF דרך pdfplumber
def extract_text_and_tables_from_pdf(uploaded_file):
    text_content = ""
    tables_content = []
    with pdfplumber.open(uploaded_file) as pdf:
        for i, page in enumerate(pdf.pages):
            extracted = page.extract_text()
            if extracted:
                text_content += f"\n--- עמוד {i + 1} ---\n" + extracted

            # חילוץ טבלאות מהעמוד אם קיימות
            tables = page.extract_tables()
            if tables:
                for t_idx, table in enumerate(tables):
                    tables_content.append(f"טבלה {t_idx + 1} בעמוד {i + 1}:")
                    for row in table:
                        tables_content.append(" | ".join([str(cell) if cell else "" for cell in row]))

    return text_content, "\n".join(tables_content)


# פונקציית יצירת PDF להורדה
def create_pdf_report(report_text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # הגדרות כתיבה בסיסיות (עבור טקסט בעברית מומלץ לוודא פונט תומך, נשתמש בבסיס ונחלק לשורות)
    text_object = c.beginText(40, height - 40)
    text_object.setFont("Helvetica", 10)

    for line in report_text.split("\n"):
        if text_object.getY() < 40:
            c.drawText(text_object)
            c.showPage()
            text_object = c.beginText(40, height - 40)
            text_object.setFont("Helvetica", 10)
        text_object.textLine(line[:100])  # חיתוך שורות ארוכות מדי למניעת חריגה

    c.drawText(text_object)
    c.save()
    buffer.seek(0)
    return buffer


# אזור העלאת קבצים ראשי
uploaded_files = st.file_uploader(
    "העלה קבצי PDF משפטיים:", type=["pdf"], accept_multiple_files=True
)

if uploaded_files:
    all_documents_text = ""
    all_tables_text = ""

    with st.spinner("מחלץ טקסט ונתונים מן המסמכים..."):
        for file in uploaded_files:
            file_text, file_tables = extract_text_and_tables_from_pdf(file)
            all_documents_text += f"\n\n=== קובץ: {file.name} ===\n" + file_text
            if file_tables:
                all_tables_text += f"\n\n=== טבלאות מתוך: {file.name} ===\n" + file_tables

    # יצירת טאבים מתוחכמים
    tab1, tab2, tab3 = st.tabs(["📋 ניתוח וסיכום כללי", "📊 טבלאות ונתונים חצולים", "💬 שיחה חופשית (Chat)"])

    with tab1:
        st.subheader("סיכום משפטי מקיף")
        if st.button("הפק ניתוח אוטומטי למסמכים", type="primary"):
            with st.spinner("הבינה המלאכותית מנתחת את ההסכמים..."):
                prompt = f"""
        אתה עורך דין מומחה ויועץ משפטי בכיר. נתח את המסמכים הבאים ביסודיות רבה.
        הצג:
        1. תקציר מנהלים של ההסכמים.
        2. זכויות וחובות מרכזיות של הצדדים.
        3. סעיפים בעייתיים, סיכונים משפטיים או פרצות אפשריות.
        4. המלצות לתיקון או שיפור ההגנה המשפטית.

        הנה תוכן המסמכים:
        {all_documents_text}
        """
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                analysis_result = response.choices[0].message.content
                st.session_state["last_analysis"] = analysis_result
                st.markdown(analysis_result)

        # הצגת כפתור הורדה אם יש תוצאה קיימת
        if "last_analysis" in st.session_state:
            pdf_buffer = create_pdf_report(st.session_state["last_analysis"])
            st.download_button(
                label="📥 הורד את הדוח המלא כקובץ PDF",
                data=pdf_buffer,
                file_name="legal_analysis_report.pdf",
                mime="application/pdf",
            )

    with tab2:
        st.subheader("נתונים וטבלאות שחולצו מן הקבצים")
        if all_tables_text:
            st.text_area("טבלאות גולמיות שאותרו במסמך:", all_tables_text, height=350)
        else:
            st.info("לא נמצאו טבלאות מובנות (מודפסות) במסמכים אלו, אך הטקסט הרגיל מנותח במלואו.")

    with tab3:
        st.subheader("שאלות המשך על המסמכים (Chat)")

        # אתחול היסטוריית צ'אט
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # הצגת הודעות קודמות
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # קלט משתמש חדש
        if user_query := st.chat_input("שאל משהו על החוזים (למשל: מה קורה במקרה של הפרה?)..."):
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                with st.spinner("מעבד תשובה..."):
                    system_prompt = f"הינך עוזר משפטי חכם. ענה על שאלות המשתמש בהתסמך אך ורק על המסמכים הבאים:\n\n{all_documents_text}"

                    messages_history = [{"role": "system", "content": system_prompt}] + [
                        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
                    ]

                    response = client.chat.completions.create(
                        model=model_choice,
                        messages=messages_history,
                        temperature=temperature,
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

else:
    st.warning("אנא העלה לפחות קובץ PDF אחד באמצעות כפתור ההעלאה למעלה כדי להתחיל.")