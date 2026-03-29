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

# --- 3. تحميل البيانات (قراءة شاملة للمحتوى) ---
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
                # نأخذ أول 35 صفحة لضمان تغطية أدلة السلامة الضخمة بالكامل
                for page in reader.pages[:35]:
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

# --- 4. محرك البحث الذكي (نظام القفز لتجاوز المقدمات) ---
def get_relevant_context(query, docs):
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # حساب النقاط (أولوية عالية لاسم الملف)
        score = sum(20 for word in query_words if word in filename_lower)
        score += sum(2 for word in query_words if word in content_lower)
        
        if score > 0:
            # ✨ ميزة القفز الذكي: ابحث عن موقع أول كلمة مفتاحية في النص
            start_index = 0
            found_indices = [content_lower.find(word) for word in query_words if content_lower.find(word) != -1]
            
            if found_indices:
                first_match = min(found_indices)
                # إذا كانت الكلمة بعيدة (بعد أول 1000 حرف)، ابدأ القراءة من قبلها بـ 300 حرف
                if first_match > 1000:
                    start_index = first_match - 300
            
            scored_docs.append((score, filename, content[start_index:]))

    # ترتيب النتائج
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    # نأخذ أفضل 3 ملفات ونعطي مساحة كبيرة للملف الأول (الأساسي)
    for i in range(min(3, len(scored_docs))):
        score, filename, content = scored_docs[i]
        limit = 7000 if i == 0 else 3000 # 7000 حرف للمصدر الأساسي كافية لذكر الـ 10 قواعد بالتفصيل
        context += f"\n\n[المصدر رقم {i+1}: {filename}]\n{content[:limit]}\n"
    
    return context[:14000]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# --- 6. الإدخال وتوليد الرد الاحترافي ---
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
                        مهمتك تقديم إجابة شاملة ومفصلة ومرتبة.
                        - لا تكتفِ بذكر الفصول (مثل مقدمة، نطاق)، بل ادخل في صلب التفاصيل الفنية.
                        - إذا كان السؤال عن قواعد، اذكرها جميعاً مع شرح مبسط لكل قاعدة.
                        - استخدم العناوين العريضة (Bold) والقوائم النقطية.
                        - اجعل أسلوبك توعوياً ومهنياً.
                        - اذكر اسم الملف المرجعي بوضوح في نهاية الرد."""
                    },
                    {"role": "user", "content": f"السؤال: {question}\n\nالنصوص المتاحة من ملفاتك:\n{context}"}
                ],
                temperature=0.2
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ عذراً، حدث خطأ فني: {e}")
