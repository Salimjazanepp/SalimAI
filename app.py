import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# --- 1. إعداد المفتاح (OpenAI API Key) ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود في Secrets")
    st.stop()
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="سالم - مساعد السلامة", page_icon="🛡️")
st.title("🛡️ مساعد السلامة الافتراضي (سالم)")
st.caption("خبير أنظمة السلامة - محطة طاقة جازان")

# --- 3. دالة جلب البيانات الذكية ---
@st.cache_resource
def load_all_data():
    data_path = "data/"
    all_text = ""
    
    if not os.path.exists(data_path):
        return ""

    # جلب قائمة الملفات (PDF و Excel)
    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]
    
    for file in files:
        path = os.path.join(data_path, file)
        # وضع علامة واحدة واضحة لكل ملف ليفصل بين المواضيع
        file_header = f"\n\n[المصدر: {file}]\n"
        
        # قراءة الـ PDF
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                text_content = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text
                all_text += file_header + text_content
            except:
                continue
        
        # قراءة الـ Excel
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                all_text += file_header + df.to_string()
            except:
                continue
                
    # رفعنا الحد لـ 60 ألف حرف لضمان شمولية السقالات، الهواء، والمرتفعات
    return all_text[:60000]

# --- 4. تشغيل قاعدة البيانات ---
knowledge_base = load_all_data()

# --- 5. نظام المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل القديمة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# إدخال سؤال المستخدم
if question := st.chat_input("اسأل سالم عن أي موضوع (مرتفعات، سقالات، جودة هواء...)"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        try:
            # استخدام موديل 16k لاستيعاب النصوص الكبيرة
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system", 
                        "content": "أنت خبير سلامة في محطة جازان. أمامك نصوص من عدة ملفات. ابحث في المصدر المناسب للسؤال (سواء كان عن السقالات أو جودة الهواء أو غيرها) وأعطِ إجابة دقيقة وتفصيلية. لا تخلط بين المواضيع."
                    },
                    {
                        "role": "user", 
                        "content": f"المعلومات المتوفرة من الملفات:\n{knowledge_base}\n\nالسؤال: {question}"
                    }
                ],
                temperature=0.2 # درجة حرارة منخفضة لضمان الدقة وعدم التأليف
            )
            
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            st.error(f"⚠️ حدث خطأ فني: {e}")

# في حال عدم وجود ملفات
if not knowledge_base:
    st.info("📂 الرجاء التأكد من وجود ملفات PDF في مجلد data على GitHub.")
