# app.py (نسخة “سالم” الذكي)
import streamlit as st
import os
import json

st.set_page_config(page_title="سالم - ذاكرة الملفات", layout="wide")
st.title("💾 سالم - استفسر عن الملفات")

# مجلد حفظ الملفات
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "memory.json")

# تحميل البيانات الموجودة مسبقًا
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = []

# ------------------------
# رفع ملف جديد
# ------------------------
st.subheader("رفع ملف أو نص جديد")
uploaded_file = st.file_uploader("اختر ملف TXT أو اكتب محتوى جديد", type=["txt"])
new_text = st.text_area("أو اكتب نص هنا:")

if st.button("احفظ في ذاكرة سالم"):
    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
    elif new_text.strip() != "":
        content = new_text
    else:
        content = None

    if content:
        memory.append(content)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)
        st.success("✅ تمت إضافة المحتوى إلى ذاكرة سالم.")
    else:
        st.warning("❌ لم يتم إدخال أي محتوى.")

# ------------------------
# استفسار عن أي محتوى
# ------------------------
st.subheader("اسأل سالم عن أي ملف أو نص")
query = st.text_input("أدخل كلمة أو جملة للبحث:")

if query.strip() != "":
    results = [m for m in memory if query.lower() in m.lower()]
    if results:
        st.write(f"🔍 سالم وجد {len(results)} نتيجة:")
        for r in results:
            st.markdown(f"- {r}")
    else:
        st.warning("⚠️ لم يتم العثور على أي محتوى مطابق.")
