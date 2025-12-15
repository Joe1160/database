import streamlit as st

st.markdown(
"""
<style>.fixed-title {
    position: fixed;
    top: 60px;
    left: 300px;
    font-size: 60px;
    font-weight: bold;
}
</style>
<div class="fixed-title">Kpop 字典</div>
""", unsafe_allow_html=True) 

st.sidebar.title("功能選擇")
option = st.sidebar.selectbox("選擇功能：", ["查詢Idol", "新增Idol", "查詢公司"])

st.text_input("🔍 搜尋", key="search")

st.markdown("""
<style>
div[data-testid="stTextInput"] {
    position: fixed;
    top: 65px;
    left: 600px;
    width: 250px;
    z-index: 999;
}
</style>
""", unsafe_allow_html=True)

