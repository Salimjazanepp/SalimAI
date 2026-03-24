import subprocess
import sys

# --- 🛠️ الجزء الأول: التثبيت التلقائي للمكتبات (حل مشكلة السطر 8) ---
def install_requirements():
    packages = [
        "langchain",
        "langchain-openai",
        "langchain-community",
        "faiss-cpu",
        "pdfplumber",
        "arabic-reshaper",
        "python-bidi",
        "pypdf",
        "openpyxl"
    ]
    for package in packages:
        try:
            # محاولة التحقق من وجود المكتبة
            dist_name = package.replace("-", "_")
            _import_(dist_name)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# تنفيذ التثبيت قبل بدء التطبيق
install_requirements()

# --- 🛡️ الجزء الثاني: استيراد المكتبات (بعد التثبيت) ---
import streamlit as st
import pandas as pd
import pdfplumber
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import arabic_reshaper
from bidi.algorithm import get_display

# --- إعدادات واجهة سالم ---
st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    [data-testid="stChatMessage"] {direction: rtl; text-align: right;}
    h1, h3, p {direction: rtl; text-align: right;}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("### 🏭 إدارة سلامة محطة طاقة جازان | نسخة مطورة")

# التحقق من مفتاح API
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ يرجى إضافة OPENAI_API_KEY في Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# --- وظائف المعالجة ---
@st.cache_resource
def process_files_to_vectorstore(files):
    all_docs = []
    for file in files:
        if file.name.endswith('.pdf'):
            with pdfplumber.open(file) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        all_docs.append(Document(page_content=text, metadata={"source": f"{file.name} - ص {i+1}"}))
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
            for index, row in df.iterrows():
                content = " | ".join([f"{col}: {val}" for col, val in row.items()])
                all_docs.append(Document(page_content=content, metadata={"source": f"{file.name} سجل رقم {index+1}"}))
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    splits = splitter.split_documents(all_docs)
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    return FAISS.from_documents(splits, embeddings)

# --- واجهة المستخدم ---
with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات PDF أو Excel", type=['pdf', 'xlsx'], accept_multiple_files=True)
    if st.button("🔄 مسح الذاكرة"):
        st.session_state.chat_history = []
        st.rerun()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if uploaded_files:
    with st.spinner("سالم يحلل البيانات..."):
        vs = process_files_to_vectorstore(tuple(uploaded_files))
        
        # إعداد محرك المحادثة
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=api_key)
        memory = ConversationBufferMemory(memory_key="chat_history", output_key="answer", return_messages=True)
        
        prompt_template = """أنت "سالم"، خبير سلامة في محطة جازان. أجب بدقة من النصوص فقط. 
        إذا كان هناك خطر، ابدأ بكلمة [تحذير].
        السياق: {context}
        السؤال: {question}
        الإجابة:"""
        
        QA_PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vs.as_retriever(search_kwargs={'k': 5}),
            memory=memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT}
        )

    # عرض المحادثة
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("اسأل سالم...")
    if user_input:
        st.chat_message("user").write(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            with st.spinner("جاري البحث..."):
                res = chain.invoke({"question": user_input})
                ans = res["answer"]
                st.markdown(ans)
                st.session_state.chat_history.append({"role": "assistant", "content": ans})
                
                with st.expander("📍 المصادر"):
                    for doc in res["source_documents"]:
                        st.write(f"- {doc.metadata['source']}")
else:
    st.info("👋 ارفع ملفات السلامة لتبدأ المحادثة مع سالم.")
