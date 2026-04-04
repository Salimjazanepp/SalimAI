import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# ------------------------
# 1. API KEY
# ------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود")
    st.stop()

openai.api_key = st.secrets["OPENAI_API_KEY"]

# ------------------------
# 2. الواجهة
# ------------------------
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")

st.title("🛡️ مساعد السلامة الافتراضي (سالم)")
st.markdown("### إلتزم بالسلامة وخلك سالم")
st.info("📑 نظام ذكي لملفات السلامة والموظفين - إدارة محطة طاقة جازان (نسخة تجريبية)")

# ------------------------
# 3. تحميل البيانات
# ------------------------
@st.cache_resource
def load_all_data():
    data_path = "data/"
    docs = {}
    excel_data = {}

    if not os.path.exists(data_path):
        return {}, {}

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
                excel_data[file] = df
                text = df.to_string()
            except:
                continue

        if text.strip():
            docs[file] = text

    return docs, excel_data

all_docs, excel_data = load_all_data()

# عرض الملفات للتأكد
st.write("📂 الملفات:", list(all_docs.keys()))

# ------------------------
# 4. بحث Excel احترافي 🔥
# ------------------------
def search_excel(query, excel_data):
    query = query.lower().strip()
    query_words = query.split()

    best_match = None
    best_score = 0

    for filename, df in excel_data.items():
        for _, row in df.iterrows():
            row_values = [str(x).lower() for x in row.values]

            score = 0

            for word in query_words:
                for cell in row_values:
                    if word in cell:
                        score += 1

            if score > best_score:
                best_score = score
                best_match = (filename, row, df.columns)

    if best_match and best_score >= 2:
        filename, row, columns = best_match

        result = f"📊 من الملف: {filename}\n\n"

        for col in columns:
            value = row[col]
            if pd.notna(value) and str(value).strip() != "":
                result += f"{col}: {value}\n"

        return result

    return None

# ------------------------
# 5. بحث PDF
# ------------------------
def get_relevant_context(query, docs):
    query = query.lower()
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()

        score = 0

        if any(word in filename_lower for word in query.split()):
            score += 10

        score += sum(word in content_lower for word in query.split())

        scored_docs.append((score, filename, content))

    scored_docs.sort(reverse=True)

    context = ""

    if scored_docs:
        main_doc = scored_docs[0]
        context += f"\n\n[مصدر رئيسي: {main_doc[1]}]\n{main_doc[2][:6000]}"

        for score, filename, content in scored_docs[1:]:
            if filename != main_doc[1]:
                context += f"\n\n[مصدر إضافي: {filename}]\n{content[:3000]}"
                break

    return context[:12000]

# ------------------------
# 6. المحادثة
# ------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ------------------------
# 7. الإدخال
# ------------------------
if question := st.chat_input("اسأل سالم عن السلامة أو الموظفين..."):

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # 🔥 Excel أولاً
    excel_result = search_excel(question, excel_data)

    if excel_result:
        with st.chat_message("assistant"):
            st.write(excel_result)

        st.session_state.messages.append({
            "role": "assistant",
            "content": excel_result
        })

        st.stop()

    # 🔥 PDF
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
- ركز على المصدر الرئيسي
- استخدم المصدر الإضافي فقط للدعم
- أجب من النص فقط
- اعرض الإجابة كنقاط
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

# ------------------------
# 8. بدون بيانات
# ------------------------
if not all_docs:
    st.warning("⚠️ لا توجد ملفات داخل مجلد data")
