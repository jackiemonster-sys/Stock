import streamlit as st

# 1. 調整頁面配置，適應手機
st.set_page_config(
    page_title="台股波段選股",
    layout="centered",  # 手機建議用 centered，避免 wide 版面太寬
    initial_sidebar_state="collapsed" # 預設隱藏側邊欄，節省手機空間
)

# 2. 隱藏 Streamlit 預設頁尾與選單 (看起來更像原生 App)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
