import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader

# إعدادات الواجهة
st.set_page_config(page_title="سالم - مساعد السلامة الذكي", page_icon="🛡️")

st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("---")

# القائمة الجانبية لرفع البيانات
with st.sidebar:
    st.header("📂 مستودع البيانات")
    uploaded_files = st.file_uploader("ارفع ملفات (PDF أو Excel)", 
                                    type=['pdf', 'xlsx'], 
                                    accept_multiple_files=True)

# دالة لقراءة النصوص من الملفات المرفوعة
def process_files(files):
    all_data = ""
    for file in files:
        if file.name.endswith('.pdf'):
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                all_data += page.extract_text()
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
            all_data += df.to_string()
    return all_data

# منطق المحادثة
if uploaded_files:
    context = process_files(uploaded_files)
    st.success(f"تم تحميل {len(uploaded_files)} ملفات بنجاح!")
    
    user_query = st.text_input("اسأل سالم عن أي معلومة داخل الملفات:")
    
    if user_query:
        # ملاحظة: هنا نحتاج لربط OpenAI للرد بذكاء
        # حالياً سنقوم ببحث بسيط حتى نضع مفتاح الـ API
        if user_query.lower() in context.lower():
            st.info("🤖 سالم يبحث الآن...")
            st.write("وجدت معلومات متعلقة بسؤالك في الملفات المرفوعة.")
        else:
            st.warning("لم أجد هذه المعلومة بدقة، يرجى التأكد من محتوى الملفات.")
else:
    st.info("الرجاء رفع ملفات العمل من القائمة الجانبية ليبدأ سالم بالعمل.")

st.markdown("---")
st.caption("تطوير نظام سالم للسلامة المهنية - 2026")
