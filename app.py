import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document  # ✅ تم الإصلاح هنا

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

# ===============================
# 📊 دالة Excel الذكية
def smart_excel_query(df, query):
    query = query.lower()

    try:
        if "عدد" in query:
            return f"عدد الصفوف هو: {len(df)}"

        for col in df.columns:
            for value in df[col].astype(str):
                if value.lower() in query:
                    row = df[df[col].astype(str) == value]
                    return row.to_string(index=False)

        if "أكبر" in query or "اعلى" in query:
            numeric_cols = df.select_dtypes(include='number')
            if not numeric_cols.empty:
                return numeric_cols.max().to_string()

        if "أصغر" in query or "اقل" in query:
            numeric_cols = df.select_dtypes(include='number')
            if not numeric_cols.empty:
                return numeric_cols.min().to_string()

    except:
        pass

    return None

# ===============================
# ⚡ تجهيز البيانات + المصادر
@st.cache_resource
def process_files(files):
    excel_data = []
    documents = []

    for file in files:
        try:
            if file.name.endswith('.pdf'):
                reader = PdfReader(file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        documents.append(
                            Document(
                                page_content=text,
                                metadata={"source": f"{file.name} - صفحة {i+1}"}
                            )
                        )

            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
                excel_data.append(df)

        except:
            continue

    # تقسيم النصوص
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    split_docs = text_splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    vectorstore = FAISS.from_documents(
        documents=split_docs,
        embedding=embeddings
    )

    return vectorstore, excel_data

# ===============================

if uploaded_files:
    with st.spinner("سالم يحلل الملفات..."):
        vectorstore, excel_data = process_files(tuple(uploaded_files))

    st.success("سالم جاهز!")

    user_query = st.chat_input("اسأل سالم...")

    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):

            llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                openai_api_key=api_key
            )

            answer = ""
            sources = []

            # ===============================
            # 📊 Excel أولًا
            if excel_data:
                for df in excel_data:
                    result = smart_excel_query(df, user_query)
                    if result:
                        answer = result
                        break

            # ===============================
            # 📄 PDF + مصادر
            if not answer:
                docs = vectorstore.similarity_search(user_query, k=5)

                context = ""
                for doc in docs:
                    context += doc.page_content + "\n\n"
                    sources.append(doc.metadata.get("source", "غير معروف"))

                prompt = f"""
أنت مساعد سلامة مهنية ذكي ودقيق.

تعليمات:
- أجب فقط من المعلومات
- لا تخمّن
- إذا لم تجد الإجابة قل: "غير موجود في البيانات"
- اذكر التفاصيل بوضوح
- نظّم الإجابة

المعلومات:
{context}

السؤال:
{user_query}

الإجابة:
"""

                response = llm.invoke(prompt)
                answer = response.content

            # عرض الإجابة
            st.write(answer)

            # عرض المصادر
            if sources:
                st.markdown("### 📍 المصادر:")
                for s in set(sources):
                    st.write(f"- {s}")

else:
    st.info("ارفع ملفاتك لتبدأ")
