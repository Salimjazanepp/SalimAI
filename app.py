import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.documents import Document

# ------------------------
# واجهة التطبيق
# ------------------------
st.set_page_config(page_title="مساعد السلامة الافتراضي (سالم)", page_icon="🛡️")
st.title("مساعد السلامة الافتراضي (سالم) 🛡️")
st.subheader("إدارة محطة طاقة جازان 🏭")

# ------------------------
# API KEY
# ------------------------
if "OPENAI_API_KEY" in st.secrets:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ لم يتم العثور على مفتاح OpenAI في Secrets")
    st.stop()

# ------------------------
# تحميل البيانات (نسخة مقاومة للأخطاء)
# ------------------------
@st.cache_resource
def load_data():
    data_path = "data/"
    documents = []

    if not os.path.exists(data_path):
        return None

    for file in os.listdir(data_path):
        file_path = os.path.join(data_path, file)

        # 📄 PDF (يتجاهل المشفر أو الخربان)
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(file_path)

                if reader.is_encrypted:
                    st.warning(f"⚠️ تم تجاهل ملف مشفر: {file}")
                    continue

                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""

                if text.strip():
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={"source": file}
                        )
                    )

            except Exception:
                st.warning(f"⚠️ تم تجاهل PDF فيه مشكلة: {file}")

        # 📊 Excel
        elif file.endswith(".xlsx") or file.endswith(".xls"):
            try:
                df = pd.read_excel(file_path)
                text = df.to_string()

                documents.append(
                    Document(
                        page_content=text,
                        metadata={"source": file}
                    )
                )

            except Exception:
                st.warning(f"⚠️ تم تجاهل Excel فيه مشكلة: {file}")

    if not documents:
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    texts = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings(
        openai_api_key=openai_api_key
    )

    vectorstore = FAISS.from_documents(texts, embeddings)

    return vectorstore

# ------------------------
# تشغيل سالم
# ------------------------
vectorstore = load_data()

if vectorstore:
    st.success("✅ سالم جاهز ويعمل بدون مشاكل")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض المحادثة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # سؤال المستخدم
    if prompt := st.chat_input("اسأل سالم عن السلامة..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(
                model_name="gpt-3.5-turbo",
                openai_api_key=openai_api_key
            ),
            retriever=vectorstore.as_retriever(),
            memory=memory
        )

        with st.chat_message("assistant"):
            try:
                response = qa_chain.invoke({"question": prompt})
                answer = response["answer"]

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as e:
                st.error(f"❌ خطأ: {e}")

else:
    st.info("📂 ضع ملفاتك داخل مجلد data")
