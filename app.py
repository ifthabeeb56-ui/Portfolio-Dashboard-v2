import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # സംഖ്യകൾ കൃത്യമായി വരുന്നുണ്ടെന്ന് ഉറപ്പാക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if 'Status' not in df.columns: df['Status'] = 'Holding'
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

# --- 2. ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")

# ബ്ലാക്ക് തീം സ്റ്റൈലിംഗ്
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    div.stTabs [data-baseweb="tab-list"] { background-color: #000000; }
    div.stTabs [data-baseweb="tab"] { background-color: #1a1a1a; color: white; border-radius: 5px; padding: 10px; }
    div.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { background-color: #ff4b4b !important; }
</style>
""", unsafe_allow_html=True)

df = load_data()
watch_stocks = get_watchlist()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "👀 Watchlist", "💾 Backup"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Overview (Portfolio + Watchlist)")
    hold_tickers = df[df['Status'] == "Holding"]['Name'].tolist()
    # പോർട്ട്‌ഫോളിയോയും വാച്ച്‌ലിസ്റ്റും ഒന്നിച്ച് കാണിക്കുന്നു
    all_tickers = list(set(hold_tickers + watch_stocks))
    
    if all_tickers:
        try:
            formatted_tickers = [s if (".NS" in s or ".BO" in s) else s + ".NS" for s in all_tickers]
            data = yf.download(formatted_tickers, period="2d", progress=False)['Close']
            if not data.empty and len(data) > 1:
                changes = ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
                m_df = pd.DataFrame({"Symbol": [s.replace(".NS","") for s in changes.index], "Change %": changes.values})
                m_df['abs_change'] = m_df['Change %'].abs() + 0.5
                fig = px.treemap(m_df, path=['Symbol'], values='abs_change', color='Change %', 
                                 color_continuous_scale='RdYlGn', range_color=[-3, 3])
                st.plotly_chart(fig, use_container_width=True)
        except: st.warning("ലൈവ് ഡാറ്റ ലോഡ് ചെയ്യാൻ കഴിഞ്ഞില്ല.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    st.subheader("Current Holdings")
    holdings = df[df['Status'] == 'Holding']
    if not holdings.empty:
        st.dataframe(holdings, use_container_width=True, hide_index=True)

# --- TAB 4: WATCHLIST ---
with tab4:
    st.subheader("Manage Watchlist")
    w_input = st.text_input("Enter Ticker (eg: RELIANCE)").upper().strip()
    if st.button("Add to Watchlist"):
        if w_input:
            with open(WATCHLIST_FILE, "a") as f: f.write(w_input + "\n")
            st.success(f"{w_input} Added!")
            st.rerun()
    st.write("Current List:", watch_stocks)

# --- TAB 5: BACKUP ---
with tab5:
    st.subheader("Backup Center")
    st.download_button("Download Portfolio", data=df.to_csv(index=False), file_name="portfolio_backup.csv")
        
