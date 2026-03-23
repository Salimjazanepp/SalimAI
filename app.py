import streamlit as st
import pandas as pd
from pypdf import PdfReader # المكتبة الجديدة الأسرع

st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

st.title("🛡️ مساعد السلامة الذكي (سالم)")

# التأكد من وجود المفتاح السري
if "OPENAI_API_KEY" not in st.secrets:
    st.error("الرجاء إضافة المفتاح السري في إعدادات Secrets")
    st.stop()

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات (PDF أو Excel)", type=['pdf', 'xlsx'], accept_multiple_files=True)

def process_files(files):
    all_data = ""
    for file in files:
        if file.name.endswith('.pdf'):
            reader = PdfReader(file)
            for page in reader.pages:
                content = page.extract_text()
                if content: all_data += content
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
            all_data += df.to_string()
    return all_data

if uploaded_files:
    with st.spinner("جاري تحليل البيانات..."):
        context = process_files(uploaded_files)
    st.success("تم تحميل الملفات بنجاح! سالم جاهز الآن.")
    
    user_query = st.text_input("اسأل سالم عن أي معلومة داخل الملفات:")
    
    if user_query:
        from langchain.chat_models import ChatOpenAI
        llm = ChatOpenAI(openai_api_key=st.secrets["OPENAI_API_KEY"], model_name="gpt-3.5-turbo")
        with st.spinner("سالم يفكر..."):
            response = llm.predict(f"بناءً على هذه البيانات: {context}\n\nالسؤال: {user_query}")
            st.info(response)
else:
    st.info("الرجاء رفع ملفات العمل من القائمة الجانبية ليبدأ سالم بالعمل.")
