import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

# التحقق من المفتاح
if "OPENAI_API_KEY" not in st.secrets:
    st.error("يرجى إضافة المفتاح في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

st.title("🛡️ مساعد السلامة الذكي (سالم)")

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader(
        "ارفع ملفات العمل (PDF أو Excel)",
        type=['pdf', 'xlsx'],
        accept_multiple_files=True
    )

# ✅ تخزين الفهرس لتسريع الأداء
@st.cache_resource
def process_files(files):
    all_text = ""

    for file in files:
        try:
            if file.name.endswith('.pdf'):
                reader = PdfReader(file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"

            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)

                columns = ", ".join(df.columns)
                all_text += f"اسماء الأعمدة: {columns}\n"

                for _, row in df.iterrows():
                    row_text = ", ".join([f"{col}: {row[col]}" for col in df.columns])
                    all_text += row_text + "\n"

        except:
            continue

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = text_splitter.split_text(all_text)

    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    vectorstore = FAISS.from_texts(
        texts=chunks,
        embedding=embeddings
    )

    return vectorstore

# ===============================

if uploaded_files:
    with st.spinner("سالم يحلل الملفات (مرة واحدة فقط)..."):
        vectorstore = process_files(tuple(uploaded_files))

    st.success("سالم جاهز للرد!")

    user_query = st.chat_input("اسأل سالم...")

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):

            llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                openai_api_key=api_key
            )

            # 🔍 البحث
            docs = vectorstore.similarity_search(user_query, k=3)

            context = "\n\n".join([
                doc.page_content for doc in docs
            ])

            prompt = f"""
أنت مساعد سلامة مهنية ذكي.
جاوب فقط من البيانات التالية:

{context}

السؤال:
{user_query}
"""

            response = llm.invoke(prompt)

            st.write(response.content)

else:
    st.info("ارفع ملفاتك لتبدأ المحادثة مع سالم.")
