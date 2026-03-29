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

st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")
st.markdown("### 🛡️ مساعد السلامة الذكي (سالم)")
st.info("📑 نظام بحث متطور لجميع ملفات السلامة - إدارة محطة جازان - نسخة تجريبية")

# --- 2. دالة تحميل البيانات الذكية ---
@st.cache_resource
def load_all_data():
    data_path = "data/"
    docs = {} 
    if not os.path.exists(data_path): return {}
    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]
    
    for file in files:
        path = os.path.join(data_path, file)
        text = ""
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                for page in reader.pages[:15]:
                    t = page.extract_text()
                    if t: text += t
            except: continue
        elif file.endswith((".xlsx", ".xls")):
            try: text = pd.read_excel(path).to_string()
            except: continue
        if text: docs[file] = text
    return docs

all_docs = load_all_data()

# --- 3. محرك البحث عن المعلومات ذات الصلة ---
def get_relevant_context(query, docs):
    query_words = query.split()
    relevant_text = ""
    for filename, content in docs.items():
        # إذا وجدنا كلمة من السؤال في الملف، نأخذ هذا الملف كأولوية
        if any(word.lower() in content.lower() for word in query_words) or any(word in filename for word in query_words):
            relevant_text += f"\n\n[مصدر البيانات: {filename}]\n{content[:6000]}\n"
    
    # إذا لم يجد كلمات محددة، يعيد أول 12000 حرف من الإجمالي (لضمان عدم تجاوز الـ Tokens)
    return relevant_text[:12000] if relevant_text else "\n".join([f"[{k}]\n{v[:2000]}" for k, v in docs.items()])[:12000]

# --- 4. إدارة الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

if question := st.chat_input("اسأل عن أنظمة الحماية من السقوط أو أي تفصيل آخر..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"): st.write(question)

    # جلب السياق المرتبط بالسؤال فقط
    context = get_relevant_context(question, all_docs)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system", 
                        "content": "أنت خبير سلامة مهنية. مهمتك استخراج إجابات دقيقة ومباشرة من النصوص. إذا سُئلت عن 'أمثلة' أو 'خطوات'، استخرجها على شكل نقاط من صلب النص المرفق. لا تعطِ ملخصات عامة عن الملفات، بل أجب عن السؤال مباشرة."
                    },
                    {
                        "role": "user", 
                        "content": f"استخرج الإجابة المباشرة للسؤال التالي من النصوص المرفقة فقط:\n\nالنصوص:\n{context}\n\nالسؤال: {question}"
                    }
                ],
                temperature=0 # جعل الإجابة دقيقة جداً ومباشرة من النص
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ خطأ: {e}")
