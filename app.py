import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_openai import ChatOpenAI # التعديل هنا

# 1. إعدادات واجهة التطبيق
st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

# 2. التحقق من وجود المفتاح السري
if "OPENAI_API_KEY" not in st.secrets:
    st.error("خطأ: يرجى إضافة OPENAI_API_KEY في إعدادات Secrets")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# 3. دالة معالجة الملفات
def process_files(files):
    all_data = ""
    for file in files:
        try:
            if file.name.endswith('.pdf'):
                reader = PdfReader(file)
                if reader.is_encrypted:
                    try: reader.decrypt("")
                    except: pass
                for page in reader.pages:
                    content = page.extract_text()
                    if content: all_data += content + "\n"
            elif file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                df = pd.read_excel(file)
                all_data += f"\nبيانات ملف {file.name}:\n" + df.to_string() + "\n"
        except Exception as e:
            st.warning(f"تعذر قراءة {file.name}")
    return all_data

# 4. واجهة المستخدم
st.title("🛡️ مساعد السلامة الذكي (سالم)")

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات (PDF أو Excel)", type=['pdf', 'xlsx', 'xls'], accept_multiple_files=True)

# 5. منطق الرد
if uploaded_files:
    with st.spinner("جاري تحليل ملفاتك..."):
        context_data = process_files(uploaded_files)
    
    if context_data:
        st.success("سالم جاهز للرد!")
        user_query = st.chat_input("اسأل سالم عن أي معلومة...")
        
        if user_query:
            with st.chat_message("user"): st.write(user_query)
            try:
                llm = ChatOpenAI(api_key=api_key, model_name="gpt-3.5-turbo", temperature=0.3)
                with st.chat_message("assistant"):
                    with st.spinner("سالم يفكر..."):
                        prompt = f"أنت مساعد اسمك سالم. بناءً على هذه البيانات:\n{context_data}\n\nسؤال المستخدم: {user_query}"
                        response = llm.invoke(prompt) # تم التعديل لـ invoke
                        st.write(response.content)
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
else:
    st.info("الرجاء رفع الملفات للبدء.")
