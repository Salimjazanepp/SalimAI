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
st.markdown("### 🛡️ مساعد السلامة الذكي (سالم)")
st.info("📑 نظام بحث متطور لجميع ملفات السلامة - إدارة محطة طاقة جازان - نسخة تجريبية")

# --- 3. تحميل البيانات ---
@st.cache_resource
def load_all_data():
    data_path = "data/"
    docs = {}

    if not os.path.exists(data_path):
        return {}

    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]

    for file in files:
        path = os.path.join(data_path, file)
        text = ""

        # PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)

                # فك التشفير
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except:
                        continue

                for page in reader.pages[:15]:
                    t = page.extract_text()
                    if t:
                        text += t

            except:
                continue

        # Excel
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                text = df.to_string()
            except:
                continue

        if text:
            docs[file] = text

    return docs

all_docs = load_all_data()

# --- 4. محرك البحث المطور 🔥 ---
def get_relevant_context(query, docs):
    query = query.lower()
    scored_docs = []

    for filename, content in docs.items():
        content_lower = content.lower()

        # حساب درجة التطابق
        score = sum(word in content_lower for word in query.split())

        if score > 0:
            scored_docs.append((score, filename, content))

    # ترتيب حسب الأفضل
    scored_docs.sort(reverse=True)

    context = ""

    # أخذ أفضل 3 ملفات فقط
    for score, filename, content in scored_docs[:3]:
        context += f"\n\n[مصدر: {filename}]\n{content[:4000]}"

    # fallback إذا ما فيه تطابق
    if not context:
        for filename, content in list(docs.items())[:3]:
            context += f"\n\n[مصدر: {filename}]\n{content[:2000]}"

    return context[:12000]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 6. إدخال المستخدم ---
if question := st.chat_input("اسأل عن أنظمة الحماية من السقوط أو أي تفصيل آخر..."):
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # جلب السياق الذكي
    context = get_relevant_context(question, all_docs)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system",
                        "content": """أنت خبير سلامة في محطة طاقة.

مهمتك:
- استخراج الإجابة من النص فقط
- إذا وجدت خطوات أو تعليمات، اعرضها كنقاط
- اقتبس الجمل المهمة عند الحاجة
- اذكر اسم المصدر إذا توفر
- لا تخمن ولا تضيف معلومات خارج النص
"""
                    },
                    {
                        "role": "user",
                        "content": f"النصوص:\n{context}\n\nالسؤال:\n{question}"
                    }
                ],
                temperature=0
            )

            answer = response["choices"][0]["message"]["content"]

            st.write(answer)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

        except Exception as e:
            st.error(f"⚠️ خطأ: {e}")
