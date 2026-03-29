import streamlit as st
import os
import pandas as pd
import pdfplumber
import openai

# --- 1. إعداد المفتاح ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("⚠️ مفتاح OpenAI غير موجود")
    st.stop()
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- 2. الواجهة ---
st.set_page_config(page_title="سالم - محطة جازان", page_icon="🛡️")
st.title("🛡️ مساعد السلامة الذكي (سالم)")
st.markdown("<h3 style='color: #2E7D32;'>إلتزم بالسلامة.. وخلك سالم</h3>", unsafe_allow_html=True)
st.divider()

# --- 3. تحميل البيانات (استخدام pdfplumber للجداول) ---
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
                with pdfplumber.open(path) as pdf:
                    # نأخذ أول 30 صفحة لضمان الشمولية
                    for page in pdf.pages[:30]:
                        t = page.extract_text()
                        if t: text += t + "\n"
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

# --- 4. محرك البحث "العادل" (يمنع احتكار ملف واحد) ---
def get_relevant_context(query, docs):
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    scored_docs = []

    for filename, content in docs.items():
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # نظام نقاط متوازن
        score = sum(15 for word in query_words if word in filename_lower)
        score += sum(1 for word in query_words if word in content_lower)
        
        if score > 0:
            # القفز الذكي لتجاوز الحشو
            start_index = 0
            found_indices = [content_lower.find(word) for word in query_words if content_lower.find(word) > 500]
            if found_indices:
                start_index = max(0, min(found_indices) - 300)
            
            scored_docs.append((score, filename, content[start_index:]))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    # 💡 الحل الجذري: نوزع الذاكرة على 4 ملفات بالتساوي (3000 حرف لكل ملف)
    # هذا يمنع أي ملف PDF من إقصاء ملف الإكسل أو الملفات الأخرى
    for i in range(min(4, len(scored_docs))):
        score, filename, content = scored_docs[i]
        context += f"\n\n[مستند {i+1}: {filename}]\n{content[:3000]}\n"
    
    return context[:12000]

# --- 5. الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

if question := st.chat_input("اسأل سالم..."):
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
                        "content": """أنت خبير سلامة محترف (سالم). 
                        أمامك مقتطفات من عدة ملفات (PDF وإكسل).
                        مهمتك:
                        1. لا تنحاز لملف واحد؛ ابحث عن الإجابة في جميع المستندات المرفقة.
                        2. إذا وجدت بيانات في الإكسل مرتبطة بالسؤال، اذكرها فوراً.
                        3. اذكر القواعد العشر للحفاظ على الحياة كما هي في ملف SEC (عزل الطاقة، المرتفعات، إلخ).
                        4. استخدم التنسيق النقطي والعناوين العريضة.
                        5. اذكر اسم الملف المستخدم في نهاية ردك."""
                    },
                    {"role": "user", "content": f"السؤال: {question}\n\nالنصوص المتاحة:\n{context}"}
                ],
                temperature=0
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ خطأ فني: {e}")
