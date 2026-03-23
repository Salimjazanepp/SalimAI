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

# ===============================
# 🔥 دالة ذكية للتعامل مع Excel
def smart_excel_query(df, query):
    query = query.lower()

    try:
        # عدد الصفوف
        if "عدد" in query:
            return f"عدد الصفوف هو: {len(df)}"

        # البحث عن قيمة
        for col in df.columns:
            for value in df[col].astype(str):
                if value.lower() in query:
                    row = df[df[col].astype(str) == value]
                    return row.to_string(index=False)

        # أكبر قيمة
        if "أكبر" in query or "اعلى" in query:
            numeric_cols = df.select_dtypes(include='number')
            if not numeric_cols.empty:
                return numeric_cols.max().to_string()

        # أصغر قيمة
        if "أصغر" in query or "اقل" in query:
            numeric_cols = df.select_dtypes(include='number')
            if not numeric_cols.empty:
                return numeric_cols.min().to_string()

    except:
        pass

    return None

# ===============================
# ⚡ تخزين البيانات لتسريع الأداء
@st.cache_resource
def process_files(files):
    text_data = ""
    excel_data = []

    for file in files:
        try:
            if file.name.endswith('.pdf'):
                reader = PdfReader(file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_data += text + "\n"

            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
                excel_data.append(df)

        except:
            continue

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = text_splitter.split_text(text_data)

    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    vectorstore = FAISS.from_texts(
        texts=chunks,
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

            # ===============================
            # 📊 أولًا: Excel (دقيق 100%)
            if excel_data:
                for df in excel_data:
                    result = smart_excel_query(df, user_query)
                    if result:
                        answer = result
                        break

            # ===============================
            # 📄 ثانيًا: PDF (محسّن)
            if not answer:
                docs = vectorstore.similarity_search(user_query, k=5)

                context = "\n\n".join([
                    doc.page_content for doc in docs
                ])

                prompt = f"""
أنت مساعد سلامة مهنية ذكي ودقيق.

تعليمات:
- أجب فقط من المعلومات الموجودة
- لا تخمّن أبداً
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

            st.write(answer)

else:
    st.info("ارفع ملفاتك لتبدأ")
