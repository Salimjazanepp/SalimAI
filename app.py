import streamlit as st

# إعدادات واجهة المتصفح
st.set_page_config(page_title="سالم - مساعد السلامة", page_icon="🛡️")

st.title("🛡️ مرحباً بك، أنا سالم")
st.write("أنا مساعدك الذكي لشؤون السلامة وبيانات الموظفين.")

# خانة لرفع ملفات العمل (PDF أو Excel)
uploaded_files = st.file_uploader("ارفع ملفات البيانات هنا (PDF/Excel)", accept_multiple_files=True)

# خانة الدردشة
user_input = st.text_input("كيف يمكنني مساعدتك اليوم؟")

if user_input:
    st.info(f"جاري البحث عن: {user_input} في الملفات المرفوعة...")
    # هنا سنضيف كود الذكاء الاصطناعي لاحقاً ليقرأ الملفات ويرد