import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

# ------------------------
# API KEY
# ------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود")
    st.stop()

openai.api_key = st.secrets["OPENAI_API_KEY"]

# ------------------------
# UI
# ------------------------
st.set_page_config(page_title="سالم - مستوى الشركات", page_icon="🛡️")
st.title("🛡️ سالم - مساعد السلامة الاحترافي")
st.caption("🚀 نسخة احترافية - إدارة محطة طاقة جازان")

# ------------------------
# تحميل + تقسيم البيانات
# ------------------------
@st.cache_resource
def load_vector_db():
    data_path = "data/"
    documents = []

    for file in os.listdir(data_path):
        path = os.path.join(data_path, file)

        # PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)

                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except:
                        continue

                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        documents.append({
                            "text": text,
                            "source": file,
                            "page": i + 1
                        })
            except:
                continue

        # Excel
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                documents.append({
                    "text": df.to_string(),
                    "source": file,
                    "page": "Excel"
                })
            except:
                continue

    # تقسيم النصوص 🔥
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    texts = []
    metadata = []

    for doc in documents:
        chunks = splitter.split_text(doc["text"])
        for chunk in chunks:
            texts.append(chunk)
            metadata.append({
                "source": doc["source"],
                "page": doc["page"]
            })

    # Embeddings (فهم المعنى)
    embeddings = OpenAIEmbeddings()

    db = FAISS.from_texts(texts, embeddings, metadatas=metadata)

    return db

db = load_vector_db()

# ------------------------
# المحادثة
# ------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ------------------------
# سؤال المستخدم
# ------------------------
if question := st.chat_input("اسأل سالم..."):

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # 🔥 البحث بالمعنى (مو بالكلمات)
    docs = db.similarity_search(question, k=5)

    context = ""
    sources = []

    for d in docs:
        context += f"\n\n[المصدر: {d.metadata['source']} - صفحة {d.metadata['page']}]\n"
        context += d.page_content

        sources.append(f"{d.metadata['source']} - صفحة {d.metadata['page']}")

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system",
                        "content": """أنت خبير سلامة محترف في محطة طاقة.

مهمتك:
- أجب فقط من النص
- اقتبس الجمل المهمة
- اذكر المصدر والصفحة
- لا تخمن
- إذا لم تجد إجابة واضحة قل: لا توجد معلومات كافية
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

            # عرض المصادر
            st.markdown("### 📌 المصادر:")
            for s in set(sources):
                st.write(f"- {s}")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

        except Exception as e:
            st.error(f"❌ {e}")
