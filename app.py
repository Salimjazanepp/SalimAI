import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
from openai import OpenAI

# ------------------------
# 1. إعدادات الصفحة والستايل
# ------------------------
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️", layout="centered")

# تنسيق السلوجن بلون مميز
st.markdown("""
    <style>
    .slogan {
        color: #FF4B4B;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        border: 2px solid #FF4B4B;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_stdio=True)

st.title("🛡️ مساعد السلامة الافتراضي (سالم)")
st.markdown('<div class="slogan">إلتزم بالسلامة وخلك سالم</div>', unsafe_allow_html=True)
st.info("📑 نظام ذكي لملفات السلامة والموظفين - إدارة محطة طاقة جازان")

# ------------------------
# 2. إعداد عميل OpenAI (الإصدار الجديد)
# ------------------------
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
            except Exception as e:
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

with st.expander("📂 الملفات المتوفرة في النظام"):
    st.write(list(all_docs.keys()))

# ------------------------
# 4. منطق البحث الذكي
# ------------------------

def is_employee_query(query):
    keywords = ["من هو", "رقم", "جوال", "هاتف", "ايميل", "بريد", "موظف", "مدير", "تواصل"]
    return any(word in query.lower() for word in keywords)

def search_excel(query, excel_data):
    query_words = query.lower().split()
    for filename, df in excel_data.items():
        # تحويل الصفوف لنصوص للبحث السريع
        mask = df.apply(lambda row: any(word in str(row.values).lower() for word in query_words), axis=1)
        result_df = df[mask]
        
        if not result_df.empty:
            row = result_df.iloc[0]
            res_text = f"### 📊 بيانات من: {filename}\n\n"
            for col in df.columns:
                if pd.notna(row[col]):
                    res_text += f"- *{col}*: {row[col]}\n"
            return res_text
    return None

def get_smart_context(query, docs):
    """تقسيم النص لفقرات والبحث عن الأكثر صلة لمنع تشتت النموذج"""
    query_words = query.lower().split()
    relevant_chunks = []
    
    for filename, content in docs.items():
        # تقسيم النص لفقرات بناءً على السطور الجديدة
        paragraphs = content.split('\n')
        for p in paragraphs:
            if len(p.strip()) < 20: continue # تخطي السطور القصيرة
            if any(word in p.lower() for word in query_words):
                relevant_chunks.append(f"[{filename}]: {p.strip()}")
    
    # نأخذ أهم 25 فقرة متعلقة بالسؤال لضمان الدقة
    return "\n".join(relevant_chunks[:25])

# ------------------------
# 5. واجهة المحادثة
# ------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("اسأل سالم عن قواعد السلامة أو الموظفين..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # أولاً: البحث في إكسل (للموظفين)
    if is_employee_query(question):
        excel_res = search_excel(question, excel_data)
        if excel_res:
            with st.chat_message("assistant"):
                st.markdown(excel_res)
            st.session_state.messages.append({"role": "assistant", "content": excel_res})
            st.stop()

    # ثانياً: البحث في PDF (باستخدام GPT-4o-mini)
    context = get_smart_context(question, all_docs)
    
    with st.chat_message("assistant"):
        if not context:
            answer = "المعذرة، لم أجد معلومة مطابقة لسؤالك في الملفات المرفقة."
            st.markdown(answer)
        else:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini", # الموديل الأحدث والأذكى
                    messages=[
                        {
                            "role": "system", 
                            "content": "أنت 'سالم' خبير السلامة. إجابتك يجب أن تكون مستمدة فقط من النص المقدم. إذا كان هناك تعداد (مثل قواعد الحياة) اذكرها كاملة كما هي في النص. كن دقيقاً جداً في الأرقام."
                        },
                        {"role": "user", "content": f"النص المستخرج:\n{context}\n\nالسؤال: {question}"}
                    ],
                    temperature=0 # لضمان عدم التأليف
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
            except Exception as e:
                answer = f"⚠️ حدث خطأ في الاتصال: {str(e)}"
                st.error(answer)
        
        st.session_state.messages.append({"role": "assistant", "content": answer})
