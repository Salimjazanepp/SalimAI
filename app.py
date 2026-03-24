[11:50, 3/24/2026] Hussain Maslouf: import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

# 🔥 عنوان + النسخة التجريبية
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("### ⚠️ نسخة تجريبية - إدارة محطة طاقة جازان")

# التحقق من المفتاح
if "OPENAI_API_KEY" not in st.secrets:
    st.error("يرجى إضافة المفتاح في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader(
        "ارفع ملفات العمل (PDF أو Excel)",
        type=['pdf', 'xlsx'],
        accept_multiple_files=True
    )

# ===============================
# 📊 Excel
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

    except:
        pass

    return None

# ===============================
# ⚡ تجهيز البيانات
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
            # 📊 Excel
            if excel_data:
                for df in excel_data:
                    result = smart_excel_query(df, user_query)
                    if result:
                        answer = result
                        break

            # ===============================
            # 📄 PDF (اقتباس حرفي)
            if not answer:
                docs = vectorstore.similarity_search(user_query, k=10)

                context = ""
                for i, doc in enumerate(docs):
                    context += f"\n--- مقطع {i+1} ---\n"
                    context += doc.page_content + "\n"
                    sources.append(doc.metadata.get("source", "غير معروف"))

                if not context.strip():
                    st.write("لا توجد معلومات كافية")
                    st.stop()

                # 🔥 برومبت الاقتباس
                prompt = f"""
أنت مساعد سلامة مهنية.

مهم جداً:
- الإجابة موجودة داخل النص
- انسخ الإجابة حرفياً من النص
- لا تشرح
- لا تختصر
- لا تغيّر الكلمات
- فقط اقتباس مباشر

إذا لم تجد نص مناسب قل:
"لا يوجد نص مطابق في البيانات"

النص:
{context}

السؤال:
{user_query}

الإجابة (اقتباس حرفي):
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
[12:01, 3/24/2026] Hussain Maslouf: import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

# 🔥 العنوان
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("### ⚠️ نسخة تجريبية - إدارة محطة طاقة جازان")

# التحقق من المفتاح
if "OPENAI_API_KEY" not in st.secrets:
    st.error("يرجى إضافة المفتاح في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# ===============================
with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader(
        "ارفع ملفات PDF أو Excel",
        type=['pdf', 'xlsx'],
        accept_multiple_files=True
    )

# ===============================
# 📊 Excel
def smart_excel_query(df, query):
    query = query.lower()

    try:
        if "عدد" in query:
            return f"عدد الصفوف: {len(df)}"

        for col in df.columns:
            for value in df[col].astype(str):
                if value.lower() in query:
                    row = df[df[col].astype(str) == value]
                    return row.to_string(index=False)

    except:
        pass

    return None

# ===============================
# ⚡ تجهيز البيانات
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
                                metadata={
                                    "source": f"{file.name} - صفحة {i+1}"
                                }
                            )
                        )

            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
                excel_data.append(df)

        except:
            continue

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
            # 📊 Excel
            if excel_data:
                for df in excel_data:
                    result = smart_excel_query(df, user_query)
                    if result:
                        answer = result
                        break

            # ===============================
            # 📄 PDF (بحث احترافي)
            if not answer:
                docs = vectorstore.max_marginal_relevance_search(
                    user_query,
                    k=8,
                    fetch_k=20
                )

                context = ""
                for i, doc in enumerate(docs):
                    src = doc.metadata.get("source", "غير معروف")
                    context += f"\n--- مصدر: {src} ---\n"
                    context += doc.page_content + "\n"
                    sources.append(src)

                if not context.strip():
                    st.write("لا توجد معلومات كافية")
                    st.stop()

                # 🔥 برومبت احترافي (فهم + اقتباس + تنظيم)
                prompt = f"""
أنت مساعد سلامة مهنية ذكي.

مهم:
- افهم السؤال جيداً
- استخرج الإجابة من النص
- اقتبس الجمل المهمة
- نظّم الإجابة بشكل واضح (نقاط)
- لا تخلط النصوص بشكل عشوائي
- لا تخترع معلومات

النص:
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
                for s in sorted(set(sources)):
                    st.write(f"- {s}")

else:
    st.info("ارفع ملفاتك لتبدأ")
