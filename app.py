import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
from openai import OpenAI

# ------------------------
# واجهة التطبيق
# ------------------------
st.set_page_config(page_title="مساعد السلامة الافتراضي (سالم)", page_icon="🛡️")
st.title("مساعد السلامة الافتراضي (سالم) 🛡️")
st.subheader("إدارة محطة طاقة جازان 🏭")

# ------------------------
# API KEY
# ------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ لم يتم العثور على مفتاح OpenAI")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------------------
# تحميل البيانات
# ------------------------
@st.cache_resource
def load_data():
    data_path = "data/"
    all_text = ""

    if not os.path.exists(data_path):
        return ""

    for file in os.listdir(data_path):
        file_path = os.path.join(data_path, file)

        # PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(file_path)

                if reader.is_encrypted:
                    st.warning(f"⚠️ تم تجاهل ملف مشفر: {file}")
                    continue

                for page in reader.pages:
                    all_text += page.extract_text() or ""

            except:
                st.warning(f"⚠️ مشكلة في PDF: {file}")

        # Excel
        elif file.endswith(".xlsx") or file.endswith(".xls"):
            try:
                df = pd.read_excel(file_path)
                all_text += df.to_string()
            except:
                st.warning(f"⚠️ مشكلة في Excel: {file}")

    return all_text[:15000]  # 🔥 نحدد الحجم عشان السرعة

# ------------------------
# تشغيل سالم
# ------------------------
data_text = load_data()

if data_text:
    st.success("✅ سالم جاهز")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض المحادثة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # إدخال المستخدم
    if prompt := st.chat_input("اسأل سالم عن السلامة..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "أنت مساعد سلامة مهنية. أجب فقط من المعلومات المعطاة."
                        },
                        {
                            "role": "user",
                            "content": f"النص:\n{data_text}\n\nالسؤال:\n{prompt}"
                        }
                    ]
                )

                answer = response.choices[0].message.content

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as e:
                st.error(f"❌ خطأ: {e}")

else:
    st.info("📂 ضع ملفاتك داخل مجلد data")
