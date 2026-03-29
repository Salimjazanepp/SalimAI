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

# --- 2. الواجهة والسلوجن ---
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("<h3 style='color: #2E7D32;'>إلتزم بالسلامة.. وخلك سالم</h3>", unsafe_allow_html=True)
st.info("📑 نظام بحث متطور لجميع ملفات السلامة - إدارة محطة طاقة جازان - نسخة تجريبية")
st.divider()

# --- 3. تحميل البيانات ---
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
                for page in reader.pages[:10]: # نأخذ أول 10 صفحات من كل ملف
                    t = page.extract_text()
                    if t: text += t
            except: continue
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                text = df.to_string()
            except: continue
        if text.strip():
            docs[file] = text
    return docs

all_docs = load_all_data()

# --- 4. محرك البحث المتنوع (يمنع التركيز على ملف واحد) ---
def get_relevant_context(query, docs):
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()
        score = sum(10 for word in query_words if word in filename_lower)
        score += sum(1 for word in query_words if word in content_lower)
        if score > 0:
            scored_docs.append((score, filename, content))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    # نوزع الذاكرة على 4 ملفات بدلاً من ملف واحد ضخم
    for i in range(min(4, len(scored_docs))):
        score, filename, content = scored_docs[i]
        context += f"\n\n[مستند {i+1}: {filename}]\n{content[:2500]}\n"
    return context[:11000]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# --- 6. الإدخال والرد ---
if question := st.chat_input("اسأل سالم عن أي تفصيل..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"): st.write(question)

    context = get_relevant_context(question, all_docs)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system",
                        "content": "أنت خبير سلامة في محطة جازان. أمامك مقتطفات من عدة ملفات مختلفة. ابحث عن الإجابة في المستندات المرفقة بدقة. إذا كان السؤال عن موضوع معين، استخرج المعلومات من الملف المرتبط به. اعرض الإجابة كنقاط واذكر اسم الملف الأساسي."
                    },
                    {"role": "user", "content": f"السؤال: {question}\n\nالنصوص المتاحة:\n{context}"}
                ],
                temperature=0
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ خطأ: {e}")
