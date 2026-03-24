import subprocess
import sys
import os

# --- 🚀 المرحلة 1: تثبيت المكتبات إجبارياً ---
def install_packages():
    packages = [
        "langchain", "langchain-openai", "langchain-community", 
        "faiss-cpu", "pdfplumber", "arabic-reshaper", 
        "python-bidi", "pypdf", "openpyxl", "langchain-core"
    ]
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# تنفيذ التثبيت فوراً عند التشغيل
if "INSTALLED_SUCCESS" not in os.environ:
    install_packages()
    os.environ["INSTALLED_SUCCESS"] = "True"

# --- 🛡️ المرحلة 2: استيراد المكتبات الأساسية فقط ---
import streamlit as st
import pandas as pd

# --- إعدادات واجهة سالم ---
st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️", layout="wide")

st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("### 🏭 إدارة سلامة محطة طاقة جازان")

# التحقق من مفتاح API
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ خطأ: أضف OPENAI_API_KEY في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# --- 🧠 المرحلة 3: استدعاء مكتبات الذكاء الاصطناعي "عند الحاجة فقط" ---
# نقلنا الـ imports هنا لضمان أنها لن تعمل إلا بعد التثبيت أعلاه
def get_ai_tools():
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from langchain.chains import ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate
    import pdfplumber
    return OpenAIEmbeddings, ChatOpenAI, FAISS, RecursiveCharacterTextSplitter, Document, ConversationalRetrievalChain, ConversationBufferMemory, PromptTemplate, pdfplumber

# --- معالجة الملفات ---
@st.cache_resource
def process_data(files):
    # استدعاء الأدوات
    OpenAIEmbeddings, ChatOpenAI, FAISS, RecursiveCharacterTextSplitter, Document, _, _, _, pdfplumber = get_ai_tools()
    
    docs = []
    for f in files:
        if f.name.endswith('.pdf'):
            with pdfplumber.open(f) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        docs.append(Document(page_content=text, metadata={"source": f"{f.name} (ص{i+1})"}))
        elif f.name.endswith('.xlsx'):
            df = pd.read_excel(f)
            for i, row in df.iterrows():
                content = " | ".join([f"{c}: {v}" for c, v in row.items()])
                docs.append(Document(page_content=content, metadata={"source": f"{f.name} (سجل{i+1})"}))
    
    if not docs: return None
    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(docs)
    return FAISS.from_documents(splits, OpenAIEmbeddings(openai_api_key=api_key))

# --- المحادثة ---
with st.sidebar:
    st.header("📂 المستندات")
    uploaded = st.file_uploader("ارفع الملفات", type=['pdf', 'xlsx'], accept_multiple_files=True)
    if st.button("🔄 مسح الذاكرة"):
        st.session_state.chat_history = []
        st.rerun()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if uploaded:
    # استدعاء الأدوات اللازمة للمحادثة
    _, ChatOpenAI, _, _, _, ConversationalRetrievalChain, ConversationBufferMemory, PromptTemplate, _ = get_ai_tools()
    
    with st.spinner("سالم يحلل البيانات..."):
        vs = process_data(tuple(uploaded))
        if vs:
            llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=api_key)
            memory = ConversationBufferMemory(memory_key="chat_history", output_key="answer", return_messages=True)
            
            template = "أنت سالم، خبير سلامة في محطة جازان. أجب من النصوص فقط.\nسياق: {context}\nسؤال: {question}\nإجابة:"
            
            chain = ConversationalRetrievalChain.from_llm(
                llm=llm, retriever=vs.as_retriever(), memory=memory, return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": PromptTemplate(template=template, input_variables=["context", "question"])}
            )

            for m in st.session_state.chat_history:
                st.chat_message(m["role"]).write(m["content"])

            query = st.chat_input("اسأل سالم...")
            if query:
                st.chat_message("user").write(query)
                st.session_state.chat_history.append({"role": "user", "content": query})
                
                with st.chat_message("assistant"):
                    res = chain.invoke({"question": query})
                    st.write(res["answer"])
                    st.session_state.chat_history.append({"role": "assistant", "content": res["answer"]})
else:
    st.info("👋 ارفع ملفات السلامة لتبدأ المحادثة مع سالم.")
