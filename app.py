import streamlit as st
import os
import json
from datetime import datetime

# ------------------------
# إعداد الصفحة
# ------------------------
st.set_page_config(page_title="إدارة محطة طاقة جازان - النسخة التجريبية", layout="wide")
st.title("🚀 إدارة محطة طاقة جازان - النسخة التجريبية")
st.write("هذا التطبيق يحفظ كل المدخلات ويجعلها قابلة للرجوع والبحث بسهولة.")

# ------------------------
# إعداد مجلد وملف حفظ البيانات
# ------------------------
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "memory.json")
os.makedirs(DATA_DIR, exist_ok=True)

# تحميل البيانات السابقة
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = []

# ------------------------
# إدخال المستخدم
# ------------------------
st.subheader("أضف نص أو اقتباس")
user_input = st.text_area("اكتب هنا:", "")

# زر الحفظ
if st.button("احفظ النص"):
    if user_input.strip() == "":
        st.warning("❌ لا يمكن حفظ نص فارغ.")
    else:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": user_input
        }
        memory.append(entry)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)
        st.success(f"✅ تم حفظ النص بنجاح! (إجمالي: {len(memory)})")

# ------------------------
# عرض النصوص المحفوظة
# ------------------------
st.subheader("جميع النصوص المحفوظة")
if st.checkbox("عرض كل النصوص"):
    if memory:
        for i, entry in enumerate(memory, 1):
            st.markdown(f"*{i}. [{entry['timestamp']}]*  \n{entry['text']}")
    else:
        st.info("لا توجد بيانات محفوظة بعد.")

# ------------------------
# البحث في النصوص
# ------------------------
st.subheader("ابحث في النصوص المحفوظة")
query = st.text_input("ابحث عن كلمة أو جملة:")
if query:
    results = [e for e in memory if query.lower() in e["text"].lower()]
    if results:
        st.write(f"🔍 تم العثور على {len(results)} نتيجة:")
        for entry in results:
            st.markdown(f"- [{entry['timestamp']}] {entry['text']}")
    else:
        st.warning("⚠️ لم يتم العثور على أي نصوص مطابقة للبحث.")
