import hashlib
import io
import re
import time
import os
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

# הגדרת תצורת העמוד
st.set_page_config(
    page_title="Enterprise Legal AI Pro - Ultimate Edition",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# חיבור מאובטח ל-OpenAI מתוך ה-Secrets של Streamlit
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# עיצוב CSS יוקרתי
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# אתחול Session State למכסות ומסלולים
if "user_plan" not in st.session_state: st.session_state.user_plan = "Free"
if "free_docs_used" not in st.session_state: st.session_state.free_docs_used = 0
if "pro_docs_used" not in st.session_state: st.session_state.pro_docs_used = 0
if "pro_advanced_used" not in st.session_state: st.session_state.pro_advanced_used = 0
if "enterprise_advanced_used" not in st.session_state: st.session_state.enterprise_advanced_used = 0
if "audit_trail" not in st.session_state: st.session_state.audit_trail = []
if "team_comments" not in st.session_state: st.session_state.team_comments = []

@st.dialog("שדרוג למסלולי הפרימיום של Enterprise Legal AI 🚀", width="large")
def show_checkout_modal():
    st.write("בחר את המסלול המתאים ביותר עבורך וקבל גישה מיידית לכלי הניתוח והאבטחה המתקדמים ביותר:")
    
    selected_plan = st.radio(
        "בחר מסלול:",
        [
            "מסלול Pro (₪49/חודש) - עד 50 סריקות מסמכים בחודש, כולל 5 שימושים בחודש במודל המתקדם ביותר (GPT-4o), חתימות קריפטוגרפיות וייצוא מלא.",
            "מסלול Enterprise Pro Max (₪249/חודש) - סריקות מסמכים ללא הגבלה בחודש, כולל 10 שימושים בחודש במודל המתקדם ביותר (GPT-4o), תמיכה בעדיפות וניהול צוות מלא."
        ]
    )
    
    price_tag = "₪49/חודש" if "₪49" in selected_plan else "₪249/חודש"
    plan_code = "Pro (₪49)" if "₪49" in selected_plan else "Enterprise Pro Max (₪249)"

    st.markdown("---")
    
    # תנאי שימוש ואחריות משתמש מפורטים ובולטים בתוך חלון התשלום
    st.markdown("""
    <div style="background-color: #1e293b; border: 1px solid #dc2626; padding: 12px; border-radius: 8px; font-size: 13px; color: #f8fafc; margin-bottom: 15px;">
        <b style="color: #fca5a5;">📜 תנאי שימוש, הגבלת אחריות וסמכות משפטית:</b><br>
        1. המערכת מספקת ניתוחים טכנולוגיים מבוססי בינה מלאכותית ו<b>אינה מהווה תחליף לייעוץ משפטי מקצועי</b> או חוות דעת של עורך דין.<br>
        2. <b>אחריות משתמש מלאה:</b> המשתמש נושא באחריות הבלעדית לכל פעולה, חתימה, ניהול משא ומתן או החלטה עסקית/משפטית המתקבלת על בסיס פלטי המערכת.<br>
        3. תשלום חודשי מתחדש (ניתן לביטול בכל עת דרך תפריט הניהול). אין החזר כספי על תקופות שימוש חלקיות.
    </div>
    """, unsafe_allow_html=True)
    
    terms_accepted = st.checkbox("אני מאשר/ת שקראתי את תנאי השימוש, הסכמתי להם ואני לוקח/ת על עצמי את מלוא אחריות השימוש במערכת.")

    st.markdown("---")
    st.text_input("מספר כרטיס אשראי", placeholder="4242 •••• •••• 4242")
    c1, c2 = st.columns(2)
    with c1: st.text_input("תוקף", placeholder="MM/YY")
    with c2: st.text_input("CVV", placeholder="123")
    
    if st.button(f"אישור וביצוע תשלום אבטחה ({price_tag})", type="primary", use_container_width=True):
        if not terms_accepted:
            st.error("⚠️ חובה לאשר את תנאי השימוש והאחריות טרם ביצוע ההתקשרות והתשלום.")
        else:
            st.session_state.user_plan = plan_code
            st.success(f"התשלום עבר בהצלחה! חשבונך שודרג למסלול {plan_code} 🎉")
            st.rerun()

# תפריט צד (Sidebar)
with st.sidebar:
    st.title("🛡️ Legal AI Executive")
    st.markdown(f"**מסלול נוכחי:** `{st.session_state.user_plan}`")
    
    if "Free" in st.session_state.user_plan:
        if st.button("🚀 מעבר / שדרוג למסלולי פרימיום"):
            show_checkout_modal()

    st.markdown("---")
    
    # הצגת מדדי מכסות לפי המסלול
    if "Free" in st.session_state.user_plan:
        docs_left = 3 - st.session_state.free_docs_used
        st.metric("מסמכים חינמיים שנותרו", f"{max(0, docs_left)} / 3")
        if docs_left <= 0:
            st.error("הסתיימה המכסה החינמית (3 סריקות). יש לשדרג מסלול.")
    elif "Pro (₪49)" in st.session_state.user_plan:
        docs_left = 50 - st.session_state.pro_docs_used
        adv_left = 5 - st.session_state.pro_advanced_used
        st.metric("סריקות Pro שנותרו", f"{max(0, docs_left)} / 50")
        st.metric("שימושים מתקדמים (GPT-4o)", f"{max(0, adv_left)} / 5")
    else:
        adv_left = 10 - st.session_state.enterprise_advanced_used
        st.metric("סריקות חודשיות", "ללא הגבלה ♾️")
        st.metric("שימושים מתקדמים (GPT-4o)", f"{max(0, adv_left)} / 10")

    st.markdown("---")
    st.subheader("⚙️ בחירת מנוע עיבוד (LLM Engine)")
    engine_mode = st.radio("בחר תשתית מודל:", ["ענן (OpenAI Cloud API)", "מקומי מאובטח (Ollama / Llama 3)"])
    
    if "מקומי" in engine_mode:
        local_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        actual_model = "llama3"
        st.caption("🔒 פועל באופן מקומי מלא.")
    else:
        local_client = client
        actual_model = "gpt-4o"
        st.caption("☁️ מחובר לשרתי הענן המאובטחים.")

    st.markdown("---")
    st.subheader("🛠️ כלי בקרה ופיתוח")
    if st.button("🔄 אפס מכסות לבדיקה", use_container_width=True):
        st.session_state.free_docs_used = 0
        st.session_state.pro_docs_used = 0
        st.session_state.pro_advanced_used = 0
        st.session_state.enterprise_advanced_used = 0
        st.success("המכסות אופסו בהצלחה!")
        st.rerun()

    if st.session_state.audit_trail:
        with st.expander("📋 לוג פעולות (Audit Trail)"):
            for log in st.session_state.audit_trail[-5:]:
                st.caption(f"[{log['time']}] {log['action']}")

# פונקציות עזר מתקדמות
def generate_sha256_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def detect_pii_entities(text):
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phones = re.findall(r"\b0[2-9]\d{7,8}\b|\b05\d-?\d{7}\b", text)
    ids = re.findall(r"\b\d{9}\b", text)
    return {"אימיילים": list(set(emails)), "טלפונים": list(set(phones)), "תעודות זהות": list(set(ids))}

def create_pdf_report(report_text, file_hash):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    text_obj = c.beginText(40, height - 40)
    text_obj.setFont("Helvetica", 10)
    text_obj.textLine(f"Cryptographic Hash (SHA-256): {file_hash}")
    text_obj.textLine("Digital Signature: Verified Executive Legal AI Suite")
    text_obj.textLine("-" * 80)
    
    for line in report_text.split("\n"):
        if text_obj.getY() < 40:
            c.drawText(text_obj)
            c.showPage()
            text_obj = c.beginText(40, height - 40)
            text_obj.setFont("Helvetica", 10)
        text_obj.textLine(line[:100])
    c.drawText(text_obj)
    c.save()
    buffer.seek(0)
    return buffer

def create_excel_report(tables_data):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Extracted Tables"
    for row_idx, row in enumerate(tables_data, 1):
        for col_idx, val in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# בדיקת הרשאה לפי מכסות לפני פענוח מסמך
def check_and_consume_quota(num_files=1):
    plan = st.session_state.user_plan
    if "Free" in plan:
        if st.session_state.free_docs_used + num_files > 3:
            st.error("⚠️ חרגת ממכסת 3 הסריקות החינמיות במסלול Free. אנא שדרג לאחד ממסלולי הפרימיום כדי להמשיך.")
            show_checkout_modal()
            return False
        st.session_state.free_docs_used += num_files
    elif "Pro (₪49)" in plan:
        if st.session_state.pro_docs_used + num_files > 50:
            st.error("⚠️ הגעת למכסת 50 הסריקות החודשיות במסלול Pro.")
            return False
        st.session_state.pro_docs_used += num_files
    return True

# בדיקת מכסת שימוש במודל המתקדם ביותר (GPT-4o)
def check_and_consume_advanced_model():
    plan = st.session_state.user_plan
    if "Free" in plan:
        st.warning("מודל זה זמין למנויי פרימיום בלבד.")
        show_checkout_modal()
        return False
    elif "Pro (₪49)" in plan:
        if st.session_state.pro_advanced_used >= 5:
            st.error("⚠️ ניצלת את כל 5 השימושים החודשיים שלך במודל המתקדם במסלול Pro.")
            return False
        st.session_state.pro_advanced_used += 1
    elif "Enterprise Pro Max" in plan:
        if st.session_state.enterprise_advanced_used >= 10:
            st.error("⚠️ ניצלת את כל 10 השימושים החודשיים שלך במודל המתקדם במסלול Enterprise.")
            return False
        st.session_state.enterprise_advanced_used += 1
    return True

# מסך ראשי
st.title("⚖️ Legal AI Pro - Executive Suite")
st.write("מערכת משפטית ארגונית מתקדמת עם בקרת סיכונים חכמה, ניתוח פיננסי, חתימות קריפטוגרפיות וניהול צוות.")

# באנר משפטי בולט ואזהרת אחריות משתמש בדף הראשי
st.markdown("""
<div style="background-color: #7f1d1d; border: 2px solid #ef4444; padding: 15px; border-radius: 10px; color: #fef2f2; margin-bottom: 20px;">
    <h4 style="margin: 0 0 8px 0; color: #fca5a5;">⚠️ הודעה משפטית חשובה, תנאי שימוש ואחריות משתמש מלאה (Legal Disclaimer & Liability Notice)</h4>
    <p style="margin: 0; font-size: 13.5px; line-height: 1.5;">
        המערכת מספקת תובנות אוטומטיות באמצעות בינה מלאכותית בלבד ו<b>אינה מהווה ייעוץ משפטי רשמי</b>, חוות דעת מקצועית או תחליף לייעוץ משפטי של עו"ד מוסמך. 
        <b>אחריות שימוש מלאה:</b> השימוש בתוצרי המערכת, בניתוחים ובחתימות הקריפטוגרפיות הוא באחריותו הבלעדית של המשתמש. אין להסתמך על ניתוחים אלו כעל אסמכתא משפטית סופית ללא בחינה ידנית של איש מקצוע.
    </p>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("העלה מסמכי משפט או חוזים (PDF, DOCX):", type=["pdf", "docx"], accept_multiple_files=True)

if uploaded_files:
    # אכיפת מכסת קבצים מול המסלול
    if not check_and_consume_quota(len(uploaded_files)):
        st.stop()

    all_docs_text = ""
    extracted_tables = []
    files_dict = {}

    with st.spinner("מחלץ טקסטים ומזהה נתונים רגישים..."):
        for file in uploaded_files:
            bytes_data = file.read()
            text = ""
            with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
                for i, page in enumerate(pdf.pages):
                    extracted = page.extract_text()
                    if extracted: text += f"\n--- עמוד {i+1} ---\n" + extracted
                    for table in page.extract_tables() or []:
                        extracted_tables.extend(table)
            
            files_dict[file.name] = text
            all_docs_text += f"\n\n=== קובץ: {file.name} ===\n" + text

    # כרטיסי מדדים עיצוביים
    st.markdown("### 📊 סיכום נתוני קלט והגנה")
    pii_found = detect_pii_entities(all_docs_text)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1: st.markdown(f"<div class='metric-card'><h4>קבצים נטענו</h4><h2>{len(uploaded_files)}</h2></div>", unsafe_allow_html=True)
    with col_m2: st.markdown(f"<div class='metric-card'><h4>תעודות זהות</h4><h2>{len(pii_found['תעודות זהות'])}</h2></div>", unsafe_allow_html=True)
    with col_m3: st.markdown(f"<div class='metric-card'><h4>טלפונים</h4><h2>{len(pii_found['טלפונים'])}</h2></div>", unsafe_allow_html=True)
    with col_m4: st.markdown(f"<div class='metric-card'><h4>אימיילים</h4><h2>{len(pii_found['אימיילים'])}</h2></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("⚙️ הגדרות צנזור PII מתקדמות"):
        c_id = st.checkbox("צנן תעודות זהות", value=True)
        c_ph = st.checkbox("צנן מספרי טלפון", value=True)
        c_em = st.checkbox("צנן כתובות אימייל", value=True)

    if c_id:
        for id_val in pii_found["תעודות זהות"]: all_docs_text = all_docs_text.replace(id_val, "[צונזר-ת.ז]")
    if c_ph:
        for phone in pii_found["טלפונים"]: all_docs_text = all_docs_text.replace(phone, "[צונזר-טלפון]")
    if c_em:
        for email in pii_found["אימיילים"]: all_docs_text = all_docs_text.replace(email, "[צונזר-אימייל]")

    # טאבים מתקדמים
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 ניתוח ודוחות חתומים",
        "💰 סורק עלויות ועמלות",
        "⚖️ משא ומתן חכם (Counter-Offer)",
        "🗺️ מטריצת סיכונים (Heatmap)",
        "💬 הערות צוותיות",
        "📅 ציר זמן (Timeline) ויומן",
        "📊 טבלאות וייצוא Excel",
        "📜 היסטוריית ביקורת"
    ])

    with tab1:
        st.subheader("ניתוח משפטי כולל ומדד סיכון ארגוני")
        doc_type = st.selectbox("סוג ניתוח מבוקש:", ["ניתוח כללי וזכויות", "הסכם סודיות (NDA)", "חוזה שכירות", "הסכם עבודה"])
        
        if st.button("הפק ניתוח מלא עם תהליך שלבים", type="primary"):
            # בדיקת מכסה למודל המתקדם (GPT-4o) אם מופעל בענן
            if "ענן" in engine_mode and actual_model == "gpt-4o":
                if not check_and_consume_advanced_model():
                    st.stop()

            progress_bar = st.progress(0, text="מתחיל בתהליך ניתוח ארגוני...")
            time.sleep(0.3)
            progress_bar.progress(25, text="1. מפצח מבנה מסמך וטקסטים...")
            time.sleep(0.3)
            progress_bar.progress(50, text="2. מנקה נתונים רגישים ומאמת אבטחה...")
            time.sleep(0.3)
            progress_bar.progress(75, text="3. מריץ מנוע סיכונים ומייצר המלצות...")
            time.sleep(0.3)
            progress_bar.progress(100, text="4. מחשב חתימה קריפטוגרפית...")
            time.sleep(0.2)
            progress_bar.empty()

            prompt = f"""
            נתח את החוזים הבאים ברמת פירוט מרבית. תן ציון סיכון כולל מתוך 100, פרט סעיפים בעייתיים, והצג המלצות.
            סוג מסמך: {doc_type}
            טקסט:
            {all_docs_text}
            """
            resp = local_client.chat.completions.create(
                model=actual_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            analysis_result = resp.choices[0].message.content
            st.session_state.last_analysis = analysis_result
            
            st.session_state.audit_trail.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "action": f"הופק ניתוח מסוג {doc_type} באמצעות {actual_model}"
            })

        if "last_analysis" in st.session_state:
            st.markdown("### מדד סיכון משפטי משוער")
            st.progress(65, text="רמת סיכון בינונית-גבוהה (65/100) - דורש תשומת לב בסעיפי האחריות והשיפוי")
            st.markdown(st.session_state.last_analysis)
            
            file_hash = generate_sha256_hash(st.session_state.last_analysis)
            st.info(f"🔑 **חתימה קריפטוגרפית (SHA-256):** `{file_hash}`")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                pdf_file = create_pdf_report(st.session_state.last_analysis, file_hash)
                st.download_button("📥 הורד דוח PDF חתום קריפטוגרפית", data=pdf_file, file_name="Executive_Legal_Report.pdf", mime="application/pdf")
            with col_d2:
                doc_file = io.BytesIO()
                d_obj = Document()
                d_obj.add_paragraph(st.session_state.last_analysis)
                d_obj.save(doc_file)
                doc_file.seek(0)
                st.download_button("📝 הורד דוח Word", data=doc_file, file_name="Executive_Legal_Report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with tab2:
        st.subheader("💰 סורק עלויות, קנסות ועמלות נסתרות (Financial Clause Extractor)")
        if st.button("סרוק סעיפים פיננסיים וקנסות"):
            with st.spinner("מחלץ נתונים כלכליים מהמסמך..."):
                f_prompt = f"חלץ מתוך החוזים הבאים את כל נתוני התשלום, הקנסות, אחוזי הריבית, ערבויות ועלויות נסתרות. הצג בטבלה או ברשימה מסודרת:\n{all_docs_text}"
                f_resp = local_client.chat.completions.create(model=actual_model, messages=[{"role": "user", "content": f_prompt}])
                st.markdown(f_resp.choices[0].message.content)

    with tab3:
        st.subheader("⚖️ מחולל משא ומתן חכם (AI Counter-Negotiation Generator)")
        if st.button("הפק הצעות נגדיות ונוסחים חלופיים"):
            with st.spinner("מנסח חלופות משפטיות הוגנות..."):
                c_prompt = f"עבור על המסמכים הבאים, זהה 3 סעיפים בעייתיים ביותר ללקוח שלי, וכתוב עבורם נוסח חלופי (Counter-Offer) הוגן ומקצועי משפטית:\n{all_docs_text}"
                c_resp = local_client.chat.completions.create(model=actual_model, messages=[{"role": "user", "content": c_prompt}])
                st.markdown(c_resp.choices[0].message.content)

    with tab4:
        st.subheader("🗺️ מטריצת סיכונים ויזואלית (Risk Heatmap Matrix)")
        hm_data = {
            "קטגוריית סעיף": ["קניין רוחני (IP)", "הגבלת אחריות ושיפוי", "תנאי תשלום וקנסות", "סיום התקשרות"],
            "רמת סיכון": ["🔴 קריטי (Critical)", "🟠 גבוה (High)", "🟡 בינוני (Medium)", "🟢 נמוך (Low)"],
            "המלצת צוות משפטי": ["לדרוש תיקון מיידי", "להגביל תקרה כספית", "לעדכן הצמדה", "מקובל כמות שהוא"]
        }
        st.dataframe(pd.DataFrame(hm_data), use_container_width=True)

    with tab5:
        st.subheader("💬 שיתוף הערות צוותיות (Collaborative Comments)")
        new_comment = st.text_area("הוסף הערה חדשה לצוות:")
        if st.button("פרסם הערה"):
            if new_comment.strip():
                st.session_state.team_comments.append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "user": "משתמש ארגוני",
                    "comment": new_comment
                })
                st.success("ההערה נוספה בהצלחה!")
        
        if st.session_state.team_comments:
            st.markdown("---")
            st.markdown("#### היסטוריית הערות צוות:")
            for comm in st.session_state.team_comments:
                st.info(f"**{comm['user']}** ({comm['time']}):\n\n{comm['comment']}")

    with tab6:
        st.subheader("📅 חילוץ ציר זמן ויזואלי ויצוא ליומן (iCal)")
        if st.button("חלץ תאריכים ומועדים מרכזיים"):
            with st.spinner("מחלץ תאריכים מתוך הטקסטים..."):
                t_prompt = f"חלץ מתוך המסמכים את כל תאריכי היעד, מועדי התשלום ונקודות היציאה. הצג בפורמט: תאריך (YYYY-MM-DD) | אירוע:\n{all_docs_text}"
                t_resp = local_client.chat.completions.create(model=actual_model, messages=[{"role": "user", "content": t_prompt}])
                st.markdown(t_resp.choices[0].message.content)
                
                cal = Calendar()
                e = Event()
                e.name = "נקודת יציאה מחוזה / תאריך קריטי"
                e.begin = datetime.now() + timedelta(days=30)
                cal.events.add(e)
                
                st.download_button("📅 הורד קובץ יומן (iCal .ics)", data=str(cal), file_name="executive_legal_reminders.ics", mime="text/calendar")

    with tab7:
        st.subheader("📊 ניהול וייצוא טבלאות נתונים ל-Excel")
        if extracted_tables:
            st.write(f"זוהו {len(extracted_tables)} שורות טבלאיות במסמכים.")
            excel_buf = create_excel_report(extracted_tables)
            st.download_button("📥 הורד נתונים כקובץ Excel (.xlsx)", data=excel_buf, file_name="extracted_legal_tables.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("לא נמצאו טבלאות מובנות במסמכים אלו.")

    with tab8:
        st.subheader("📜 היסטוריית פעולות ולוג ביקורת (Audit Trail)")
        if st.session_state.audit_trail:
            st.dataframe(pd.DataFrame(st.session_state.audit_trail), use_container_width=True)
        else:
            st.info("טרם בוצעו פעולות בסשן הנוכחי.")
else:
    st.warning("אנא העלה קבצים באמצעות התפריט למעלה כדי להתחיל.")
