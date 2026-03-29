import streamlit as st
import os
import pandas as pd
from pypdf import PdfReader
import openai

# --- 1. إعداد المفتاح ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود")
    st.stop()
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- 2. الواجهة والسلوجن ---
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("<h3 style='color: #2E7D32;'>إلتزم بالسلامة.. وخلك سالم</h3>", unsafe_allow_html=True)
st.info("📑 نظام بحث متطور لجميع ملفات السلامة - إدارة محطة طاقة جازان")
st.divider()

# --- 3. تحميل البيانات (PDF بشمولية أكبر & Excel بدقة) ---
@st.cache_resource
def load_all_data():
    data_path = "data/"
    docs = {}
    if not os.path.exists(data_path): return {}
    files = [f for f in os.listdir(data_path) if f.endswith(('.pdf', '.xlsx', '.xls'))]

    for file in files:
        path = os.path.join(data_path, file)
        text = ""
        if file.endswith(".pdf"):
            try:
                reader = PdfReader(path)
                # رفعنا القراءة لـ 25 صفحة لضمان الوصول لصلب القواعد والتفاصيل
                for page in reader.pages[:25]:
                    t = page.extract_text()
                    if t: text += t
            except: continue
        elif file.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(path)
                text = df.to_string()
            except: continue
        if text.strip():
            docs[file] = text
    return docs

all_docs = load_all_data()

# --- 4. محرك البحث المتنوع (توزيع الذاكرة) ---
def get_relevant_context(query, docs):
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()
        score = sum(15 for word in query_words if word in filename_lower)
        score += sum(1 for word in query_words if word in content_lower)
        if score > 0:
            scored_docs.append((score, filename, content))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    # توزيع الذاكرة لضمان رؤية تفاصيل أكثر من الملف الأول
    for i in range(min(3, len(scored_docs))):
        score, filename, content = scored_docs[i]
        # إذا كان هو الملف الأول (الأكثر صلة)، نعطيه مساحة أكبر (5000 حرف)
        limit = 5000 if i == 0 else 2500
        context += f"\n\n[مستند {i+1}: {filename}]\n{content[:limit]}\n"
    return context[:12000]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# --- 6. الإدخال والرد الاحترافي ---
if question := st.chat_input("اسأل سالم عن أي تفصيل..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"): st.write(question)

    context = get_relevant_context(question, all_docs)

    with st.chat_message("assistant"):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {
                        "role": "system",
                        "content": """أنت خبير سلامة محترف في محطة جازان (سالم). 
                        مهمتك هي تقديم إجابة شاملة، مرتبة، وشيقة من النصوص المرفقة.
                        - استخدم العناوين العريضة (Bold) لتقسيم الإجابة.
                        - استخدم النقاط (Bullet points) لشرح التفاصيل والخطوات.
                        - إذا وجد عدد معين (مثل 10 قواعد)، اذكر العدد ثم فصّل النقاط.
                        - لا تكتفِ بالملخص، بل استخرج التفاصيل الفنية الموجودة.
                        - ابدأ الرد بترحيب مهني بسيط.
                        - اذكر اسم الملف المرجعي في نهاية الإجابة."""
                    },
                    {"role": "user", "content": f"السؤال: {question}\n\nالنصوص المتاحة:\n{context}"}
                ],
                temperature=0.2 # درجة بسيطة من المرونة لإعطاء تنسيق أجمل
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ خطأ فني: {e}")
