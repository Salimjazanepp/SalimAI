import streamlit as st
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

# إعداد واجهة التطبيق بالمسميات الجديدة
st.set_page_config(page_title="مساعد السلامة الافتراضي (سالم)", page_icon="🛡️")
st.title("مساعد السلامة الافتراضي (سالم) 🛡️")
st.subheader("إدارة محطة طاقة جازان 🏭")

# الحصول على المفتاح من Secrets
if "OPENAI_API_KEY" in st.secrets:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ خطأ: لم يتم العثور على مفتاح OpenAI في إعدادات Secrets.")
    st.stop()

# دالة لتحميل البيانات من مجلد data
@st.cache_resource
def load_data():
    data_path = "data/"
    documents = []
    
    if not os.path.exists(data_path):
        return None

    for file in os.listdir(data_path):
        file_path = os.path.join(data_path, file)
        if file.endswith(".pdf"):
            try:
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
            except Exception as e:
                st.warning(f"تعذر تحميل الملف {file}: {e}")
        elif file.endswith(".xlsx") or file.endswith(".xls"):
            try:
                loader = UnstructuredExcelLoader(file_path)
                documents.extend(loader.load())
            except Exception as e:
                st.warning(f"تعذر تحميل الملف {file}: {e}")
            
    if not documents:
        return None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore = FAISS.from_documents(texts, embeddings)
    return vectorstore

# تحميل البيانات
vectorstore = load_data()

if vectorstore:
    st.success("✅ تم تحميل قاعدة بيانات السلامة بنجاح! سالم جاهز لمساعدتك.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("اسأل سالم عن إجراءات السلامة في محطة جازان..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # إعداد سلسلة المحادثة
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_api_key),
            retriever=vectorstore.as_retriever(),
            memory=memory
        )

        with st.chat_message("assistant"):
            try:
                response = qa_chain.invoke({"question": prompt})
                full_response = response['answer']
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة الطلب: {e}")
else:
    st.info("👋 مرحباً بك. يرجى التأكد من وجود ملفات السلامة في مجلد data ليتوفر سالم للخدمة.")
