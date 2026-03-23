import streamlit as st
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("يرجى إضافة المفتاح في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

st.title("🛡️ مساعد السلامة الذكي (سالم)")

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات PDF", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    # 1. قراءة النصوص
    text = ""
    for file in uploaded_files:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    
    # 2. تقسيم النص إلى أجزاء صغيرة (عشان ما نتجاوز الليمت)
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    
    # 3. إنشاء قاعدة بيانات للبحث السريع
    with st.spinner("سالم يحلل البيانات الضخمة..."):
        embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        vectorstore = FAISS.from_texts(texts=chunks, embedding=embeddings)
        st.success("سالم جاهز الآن ومستعد لأسئلتك!")

    # 4. نظام السؤال والجواب
    user_query = st.chat_input("اسأل سالم عن أي معلومة...")
    if user_query:
        with st.chat_message("user"): st.write(user_query)
        
        qa = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=api_key),
            chain_type="stuff",
            retriever=vectorstore.as_retriever()
        )
        
        with st.chat_message("assistant"):
            with st.spinner("يبحث في الملفات..."):
                response = qa.run(user_query)
                st.write(response)
else:
    st.info("ارفع الملفات الكبيرة وسأقوم بتقسيمها وفهمها لك.")
