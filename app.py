import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# ------------------------
# إعداد المفتاح
# ------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ لم يتم العثور على مفتاح OpenAI في Secrets")
    st.stop()

# تحديث طريقة استدعاء المفتاح للنسخ الجديدة
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ------------------------
# واجهة التطبيق
# ------------------------
st.set_page_config(page_title="سالم", page_icon="🛡️")
st.title("🛡️ مساعد السلامة الافتراضي (سالم)")
st.subheader("إدارة محطة طاقة جازان")

# ------------------------
# تحميل البيانات (محسن للملفات المفتوحة)
# ------------------------
@st.cache_resource
def load_data():
    data_path = "data/"
    all_text = ""

    if not os.path.exists(data_path):
        return ""

    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]
    
    if not files:
        return ""

    for file in files:
        path = os.path.join(data_path, file)

        # 📄 معالجة الـ PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                # قراءة النص مباشرة لأن الملفات الآن unlocked
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        all_text += f"\n--- مصدر: {file} ---\n" + text
            except Exception as e:
                st.warning(f"⚠️ تعذر قراءة PDF: {file}")

        # 📊 معالجة الـ Excel
        elif file.endswith(".xlsx") or file.endswith(".xls"):
            try:
                df = pd.read_excel(path)
                all_text += f"\n--- مصدر بيانات: {file} ---\n" + df.to_string() + "\n"
            except:
                st.warning(f"⚠️ تعذر قراءة Excel: {file}")

    # زيادة حجم القراءة قليلاً لضمان شمولية المعلومات
    return all_text[:25000] 

# ------------------------
# تشغيل سالم
# ------------------------
data = load_data()

if data:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض المحادثة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # إدخال المستخدم
    if question := st.chat_input("اسأل سالم عن إجراءات السلامة..."):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            try:
                # استخدام موديل أحدث وأسرع
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-16k", # نسخة تدعم نصوص أطول
                    messages=[
                        {
                            "role": "system", 
                            "content": "أنت خبير سلامة في محطة طاقة جازان. استخدم البيانات المقدمة فقط للإجابة بدقة وتفصيل."
                        },
                        {
                            "role": "user", 
                            "content": f"استخرج الإجابة من النص التالي:\n\n{data}\n\nالسؤال: {question}"
                        }
                    ],
                    temperature=0.2 # لجعل الإجابة واقعية ومباشرة من النص
                )

                answer = response["choices"][0]["message"]["content"]
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"❌ حدث خطأ في الاتصال: {e}")
else:
    st.info("📂 سالم جاهز، تأكد من رفع ملفات الـ PDF المفتوحة في مجلد data على GitHub.")
