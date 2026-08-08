import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. 頁面基礎設定與手機端優化
# ==========================================
st.set_page_config(
    page_title="台股 5日波段選股",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 隱藏 Streamlit 預設選單與頁尾
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
# 3. 台股中文名稱對照表（可自行新增）
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
# 4. 核心數據處理 (包含停利與停損價計算)
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
            name = ch_name
            
            latest_close = round(df['Close'].iloc[-1], 2)
            prev_close = round(df['Close'].iloc[-2], 2)
            pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2)
            latest_vol = int(df['Volume'].iloc[-1])
            market_cap = info.get("marketCap", 0) / 1e8  # 億台幣
            
            # 計算 MA 均線
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA10'] = df['Close'].rolling(10).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            
            c_ma5 = df['MA5'].iloc[-1] if not pd.isna(df['MA5'].iloc[-1]) else latest_close
            c_ma10 = df['MA10'].iloc[-1] if not pd.isna(df['MA10'].iloc[-1]) else latest_close
            
            # 💡 【風控計算】
            # 建議停利價：當前股價 +8% (5日短波段預期目標)
            # 建議停損價：10 日均線位置 (跌破關鍵支撐離場)
            target_tp = round(latest_close * 1.08, 2)
            stop_loss = round(c_ma10, 2)
            
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
                "建議停利": target_tp,
                "建議停損": stop_loss,
                "成交量(張)": int(latest_vol / 1000),
                "訊號": ", ".join(signals),
                "df": df
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# ==========================================
# 5. 畫面渲染
# ==========================================
with st.spinner("資料載入中，請稍候..."):
    df_res = fetch_data_safe(STOCK_DICT)

if df_res.empty:
    st.error("❌ 數據載入失敗，請稍後重新整理頁面試試。")
else:
    # 排序邏輯
    if sort_by == "市值大小 (Market Cap)":
        df_sorted = df_res.sort_values(by=["市值(億)", "綜合評分"], ascending=[False, False])
    else:
        df_sorted = df_res.sort_values(by=["綜合評分", "市值(億)"], ascending=[False, False])

    # 列表顯示（包含建議停利與建議停損）
    display_cols = ["代號", "名稱", "綜合評分", "收盤價", "漲跌幅(%)", "建議停利", "建議停損", "市值(億)"]
    
    st.dataframe(
        df_sorted[display_cols],
        column_config={
            "建議停利": st.column_config.NumberColumn("建議停利 (+8%)", format="%.2f 元"),
            "建議停損": st.column_config.NumberColumn("建議停損 (10日線)", format="%.2f 元"),
            "漲跌幅(%)": st.column_config.NumberColumn("漲跌幅(%)", format="%.2f%%"),
        },
        use_container_width=True,
        hide_index=True
    )

    # 查看技術圖表與詳細風控卡片
    st.markdown("---")
    st.subheader("📈 個股風控與 K 線分析")
    
    stock_options = df_sorted["代號"] + " " + df_sorted["名稱"]
    selected_option = st.selectbox("選擇股票：", options=stock_options)
    
    selected_code = selected_option.split(" ")[0]
    selected_row = df_sorted[df_sorted["代號"] == selected_code].iloc[0]
    hist = selected_row["df"]

    # 🎯 提示卡片：風控價格提醒
    st.info(
        f"🎯 **{selected_row['名稱']} ({selected_row['代號']}) 風控提示**：\n"
        f"- 💵 **當前收盤價**：`{selected_row['收盤價']}` 元\n"
        f"- 🎯 **建議停利價**：`{selected_row['建議停利']}` 元（預期動能目標 +8%）\n"
        f"- 🛑 **建議停損價**：`{selected_row['建議停損']}` 元（跌破 10 日線支撐）"
    )

    # 圖表
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
