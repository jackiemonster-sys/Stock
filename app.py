import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. 頁面基礎設定與手機端防黑屏優化
# ==========================================
st.set_page_config(
    page_title="台股 5日波段選股",
    page_icon="📈",
    layout="centered", # 手機上使用 centered 體驗較好
    initial_sidebar_state="collapsed"
)

# 隱藏 Streamlit 預設選單與頁尾，讓它更像原生 App
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("📈 台股 5日波段選股 App")

# ==========================================
# 2. 控制區塊
# ==========================================
sort_by = st.radio(
    "排序方式：",
    options=["市值大小 (Market Cap)", "模型綜合評分 (Score)"],
    horizontal=True
)

# ==========================================
# 3. 台股中文名稱對照表（可自行自由新增）
# 格式為 "股票代號.TW": "中文名稱"
# ==========================================
STOCK_DICT = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2382.TW": "廣達",
    "3231.TW": "緯創",
    "2308.TW": "台達電",
    "2303.TW": "聯電",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "3037.TW": "欣興",
    "2345.TW": "智邦",
    "6669.TW": "緯穎",
    "3661.TW": "世芯-KY",
    "3035.TW": "智原",
    "2357.TW": "華碩",
    "2356.TW": "英業達"
}

# ==========================================
# 4. 核心數據處理 (中文名稱與防爆機制)
# ==========================================
@st.cache_data(ttl=1800) # 快取 30 分鐘
def fetch_data_safe(stock_dict):
    results = []
    
    for ticker, ch_name in stock_dict.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d", timeout=5)
            
            if df.empty or len(df) < 10:
                continue
                
            info = stock.info
            symbol = ticker.replace(".TW", "").replace(".TWO", "")
            
            # 優先使用設定好的中文名稱
            name = ch_name
            
            latest_close = round(df['Close'].iloc[-1], 2)
            prev_close = round(df['Close'].iloc[-2], 2)
            pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
            latest_vol = int(df['Volume'].iloc[-1])
            market_cap = info.get("marketCap", 0) / 1e8  # 億台幣
            
            # 計算 MA
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            c_ma5 = df['MA5'].iloc[-1] if not pd.isna(df['MA5'].iloc[-1]) else latest_close
            c_ma10 = df['MA10'].iloc[-1] if not pd.isna(df['MA10'].iloc[-1]) else latest_close
            
            # 計分邏輯
            score = 50 # 基礎分
            signals = []
            
            if latest_close > c_ma5:
                score += 25
                signals.append("站上5日線")
            if latest_close > c_ma10:
                score += 15
                signals.append("站上10日線")
            if market_cap >= 500:
                score += 10
                signals.append("中大型市值")
                
            results.append({
                "代號": symbol,
                "名稱": name,
                "綜合評分": score,
                "市值(億)": round(market_cap, 1),
                "收盤價": latest_close,
                "漲跌幅(%)": pct_change,
                "成交量(張)": int(latest_vol / 1000),
                "訊號": ", ".join(signals),
                "df": df
            })
        except Exception:
            # 單一股票抓取失敗自動跳過，防止崩潰
            continue
            
    return pd.DataFrame(results)

# ==========================================
# 5. 畫面渲染
# ==========================================
with st.spinner("資料載入中，請稍候..."):
    df_res = fetch_data_safe(STOCK_DICT)

if df_res.empty:
    st.error("❌ 數據載入失敗（可能因 Yahoo API 連線限制），請稍後重新整理頁面試試。")
else:
    # 排序邏輯
    if sort_by == "市值大小 (Market Cap)":
        df_sorted = df_res.sort_values(by=["市值(億)", "綜合評分"], ascending=[False, False])
    else:
        df_sorted = df_res.sort_values(by=["綜合評分", "市值(億)"], ascending=[False, False])

    # 列表顯示
    display_cols = ["代號", "名稱", "綜合評分", "市值(億)", "收盤價", "漲跌幅(%)", "訊號"]
    st.dataframe(
        df_sorted[display_cols],
        use_container_width=True,
        hide_index=True
    )

    # 查看圖表
    st.markdown("---")
    st.subheader("📈 個股技術分析")
    
    # 選單同步顯示 中文名稱 + 代號
    stock_options = df_sorted["代號"] + " " + df_sorted["名稱"]
    selected_option = st.selectbox("選擇股票：", options=stock_options)
    
    selected_code = selected_option.split(" ")[0]
    selected_row = df_sorted[df_sorted["代號"] == selected_code].iloc[0]
    hist = selected_row["df"]

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="K線"
    ))
    fig.update_layout(
        title=f"{selected_row['名稱']} ({selected_row['代號']}) K線圖",
        height=400, 
        template="plotly_dark", 
        margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
