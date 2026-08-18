from datetime import datetime
import json
import urllib.request
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ==========================================
# 1. 頁面基礎設定與手機端優化
# ==========================================
st.set_page_config(
    page_title="台股 5日波段選股",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📈 台股 5日波段選股 App")

# ==========================================
# 2. 控制區塊
# ==========================================
sort_by = st.radio(
    "排序方式：",
    options=["模型綜合評分 (Score)", "成交金額大小"],
    horizontal=True,
)

# ==========================================
# 3. 台股對照表 (代號與名稱)
# ==========================================
STOCK_DICT = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2382": "廣達",
    "3231": "緯創",
    "2308": "台達電",
    "2303": "聯電",
    "2881": "富邦金",
    "2882": "國泰金",
    "2603": "長榮",
    "2609": "陽明",
    "3037": "欣興",
    "2345": "智邦",
    "6669": "緯穎",
    "3661": "世芯-KY",
    "3035": "智原",
    "2357": "華碩",
    "2356": "英業達",
}


# ==========================================
# 4. 抓取真實 Yahoo Finance 數據與計算
# ==========================================
@st.cache_data(ttl=1800)
def fetch_real_stock_data(stock_dict):
    results = []
    latest_trade_date = datetime.now().strftime("%Y/%m/%d")

    # 批次下載 3 個月 (3m) 的真實數據
    tickers = [f"{symbol}.TW" for symbol in stock_dict.keys()]
    try:
        data = yf.download(tickers, period="3m", interval="1d", group_by="ticker", progress=False)
    except Exception:
        return pd.DataFrame(), latest_trade_date

    for symbol, name in stock_dict.items():
        try:
            ticker_symbol = f"{symbol}.TW"
            if ticker_symbol not in data or data[ticker_symbol].empty:
                continue

            hist_df = data[ticker_symbol].dropna().copy()
            if len(hist_df) < 10:
                continue

            # 整理日期與數值欄位
            hist_df.reset_index(inplace=True)
            hist_df["Date"] = hist_df["Date"].dt.strftime("%Y-%m-%d")

            latest_close = float(hist_df["Close"].iloc[-1])
            prev_close = float(hist_df["Close"].iloc[-2])
            change = latest_close - prev_close
            pct_change = round((change / prev_close) * 100, 2)
            vol = int(hist_df["Volume"].iloc[-1] / 1000)  # 轉為張數

            # 技術指標真實計算
            hist_df["MA5"] = hist_df["Close"].rolling(5).mean()
            hist_df["MA10"] = hist_df["Close"].rolling(10).mean()

            # MACD 指標計算 (12, 26, 9)
            ema12 = hist_df["Close"].ewm(span=12, adjust=False).mean()
            ema26 = hist_df["Close"].ewm(span=26, adjust=False).mean()
            hist_df["DIF"] = ema12 - ema26
            hist_df["DEM"] = hist_df["DIF"].ewm(span=9, adjust=False).mean()
            hist_df["MACD_Hist"] = hist_df["DIF"] - hist_df["DEM"]

            c_ma5 = hist_df["MA5"].iloc[-1]
            c_ma10 = hist_df["MA10"].iloc[-1]

            target_tp = round(latest_close * 1.08, 2)
            stop_loss = round(c_ma10, 2)

            score = 50
            signals = []
            if latest_close > c_ma5:
                score += 25
                signals.append("站上5日線")
            if latest_close > c_ma10:
                score += 25
                signals.append("站上10日線")

            latest_trade_date = hist_df["Date"].iloc[-1]

            results.append(
                {
                    "代號": symbol,
                    "名稱": name,
                    "綜合評分": score,
                    "收盤價": round(latest_close, 2),
                    "漲跌幅(%)": pct_change,
                    "建議停利": target_tp,
                    "建議停損": stop_loss,
                    "成交量(張)": vol,
                    "訊號": ", ".join(signals),
                    "交易日期": latest_trade_date,
                    "df": hist_df,
                }
            )
        except Exception:
            continue

    return pd.DataFrame(results), latest_trade_date


# ==========================================
# 5. 畫面渲染與技術圖表佈局
# ==========================================
with st.spinner("正在讀取真實股市日 K 線數據..."):
    df_res, data_date = fetch_real_stock_data(STOCK_DICT)

if df_res.empty:
    st.error("❌ 行情數據載入失敗，請確認網路連線或稍後再試。")
else:
    st.markdown(f"📅 **數據更新日期：`{data_date}` (真實市場行情)**")

    if sort_by == "成交金額大小":
        df_sorted = df_res.sort_values(
            by=["成交量(張)", "綜合評分"], ascending=[False, False]
        )
    else:
        df_sorted = df_res.sort_values(
            by=["綜合評分", "成交量(張)"], ascending=[False, False]
        )

    display_cols = [
        "代號",
        "名稱",
        "綜合評分",
        "收盤價",
        "漲跌幅(%)",
        "建議停利",
        "建議停損",
        "成交量(張)",
    ]

    st.dataframe(
        df_sorted[display_cols],
        column_config={
            "建議停利": st.column_config.NumberColumn(
                "建議停利 (+8%)", format="%.2f 元"
            ),
            "建議停損": st.column_config.NumberColumn(
                "建議停損 (10日線)", format="%.2f 元"
            ),
            "漲跌幅(%)": st.column_config.NumberColumn(
                "漲跌幅(%)", format="%.2f%%"
            ),
        },
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("📈 個股風控與 MACD 技術圖表")

    stock_options = df_sorted["代號"] + " " + df_sorted["名稱"]
    selected_option = st.selectbox("選擇股票：", options=stock_options)

    selected_code = selected_option.split(" ")[0]
    selected_row = df_sorted[df_sorted["代號"] == selected_code].iloc[0]
    hist = selected_row["df"]

    st.info(
        f"🎯 **{selected_row['名稱']} ({selected_row['代號']}) 風控提示**：\n"
        f"- 💵 **當前收盤價**：`{selected_row['收盤價']}` 元\n"
        f"- 🎯 **建議停利價**：`{selected_row['建議停利']}` 元（預期動能目標 +8%）\n"
        f"- 🛑 **建議停損價**：`{selected_row['建議停損']}` 元（跌破 10 日線支撐）"
    )

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.6, 0.4],
        subplot_titles=(
            f"{selected_row['名稱']} ({selected_row['代號']}) 真實 K線圖",
            "MACD 指標 (12, 26, 9)",
        ),
    )

    # 1. 主圖：K線圖
    fig.add_trace(
        go.Candlestick(
            x=hist["Date"],
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name="K線",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
        ),
        row=1,
        col=1,
    )

    # 2. 副圖：MACD
    colors = np.where(hist["MACD_Hist"] >= 0, "#ef5350", "#26a69a")

    fig.add_trace(
        go.Bar(
            x=hist["Date"],
            y=hist["MACD_Hist"],
            name="MACD柱狀",
            marker_color=colors,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=hist["Date"],
            y=hist["DIF"],
            name="DIF(快線)",
            line=dict(color="#2962FF", width=1.5),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=hist["Date"],
            y=hist["DEM"],
            name="MACD(慢線)",
            line=dict(color="#FF6D00", width=1.5),
        ),
        row=2,
        col=1,
    )

    # Layout 設定
    fig.update_layout(
        height=580,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
        xaxis=dict(type="category"),
        xaxis2=dict(type="category"),
    )

    fig.update_xaxes(nticks=8)

    st.plotly_chart(fig, use_container_width=True)
