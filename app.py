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

# --- 2. الواجهة ---
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
                for page in reader.pages[:12]: # تقليل الصفحات قليلاً لزيادة التركيز
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

# --- 4. محرك البحث الذكي (الموزون) ---
def get_relevant_context(query, docs):
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()
        score = sum(5 for word in query_words if word in filename_lower)
        score += sum(content_lower.count(word) for word in query_words)
        
        if score > 0:
            scored_docs.append((score, filename, content))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    for i in range(min(2, len(scored_docs))):
        score, filename, content = scored_docs[i]
        context += f"\n\n[المصدر {i+1}: {filename}]\n{content[:5500]}\n"
    return context[:11500]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# --- 6. الإدخال والرد ---
if question := st.chat_input("اسأل عن تفاصيل السلامة..."):
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
                        "content": "أنت خبير سلامة مهنية في محطة جازان. مهمتك هي الإجابة بدقة من المصادر المرفقة. إذا كانت الإجابة موجودة في 'المصدر 1' فاعتمد عليه بشكل أساسي. اذكر النقاط بوضوح واذكر اسم الملف في النهاية."
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
