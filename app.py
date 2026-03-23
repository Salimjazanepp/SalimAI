import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter # تعديل هنا
from langchain.chains import RetrievalQA

st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("يرجى إضافة المفتاح في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

st.title("🛡️ مساعد السلامة الذكي (سالم)")

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات العمل (PDF أو Excel)", type=['pdf', 'xlsx'], accept_multiple_files=True)

def get_text(files):
    all_text = ""
    for file in files:
        try:
            if file.name.endswith('.pdf'):
                reader = PdfReader(file)
                for page in reader.pages:
                    all_text += page.extract_text() + "\n"
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
                all_text += df.to_string() + "\n"
        except:
            continue
    return all_text

if uploaded_files:
    raw_text = get_text(uploaded_files)
    
    if raw_text:
        # تقسيم النص لقطع صغيرة للبحث
        text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(raw_text)
        
        with st.spinner("سالم يحلل البيانات..."):
            try:
                embeddings = OpenAIEmbeddings(openai_api_key=api_key)
                vectorstore = FAISS.from_texts(texts=chunks, embedding=embeddings)
                st.success("سالم جاهز للرد!")

                user_query = st.chat_input("اسأل سالم...")
                if user_query:
                    with st.chat_message("user"): st.write(user_query)
                    
                    qa = RetrievalQA.from_chain_type(
                        llm=ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=api_key),
                        chain_type="stuff",
                        retriever=vectorstore.as_retriever()
                    )
                    
                    with st.chat_message("assistant"):
                        response = qa.invoke(user_query)
                        st.write(response["result"])
            except Exception as e:
                st.error(f"حدث خطأ فني: {e}")
    else:
        st.warning("لم يتم العثور على نص داخل الملفات.")
else:
    st.info("ارفع ملفاتك لتبدأ المحادثة مع سالم.")
