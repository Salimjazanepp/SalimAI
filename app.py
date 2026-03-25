import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# ------------------------
# إعداد المفتاح (الطريقة الصحيحة)
# ------------------------
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ لم يتم العثور على مفتاح OpenAI")
    st.stop()

openai.api_key = st.secrets["OPENAI_API_KEY"]

# ------------------------
# واجهة التطبيق
# ------------------------
st.set_page_config(page_title="سالم", page_icon="🛡️")
st.title("🛡️ مساعد السلامة الافتراضي (سالم)")
st.subheader("إدارة محطة طاقة جازان")

# ------------------------
# تحميل البيانات (مع فك التشفير)
# ------------------------
@st.cache_resource
def load_data():
    data_path = "data/"
    all_text = ""

    if not os.path.exists(data_path):
        return ""

    for file in os.listdir(data_path):
        path = os.path.join(data_path, file)

        # 📄 PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)

                # 🔥 فك التشفير (حتى لو بدون كلمة)
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except:
                        try:
                            reader.decrypt("1234")
                        except:
                            st.warning(f"⚠️ لم نستطع فك التشفير: {file}")
                            continue

                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"

            except Exception as e:
                st.warning(f"⚠️ خطأ في PDF: {file}")

        # 📊 Excel
        elif file.endswith(".xlsx") or file.endswith(".xls"):
            try:
                df = pd.read_excel(path)
                all_text += df.to_string() + "\n"
            except:
                st.warning(f"⚠️ خطأ في Excel: {file}")

    return all_text[:15000]  # عشان السرعة

# ------------------------
# تشغيل سالم
# ------------------------
data = load_data()

if data:
    st.success("✅ سالم جاهز ويقرأ جميع الملفات")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض المحادثة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # إدخال المستخدم
    if question := st.chat_input("اسأل سالم..."):
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "أنت خبير سلامة في محطة طاقة. أجب من البيانات فقط."
                        },
                        {
                            "role": "user",
                            "content": f"النص:\n{data}\n\nالسؤال:\n{question}"
                        }
                    ]
                )

                answer = response["choices"][0]["message"]["content"]

                st.write(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as e:
                st.error(f"❌ {e}")

else:
    st.info("📂 ضع ملفاتك داخل مجلد data")
