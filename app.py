import subprocess
import sys

# --- 🛠️ الجزء الأول: التثبيت التلقائي للمكتبات (نسخة مصححة) ---
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
            _import_(dist_name) # تم تصحيح الشرطات السفلية هنا
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# تنفيذ التثبيت
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

# تنسيق الواجهة لتناسب اللغة العربية
st.markdown("""
<style>
    [data-testid="stChatMessage"] {direction: rtl; text-align: right;}
    h1, h3, p {direction: rtl; text-align: right;}
    .stMarkdown {direction: rtl; text-align: right;}
</style>
""", unsafe_allow_html=True)

st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("### 🏭 إدارة سلامة محطة طاقة جازان | النسخة الاحترافية")

# التحقق من مفتاح API من Secrets
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ خطأ: لم يتم العثور على مفتاح OpenAI في إعدادات Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# --- وظائف المعالجة الذكية ---
@st.cache_resource
def process_files_to_vectorstore(files):
    all_docs = []
    for file in files:
        try:
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
                    all_docs.append(Document(page_content=content, metadata={"source": f"{file.name} سجل {index+1}"}))
        except Exception as e:
            st.warning(f"تعذر معالجة الملف {file.name}: {str(e)}")
    
    if not all_docs:
        return None

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    splits = splitter.split_documents(all_docs)
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    return FAISS.from_documents(splits, embeddings)

# --- واجهة المستخدم ---
with st.sidebar:
    st.header("📂 إدارة المستندات")
    uploaded_files = st.file_uploader("ارفع ملفات السلامة (PDF/Excel)", type=['pdf', 'xlsx'], accept_multiple_files=True)
    if st.button("🔄 تفريغ ذاكرة المحادثة"):
        if "chat_history" in st.session_state:
            st.session_state.chat_history = []
        st.rerun()

# تهيئة سجل المحادثة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if uploaded_files:
    with st.spinner("سالم يقوم بتحليل المستندات الآن..."):
        vs = process_files_to_vectorstore(tuple(uploaded_files))
        
        if vs:
            # إعداد محرك الذكاء الاصطناعي
            llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=api_key)
            memory = ConversationBufferMemory(memory_key="chat_history", output_key="answer", return_messages=True)
            
            prompt_template = """أنت "سالم"، مساعد سلامة مهنية خبير في محطة طاقة جازان.
            أجب على الأسئلة بناءً على المستندات المرفقة فقط.
            إذا كان السؤال يتعلق بإجراء خطير، ابدأ بكلمة *[تحذير]* بخط عريض.
            استخدم القوائم المنظمة في الإجابة.
            
            النصوص المرجعية:
            {context}
            
            سؤال المستخدم: {question}
            
            الإجابة المعتمدة:"""
            
            QA_PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
            
            chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=vs.as_retriever(search_kwargs={'k': 5}),
                memory=memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": QA_PROMPT}
            )

            # عرض المحادثة التاريخية
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            # إدخال سؤال جديد
            user_input = st.chat_input("اسأل سالم عن أي شيء في ملفات السلامة...")
            if user_input:
                with st.chat_message("user"):
                    st.write(user_input)
                
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                with st.chat_message("assistant"):
                    with st.spinner("يبحث سالم في الأدلة..."):
                        res = chain.invoke({"question": user_input})
                        ans = res["answer"]
                        st.markdown(ans)
                        st.session_state.chat_history.append({"role": "assistant", "content": ans})
                        
                        # عرض المصادر
                        with st.expander("📍 مراجع الإجابة من ملفاتك"):
                            sources = set([doc.metadata['source'] for doc in res["source_documents"]])
                            for s in sources:
                                st.write(f"- {s}")
        else:
            st.error("لم يتم العثور على نصوص صالحة في الملفات المرفوعة.")
else:
    st.info("👋 أهلاً بك. أنا سالم، مساعدك الذكي. يرجى رفع ملفات إجراءات السلامة من القائمة الجانبية لنبدأ.")
