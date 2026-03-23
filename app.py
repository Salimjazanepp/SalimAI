import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

# استخراج النصوص
def get_text(files):
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
                all_text += df.to_string() + "\n"

        except:
            continue
    return all_text

if uploaded_files:
    raw_text = get_text(uploaded_files)

    if raw_text:
        # 🔥 تقسيم ذكي للنص
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150
        )

        chunks = text_splitter.split_text(raw_text)

        with st.spinner("سالم يحلل البيانات..."):
            try:
                # إنشاء embeddings + vector DB
                embeddings = OpenAIEmbeddings(openai_api_key=api_key)
                vectorstore = FAISS.from_texts(
                    texts=chunks,
                    embedding=embeddings
                )

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

                        # 1. البحث
                        docs = vectorstore.similarity_search(user_query, k=4)

                        # 2. فلترة
                        filtered_docs = []
                        for doc in docs:
                            if user_query.lower() in doc.page_content.lower():
                                filtered_docs.append(doc)

                        if not filtered_docs:
                            filtered_docs = docs

                        # 3. اختيار أفضل نتائج
                        final_docs = filtered_docs[:3]

                        # 4. دمج النصوص
                        context = "\n\n".join([
                            doc.page_content for doc in final_docs
                        ])

                        # 5. بناء البرومبت
                        prompt = f"""
أنت مساعد سلامة مهنية ذكي.
اعتمد فقط على المعلومات التالية للإجابة:

{context}

السؤال:
{user_query}
"""

                        # 6. إرسال الطلب
                        response = llm.invoke(prompt)

                        st.write(response.content)

            except Exception as e:
                st.error(f"حدث خطأ فني: {e}")

    else:
        st.warning("لم يتم العثور على نص داخل الملفات.")

else:
    st.info("ارفع ملفاتك لتبدأ المحادثة مع سالم.")
