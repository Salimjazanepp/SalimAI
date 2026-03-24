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

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="سالم - مساعد السلامة الذكي (GPC)", 
    page_icon="🛡️",
    layout="wide"
)

# --- واجهة المستخدم الرسومية العربي (تحسين العرض) ---
st.markdown("""
<style>
    .stTable {direction: rtl; text-align: right;}
    .stDataFrame {direction: rtl; text-align: right;}
    [data-testid="stChatMessage"] {direction: rtl; text-align: right;}
    h1, h2, h3, p {direction: rtl; text-align: right;}
</style>
""", unsafe_allow_html=True)

# --- العنوان والشعار ---
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("### 🏭 إدارة سلامة محطة طاقة جازان | نسخة مطورة 1.1")

# --- التحقق من المفتاح ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ يرجى إضافة OPENAI_API_KEY في ملف Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# ==========================================
# --- 🧠 وظائف المعالجة الأساسية ---
# ==========================================

# 1. تحسين معالجة النصوص العربية
def reshape_arabic(text):
    """يصلح النصوص العربية المقطعة أو المقلوبة من PDF."""
    if not text:
        return ""
    # إصلاح التشكيل والترابط
    reshaped_text = arabic_reshaper.reshape(text)
    # إصلاح الاتجاه (RTL)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# 2. تحسين استخراج النصوص من PDF (استخدام pdfplumber)
def extract_text_advanced(file):
    all_documents = []
    file_name = file.name
    
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            # استخراج النص الخام
            raw_text = page.extract_text(layout=True)
            
            # محاولة استخراج الجداول (ميزة جديدة قوية)
            tables = page.extract_tables()
            table_text = ""
            if tables:
                for table in tables:
                    # تحويل الجدول لنص مفصل
                    table_text += "\n---جدول بيانات---\n"
                    table_text += pd.DataFrame(table).to_string(index=False, header=False)
                    table_text += "\n----------------\n"

            final_page_content = f"{raw_text or ''}\n{table_text}"
            
            if final_page_content.strip():
                # ملاحظة: إذا كان الـ PDF عربي أصلي سليم، 
                # قد لا نحتاج reshaping. نستخدم النص الخام مباشرة.
                # نترك التصحيح فقط إذا كانت النصوص مقلوبة.
                all_documents.append(
                    Document(
                        page_content=final_page_content, # أو reshape_arabic(final_page_content)
                        metadata={"source": f"{file_name} - صفحة {i+1}"}
                    )
                )
    return all_documents

# 3. معالجة Excel المتقدمة (دمجها مع RAG)
def extract_excel_as_documents(file):
    documents = []
    # قراءة كل الشيتات
    excel_file = pd.ExcelFile(file)
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(file, sheet_name=sheet_name)
        
        # تحويل كل صف لوثيقة مستقلة
        # هذا يسمح للـ LLM بفهم سياق كل سجل (مثلاً: سجل حادث)
        for index, row in df.iterrows():
            # تحويل الصف لنص مقروء
            row_content = f"--- بيانات سجل (شيت: {sheet_name}) ---\n"
            for col in df.columns:
                row_content += f"{col}: {row[col]}\n"
            
            documents.append(
                Document(
                    page_content=row_content,
                    metadata={
                        "source": f"{file.name} - {sheet_name}",
                        "row_index": index
                    }
                )
            )
    return documents

# 4. بناء مخزن المتجهات (Vector Store)
@st.cache_resource
def build_vector_store(uploaded_files):
    all_docs = []
    
    for file in uploaded_files:
        if file.name.endswith('.pdf'):
            st.write(f"⏳ جاري معالجة PDF: {file.name}...")
            all_docs.extend(extract_text_advanced(file))
        elif file.name.endswith('.xlsx'):
            st.write(f"⏳ جاري معالجة Excel: {file.name}...")
            all_docs.extend(extract_excel_as_documents(file))
            
    if not all_docs:
        return None

    # تقسيم النصوص
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(all_docs)
    
    # حساب Embeddings وإنشاء المخزن
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    vectorstore = FAISS.from_documents(splits, embedding=embeddings)
    
    return vectorstore

# ==========================================
# --- 🏗️ بناء سلسلة المحادثة (Chain) ---
# ==========================================

def get_conversational_chain(vectorstore):
    # استخدام موديل أحدث (اختياري gpt-4-turbo)
    llm = ChatOpenAI(model_name="gpt-3.5-turbo-0125", temperature=0, openai_api_key=api_key)
    
    # 1. الذاكرة (للاحتفاظ بسياق الحوار)
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer", # مهمة جداً لإرجاع الإجابة فقط للذاكرة
        return_messages=True
    )
    
    # 2. برومبت مهندس خصيصاً لسلامة جازان (تحسين)
    qa_prompt_template = """
أنت "سالم"، مساعد السلامة المهنية الذكي الرسمي لمحطة طاقة جازان (GPC).
مهمتك هي تقديم إجابات دقيقة وموثوقة بناءً على المستندات المرفقة فقط.

القواعد الصارمة:
1. الشخصية: حافظ على نبرة مهنية، رسمية، ومساعدة. ابدأ بترحيب مهذب عند الحاجة.
2. التحذيرات أولاً: إذا كان السؤال يتعلق بخطر أو إجراء سلامة حرج، ابدأ إجابتك بتحذير واضح ومميز بـ *[تحذير]*.
3. التوثيق: اعتمد كلياً على النصوص المقدمة (Context). لا تخترع معلومات، لا تستخدم معلومات خارجية.
4. الخطوات: عند شرح إجراءات، استخدم القوائم الرقمية الممنهجة.
5. عدم المعرفة: إذا لم تجد الإجابة في النص، قل بوضوح: "المعذرة، لا تتوفر معلومات حول هذا الموضوع في أدلة المحطة المتوفرة حالياً". لا تحاول التخمين.
6. المصطلحات: استخدم المصطلحات الفنية كما هي في المستندات (عربي/إنجليزي).

النصوص المرجعية (Context):
----------------
{context}
----------------

سؤال المستخدم: {question}

الإجابة المعتمدة (تأكد من تطبيق القواعد):
"""
    QA_PROMPT = PromptTemplate(
        template=qa_prompt_template, input_variables=["context", "question"]
    )

    # 3. إنشاء السلسلة
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_type="mmr", search_kwargs={'k': 8, 'fetch_k': 20}),
        memory=memory,
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": QA_PROMPT} # تمرير البرومبت الخاص بنا
    )
    
    return chain

# ==========================================
# --- 💻 واجهة المستخدم والتفاعل ---
# ==========================================

# الشريط الجانبي (Sidebar)
with st.sidebar:
    st.header("📂 إدارة مستودع البيانات")
    
    # زر إعادة تعيين الذاكرة
    if st.button("🔄 بدء محادثة جديدة (مسح الذاكرة)"):
        st.session_state.chat_history = []
        st.session_state.chain_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        st.rerun()
        
    st.markdown("---")
    
    uploaded_files = st.file_uploader(
        "ارفع أدلة السلامة وسجلات الحوادث (PDF/Excel)",
        type=['pdf', 'xlsx'],
        accept_multiple_files=True,
        key="uploader"
    )

# تهيئة Session State للذاكرة والمحادثة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- المعالجة عند رفع الملفات ---
if uploaded_files:
    # تهيئة Vector Store إذا لم يكن موجوداً
    if "vectorstore" not in st.session_state:
        with st.spinner("🧠 سالم يقوم بتحليل وهيكلة الأدلة... قد يستغرق هذا دقيقة..."):
            vs = build_vector_store(uploaded_files)
            if vs:
                st.session_state.vectorstore = vs
                # إنشاء السلسلة مرة واحدة
                st.session_state.conversation_chain = get_conversational_chain(vs)
                st.success("✅ تم الانتهاء من فهرسة الأدلة. سالم جاهز للأسئلة!")
            else:
                st.error("❌ فشل معالجة الملفات. تأكد من محتواها.")

# --- عرض المحادثة السابقة ---
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- حقل الإدخال والاستجابة ---
user_query = st.chat_input("تحدث مع سالم حول إجراءات السلامة...")

if user_query:
    # 1. عرض سؤال المستخدم
    st.chat_message("user").write(user_query)
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    if "conversation_chain" not in st.session_state:
        with st.chat_message("assistant"):
            st.error("⚠️ يرجى رفع ملفات البيانات أولاً ليبدأ سالم العمل.")
    else:
        # 2. الحصول على الإجابة من سالم
        with st.chat_message("assistant"):
            with st.spinner("🤔 جاري البحث في الأدلة..."):
                response = st.session_state.conversation_chain.invoke({"question": user_query})
                
                answer = response["answer"]
                source_docs = response["source_documents"]

                # عرض الإجابة
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})

                # 3. عرض المصادر بشكل منسق (اختياري)
                if source_docs:
                    with st.expander("📍 تفاصيل المصادر المعتمدة"):
                        unique_sources = set()
                        for doc in source_docs:
                            # عرض جزء من النص المقتبس + المصدر
                            src = doc.metadata.get("source", "غير معروف")
                            if src not in unique_sources:
                                st.markdown(f"*- {src}*")
                                unique_sources.add(src)
                        
                            # (اختياري) عرض الاقتباس الفعلي
                            # st.caption(f"... {doc.page_content[:150]} ...")

else:
    if not uploaded_files:
        st.info("👋 مرحبًا، أنا سالم. للبدء، يرجى رفع أدلة السلامة الخاصة بمحطة جازان عبر الشريط الجانبي.")
