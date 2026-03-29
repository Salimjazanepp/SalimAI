import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# --- 1. إعداد المفتاح ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود في Secrets")
    st.stop()
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")

# العبارة التي طلبتها في الواجهة
st.markdown("### 🛡️ مساعد السلامة الذكي (سالم)")
st.info("📑 نظام بحث متطور لجميع ملفات السلامة - إدارة محطة جازان - نسخة تجريبية")

# --- 3. دالة جلب البيانات (معدلة لحل مشكلة التمركز على ملف واحد) ---
@st.cache_resource
def load_all_data():
    data_path = "data/"
    all_sections = [] # سنجمع أجزاء من كل ملف بدلاً من نص واحد طويل
    
    if not os.path.exists(data_path):
        return ""

    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]
    
    for file in files:
        path = os.path.join(data_path, file)
        file_content = ""
        
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                # نأخذ أول 15 صفحة من كل ملف لضمان وصول "سالم" لكل الملفات
                for page in reader.pages[:15]:
                    text = page.extract_text()
                    if text:
                        file_content += text
            except:
                continue
        
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                file_content = df.to_string()
            except:
                continue
        
        if file_content:
            # نأخذ زبدة كل ملف (أول 8000 حرف) لضمان أن ملف النفايات لا يغطي على الباقي
            all_sections.append(f"\n[اسم المستند: {file}]\n{file_content[:8000]}")
                
    # ندمج كل الأقسام مع بعضها
    return "\n\n".join(all_sections)

# --- 4. تشغيل قاعدة البيانات ---
knowledge_base = load_all_data()

# --- 5. نظام المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if question := st.chat_input("اسأل سالم عن السقالات، جودة الهواء، أو أي موضوع آخر..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system", 
                        "content": "أنت خبير سلامة في محطة جازان. أمامك نصوص من عدة ملفات مختلفة. ابحث في المصدر المرتبط بسؤال المستخدم فقط. إذا كان السؤال عن السقالات، تجاهل نص ملف النفايات. كن دقيقاً جداً في تحديد مصدر المعلومة."
                    },
                    {
                        "role": "user", 
                        "content": f"المعلومات المتاحة من الملفات:\n{knowledge_base}\n\nالسؤال: {question}"
                    }
                ],
                temperature=0.1 # تقليل الدرجة لضمان عدم الخلط بين الملفات
            )
            
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            st.error(f"⚠️ حدث خطأ فني: {e}")

if not knowledge_base:
    st.info("📂 الرجاء التأكد من وجود ملفات PDF في مجلد data على GitHub.")
