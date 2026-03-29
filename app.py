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

        # 📄 PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)

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

        # 📊 Excel
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                text = df.to_string()
            except:
                continue

        if text.strip():
            docs[file] = text

    return docs

all_docs = load_all_data()

# 🧪 عرض الملفات للتأكد (احذفه لاحقًا)
st.write("📂 الملفات:", list(all_docs.keys()))

# --- 4. محرك البحث الذكي 🔥 ---
def get_relevant_context(query, docs):
    query = query.lower()
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()

        score = 0

        # 🔥 1. تطابق اسم الملف (أقوى)
        if any(word in filename_lower for word in query.split()):
            score += 5

        # 🔥 2. تطابق داخل المحتوى
        score += sum(word in content_lower for word in query.split())

        scored_docs.append((score, filename, content))

    # ترتيب حسب الأعلى
    scored_docs.sort(reverse=True)

    context = ""

    # 🔥 أفضل ملفين فقط لزيادة الدقة
    for score, filename, content in scored_docs[:2]:
        context += f"\n\n[مصدر: {filename}]\n{content[:5000]}"

    return context[:12000]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 6. إدخال المستخدم ---
if question := st.chat_input("اسأل عن أنظمة السلامة أو أي تفصيل..."):
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    context = get_relevant_context(question, all_docs)

    # 🧪 مراقبة
    st.write("📊 حجم البيانات:", len(context))

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system",
                        "content": """أنت خبير سلامة في محطة طاقة.

مهمتك:
- أجب فقط من النص
- ركز على الموضوع المطلوب (مثلاً: العمل على المرتفعات)
- تجاهل أي معلومات غير مرتبطة
- اعرض الخطوات كنقاط
- اذكر المصدر إذا وجد
- لا تخمن أبداً
"""
                    },
                    {
                        "role": "user",
                        "content": f"النص:\n{context}\n\nالسؤال:\n{question}"
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

# --- 7. في حال ما فيه ملفات ---
if not all_docs:
    st.warning("⚠️ لا توجد ملفات داخل مجلد data")
