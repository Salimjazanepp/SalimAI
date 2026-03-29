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
st.info("📑 نظام بحث شامل - شركة الكهرباء (SEC) - إدارة محطة جازان")
st.divider()

# --- 3. تحميل البيانات (قراءة عميقة جداً) ---
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
                # رفعنا القراءة لـ 50 صفحة لضمان تغطية كامل ملف Life Saving Rules
                for page in reader.pages[:50]:
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

# --- 4. محرك البحث (البحث عن الجوهر وتجاوز الحشو) ---
def get_relevant_context(query, docs):
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    scored_docs = []

    for filename, content in docs.items():
        content_lower = content.lower()
        
        # حساب النقاط بناءً على اسم الملف ومحتواه
        score = sum(30 for word in query_words if word in filename.lower())
        score += sum(3 for word in query_words if word in content_lower)
        
        if score > 0:
            # ✨ ميزة: "البحث عن قلب المعلومة"
            # نبحث عن أول ظهور لمصطلح البحث ونبدأ القراءة من هناك بـ 500 حرف للخلف
            # لنتجاوز المقدمات والفهارس آلياً
            start_index = 0
            found_indices = [content_lower.find(word) for word in query_words if content_lower.find(word) > 1000]
            if found_indices:
                start_index = min(found_indices) - 500
            
            scored_docs.append((score, filename, content[max(0, start_index):]))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    context = ""
    # نأخذ المصدر الأول بمساحة ضخمة (9000 حرف) ليتمكن من سرد الـ 10 قواعد كاملة
    for i in range(min(2, len(scored_docs))):
        score, filename, content = scored_docs[i]
        limit = 9000 if i == 0 else 3000
        context += f"\n\n[المصدر رقم {i+1}: {filename}]\n{content[:limit]}\n"
    
    return context[:12500]

# --- 5. إدارة المحادثة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# --- 6. الإدخال وتوليد الرد (تعليمات صارمة للموديل) ---
if question := st.chat_input("اسأل سالم عن قواعد السلامة..."):
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
                        "content": """أنت (سالم)، خبير السلامة في محطة جازان. 
                        تعليمات صارمة للرد:
                        1. ابحث عن القواعد العشر الحقيقية (عزل الطاقة، العمل على المرتفعات، القيادة، إلخ).
                        2. لا تذكر الفهرس أو المقدمات (نطاق، غرض، مسؤولية).
                        3. إذا سألت عن 'قواعد الحفاظ على الحياة'، يجب أن تسرد القواعد العشر كاملة مع شرح بسيط لكل واحدة.
                        4. استخدم الجداول أو القوائم المنظمة جداً.
                        5. كن دقيقاً جداً ولا تؤلف معلومات من خارج النص المرفق.
                        6. اذكر اسم الملف المرجعي في نهاية الإجابة."""
                    },
                    {"role": "user", "content": f"السؤال: {question}\n\nالنصوص الفنية المتاحة:\n{context}"}
                ],
                temperature=0 # صفر لضمان الدقة المطلقة وعدم التأليف
            )
            answer = response["choices"][0]["message"]["content"]
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"⚠️ حدث خطأ فني: {e}")
