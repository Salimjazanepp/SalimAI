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
st.caption("🚀 نظام داخلي ذكي - إدارة محطة طاقة جازان")

# ------------------------
# تحميل البيانات + تحويلها لذكاء
# ------------------------
@st.cache_resource
def load_vector_db():
    data_path = "data/"
    documents = []

    if not os.path.exists(data_path):
        return None

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

    # تقسيم النصوص
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    texts = []
    metadatas = []

    for doc in documents:
        chunks = splitter.split_text(doc["text"])
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({
                "source": doc["source"],
                "page": doc["page"]
            })

    # Embeddings (فهم المعنى)
    embeddings = OpenAIEmbeddings()

    db = FAISS.from_texts(texts, embeddings, metadatas=metadatas)

    return db

db = load_vector_db()

# ------------------------
# إدارة المحادثة
# ------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ------------------------
# سؤال المستخدم
# ------------------------
if question := st.chat_input("اسأل سالم عن السلامة..."):

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # 🔥 بحث احترافي (متعدد المصادر)
    search_results = db.similarity_search(question, k=10)

    docs = []
    seen_sources = set()

    for d in search_results:
        source = d.metadata["source"]

        if source not in seen_sources:
            docs.append(d)
            seen_sources.add(source)

        if len(seen_sources) >= 4:  # 🔥 تنوع المصادر
            break

    # بناء السياق
    context = ""
    sources = []

    for d in docs:
        src = f"{d.metadata['source']} - صفحة {d.metadata['page']}"
        context += f"\n\n[المصدر: {src}]\n{d.page_content}"
        sources.append(src)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system",
                        "content": """أنت خبير سلامة في محطة طاقة.

مهمتك:
- اجمع المعلومات من عدة مصادر
- لا تعتمد على مصدر واحد
- اعرض الإجابة كنقاط واضحة
- اذكر المصدر لكل نقطة إذا أمكن
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

            # عرض المصادر
            st.markdown("### 📌 المصادر:")
            for s in sorted(set(sources)):
                st.write(f"- {s}")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

        except Exception as e:
            st.error(f"❌ خطأ: {e}")

# ------------------------
# في حال ما فيه بيانات
# ------------------------
if not db:
    st.warning("⚠️ لا توجد ملفات في مجلد data")
