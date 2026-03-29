import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# --- 1. إعداد المفتاح ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود")
    st.stop()
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")
st.markdown("### 🛡️ مساعد السلامة الذكي (سالم)")
st.info("📑 نظام بحث متطور لجميع ملفات السلامة - إدارة محطة جازان - نسخة تجريبية")

# --- 3. دالة جلب البيانات (موزونة بدقة لتفادي خطأ الـ Tokens) ---
@st.cache_resource
def load_all_data():
    data_path = "data/"
    all_sections = []
    
    if not os.path.exists(data_path):
        return ""

    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]
    
    if not files:
        return ""

    # تقسيم المساحة المتاحة (16 ألف توكن) على عدد الملفات
    # سنأخذ حوالي 3500 حرف من كل ملف لضمان شمولية 10-15 ملف بسهولة
    for file in files:
        path = os.path.join(data_path, file)
        file_content = ""
        
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                # نأخذ أول 8 صفحات فقط من كل ملف لضمان المساحة
                for page in reader.pages[:8]:
                    text = page.extract_text()
                    if text: file_content += text
            except: continue
        
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                file_content = df.to_string()
            except: continue
        
        if file_content:
            # نأخذ أهم 3500 حرف من كل ملف (حوالي 700-900 كلمة)
            all_sections.append(f"\n[مستند: {file}]\n{file_content[:3500]}")
                
    # ندمج الأقسام (المجموع سيكون حوالي 12-14 ألف توكن، وهو آمن جداً)
    return "\n\n".join(all_sections)

# --- 4. تشغيل قاعدة البيانات ---
knowledge_base = load_all_data()

# --- 5. نظام المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

if question := st.chat_input("اسأل سالم عن السقالات، جودة الهواء، أو أي موضوع آخر..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"): st.write(question)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system", 
                        "content": "أنت خبير سلامة في محطة جازان. أمامك مقتطفات من عدة ملفات. أجب بدقة من المصدر المرتبط بالسؤال فقط."
                    },
                    {
                        "role": "user", 
                        "content": f"المعلومات:\n{knowledge_base}\n\nالسؤال: {question}"
                    }
                ],
                temperature=0.1
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ حدث خطأ فني: {e}")
