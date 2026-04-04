import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
from openai import OpenAI

# ------------------------
# 1. إعدادات الصفحة
# ------------------------
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")

# عرض السلوجن بلون أحمر غامق وعريض باستخدام Markdown بسيط (أضمن للتشغيل)
st.title("🛡️ مساعد السلامة الافتراضي (سالم)")
st.markdown("---")
st.markdown("### :red[إلتزم بالسلامة وخلك سالم]")
st.info("📑 نظام ذكي لملفات السلامة والموظفين - إدارة محطة طاقة جازان")
st.markdown("---")

# ------------------------
# 2. إعداد عميل OpenAI
# ------------------------
# تأكد أن المفتاح مضاف في الـ Secrets باسم OPENAI_API_KEY
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود في Secrets")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------------------
# 3. دالة تحميل ومعالجة البيانات
# ------------------------
@st.cache_resource
def load_all_data():
    data_path = "data/"
    docs = {}
    excel_data = {}

    if not os.path.exists(data_path):
        return {}, {}

    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]

    for file in files:
        path = os.path.join(data_path, file)
        text = ""

        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                for page in reader.pages:
                    t = page.extract_text()
                    if t: text += t + "\n"
            except:
                continue
        
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                excel_data[file] = df
                text = df.to_string()
            except:
                continue

        if text.strip():
            docs[file] = text

    return docs, excel_data

all_docs, excel_data = load_all_data()

# عرض الملفات للتأكد من تحميلها
with st.expander("📂 الملفات التي يقرأ منها سالم"):
    if all_docs:
        st.write(list(all_docs.keys()))
    else:
        st.warning("لا توجد ملفات في مجلد data")

# ------------------------
# 4. دوائر البحث (إكسل و PDF)
# ------------------------

def is_employee_query(query):
    keywords = ["من هو", "رقم", "جوال", "هاتف", "ايميل", "بريد", "موظف", "مدير", "تواصل", "بيانات"]
    return any(word in query.lower() for word in keywords)

def search_excel(query, excel_data):
    query_words = query.lower().split()
    for filename, df in excel_data.items():
        # بحث مرن في جميع الأعمدة
        mask = df.apply(lambda row: any(word in str(row.values).lower() for word in query_words), axis=1)
        result_df = df[mask]
        
        if not result_df.empty:
            row = result_df.iloc[0]
            res_text = f"### 📊 بيانات من ملف: {filename}\n\n"
            for col in df.columns:
                if pd.notna(row[col]):
                    res_text += f"- *{col}*: {row[col]}\n"
            return res_text
    return None

def get_smart_context(query, docs):
    query_words = query.lower().split()
    relevant_chunks = []
    
    for filename, content in docs.items():
        paragraphs = content.split('\n')
        for p in paragraphs:
            if len(p.strip()) < 15: continue
            if any(word in p.lower() for word in query_words):
                relevant_chunks.append(f"[{filename}]: {p.strip()}")
    
    return "\n".join(relevant_chunks[:20])

# ------------------------
# 5. واجهة المحادثة
# ------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("اسأل سالم..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # التحقق من إكسل أولاً
    excel_res = None
    if is_employee_query(question):
        excel_res = search_excel(question, excel_data)

    if excel_res:
        with st.chat_message("assistant"):
            st.markdown(excel_res)
        st.session_state.messages.append({"role": "assistant", "content": excel_res})
    else:
        # البحث في PDF باستخدام الذكاء الاصطناعي
        context = get_smart_context(question, all_docs)
        
        with st.chat_message("assistant"):
            if not context:
                answer = "المعذرة، لم أجد هذه المعلومة في ملفات السلامة المرفقة."
                st.markdown(answer)
            else:
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "أنت 'سالم' خبير السلامة في محطة جازان. أجب بدقة واذكر القواعد كاملة (خاصة إذا كانت 10 قواعد). استخدم النقاط."},
                            {"role": "user", "content": f"السياق:\n{context}\n\nالسؤال: {question}"}
                        ],
                        temperature=0
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                except Exception as e:
                    answer = "عذراً، واجهت مشكلة في الاتصال بالخادم."
                    st.error(f"Error: {e}")
            
            st.session_state.messages.append({"role": "assistant", "content": answer})
