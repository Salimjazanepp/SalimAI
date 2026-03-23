import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain.chat_models import ChatOpenAI

# 1. إعدادات واجهة التطبيق
st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

# 2. التحقق من وجود المفتاح السري (API Key) في إعدادات Secrets
if "OPENAI_API_KEY" not in st.secrets:
    st.error("خطأ: لم يتم العثور على مفتاح OpenAI. يرجى إضافته في إعدادات Secrets باسم OPENAI_API_KEY")
    st.stop()

api_key = st.secrets["OPENAI_API_KEY"]

# 3. دالة معالجة واستخراج النصوص من الملفات المرفوعة
def process_files(files):
    all_data = ""
    for file in files:
        try:
            if file.name.endswith('.pdf'):
                reader = PdfReader(file)
                # معالجة الملفات المشفرة أو المحمية
                if reader.is_encrypted:
                    try:
                        reader.decrypt("") # محاولة الفتح بدون كلمة سر
                    except:
                        pass
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        all_data += content + "\n"
            
            elif file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                df = pd.read_excel(file)
                all_data += f"\nبيانات ملف {file.name}:\n" + df.to_string() + "\n"
        
        except Exception as e:
            st.warning(f"تعذر قراءة الملف {file.name} بالكامل. سيحاول سالم المتابعة بما لديه.")
    return all_data

# 4. واجهة المستخدم (العنوان والقائمة الجانبية)
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("أنا مساعدك الذكي، ارفع ملفات العمل وسأجيب على استفساراتك بناءً عليها.")

with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات (PDF أو Excel)", type=['pdf', 'xlsx', 'xls'], accept_multiple_files=True)
    if uploaded_files:
        if st.button("تفريغ الذاكرة"):
            st.rerun()

# 5. منطق المحادثة والرد
if uploaded_files:
    with st.spinner("جاري تحليل ملفاتك، يرجى الانتظار..."):
        context_data = process_files(uploaded_files)
    
    if context_data:
        st.success(f"تم تحليل {len(uploaded_files)} ملفات بنجاح! سالم جاهز للرد.")
        
        # خانة السؤال
        user_query = st.chat_input("اسأل سالم عن أي معلومة داخل ملفاتك...")
        
        if user_query:
            # عرض سؤال المستخدم
            with st.chat_message("user"):
                st.write(user_query)
            
            # معالجة الرد عبر OpenAI
            try:
                llm = ChatOpenAI(openai_api_key=api_key, model_name="gpt-3.5-turbo", temperature=0.3)
                with st.chat_message("assistant"):
                    with st.spinner("سالم يفكر..."):
                        prompt = f"أنت مساعد خبير اسمك 'سالم'. استخدم المعلومات التالية فقط للرد على سؤال المستخدم.\nالمعلومات:\n{context_data}\n\nسؤال المستخدم: {user_query}"
                        response = llm.predict(prompt)
                        st.write(response)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بعقل سالم: {e}")
    else:
        st.warning("لم يتم استخراج نصوص واضحة من الملفات. تأكد أنها ليست صوراً فقط.")
else:
    st.info("الرجاء رفع ملفات العمل (PDF أو Excel) من القائمة الجانبية للبدء.")

st.markdown("---")
st.caption("تطوير نظام سالم للسلامة المهنية - 2026")
