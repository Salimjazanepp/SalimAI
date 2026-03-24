# app.py (النسخة الأصلية لسالم)
import streamlit as st

# عنوان الصفحة
st.set_page_config(page_title="تطبيقي", layout="wide")

# عنوان رئيسي
st.title("مرحبا بك في تطبيقي")

# نص ترحيبي
st.write("هذا مثال لتطبيق Streamlit الأصلي.")

# إضافة عناصر تفاعلية بسيطة
name = st.text_input("أدخل اسمك:")
if name:
    st.write(f"أهلاً بك، {name}!")

# مثال على زر
if st.button("اضغط هنا"):
    st.success("تم الضغط على الزر!")
