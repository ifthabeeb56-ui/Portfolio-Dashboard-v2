import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time
from GoogleNews import GoogleNews

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        return sorted(pd.read_csv(url)['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY"]

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # സംഖ്യകളെ കൃത്യമായി മാറ്റുന്നു, ഒഴിഞ്ഞ കോളങ്ങളിൽ 0 നൽകുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "Today_PnL", "P_Percentage"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        if "Account" not in df.columns: df["Account"] = "Habeeb"
        if "Status" not in df.columns: df["Status"] = "Holding"
        return df
    return pd.DataFrame(columns=["Name", "Buy Date", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status", "CMP"])

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="1d", progress=False)['Close']
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    curr_p = float(live_data[t_name].iloc[-1]) if len(tickers) > 1 else float(live_data.iloc[-1])
                    df.at[index, 'CMP'] = round(curr_p, 2)
                    df.at[index, 'CM Value'] = round(row['QTY Available'] * curr_p, 2)
                    df.at[index, 'P&L'] = round(df.at[index, 'CM Value'] - row['Investment'], 2)
                    if row['Investment'] > 0:
                        df.at[index, 'P_Percentage'] = round((df.at[index, 'P&L'] / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
nifty500 = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    
    if not hold_df.empty:
        # Metrics
        t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100 if t_inv > 0 else 0):.2f}%")

        # --- ഡിസ്പ്ലേ സെക്ഷൻ (എറർ ഒഴിവാക്കാൻ ശരിയാക്കിയത്) ---
        view_mode = st.radio("Display Mode:", ["Summary View", "Detailed View"], horizontal=True)
        
        # ഡിസ്പ്ലേയ്ക്ക് ആവശ്യമായ കോളങ്ങൾ മാത്രം എടുക്കുന്നു
        disp_cols = ['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']
        disp_df = hold_df[disp_cols].copy()
        
        # Decimal ഒഴിവാക്കാൻ സംഖ്യകളെ റൗണ്ട് ചെയ്യുന്നു (IntCasting Error ഒഴിവാക്കാൻ ഇതാണ് നല്ലത്)
        for col in ['QTY Available', 'Investment', 'P&L']:
            disp_df[col] = disp_df[col].round(0).astype(int)
        
        disp_df.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'P&L']

        style_f = lambda x: 'color: #2ecc71' if isinstance(x, (int, float)) and x > 0 else 'color: #e74c3c' if isinstance(x, (int, float)) and x < 0 else ''
        
        st.dataframe(disp_df.style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)

    # --- ADD STOCK SECTION ---
    with st.expander("➕ Add Stock"):
        # സജഷൻ: നിങ്ങളുടെ ലിസ്റ്റിലുള്ളതും + Nifty 500 ഉം
        portfolio_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
        full_suggestions = sorted(list(set(portfolio_stocks + nifty500)))
        
        sel_stock = st.selectbox("Search/Select Stock", full_suggestions)
        
        curr_mkt_price = 0.0
        if sel_stock:
            try:
                t_obj = yf.Ticker(sel_stock + ".NS")
                curr_mkt_price = t_obj.fast_info['lastPrice']
                st.caption(f"Current Market Price: ₹{curr_mkt_price:.2f}")
            except: pass

        with st.form("add_stock_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            buy_price = col1.number_input("Buy Price", value=float(curr_mkt_price))
            qty_val = col2.number_input("Quantity", min_value=1)
            acc_name = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            
            if st.form_submit_button("Save"):
                new_data = {
                    "Name": sel_stock + ".NS", "Buy Price": buy_price, "QTY Available": qty_val, 
                    "Investment": buy_price * qty_val, "Account": acc_name, "Status": "Holding",
                    "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": curr_mkt_price,
                    "CM Value": curr_mkt_price * qty_val, "P&L": (curr_mkt_price - buy_price) * qty_val
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{sel_stock} added to Portfolio!")
                st.rerun()

# --- മറ്റ് ടാബുകൾ (Heatmap, News, etc. പഴയപോലെ തന്നെ) ---
with tab1:
    if not hold_df.empty:
        st.plotly_chart(px.treemap(hold_df, path=['Name'], values='Investment', color='P_Percentage', color_continuous_scale='RdYlGn'), use_container_width=True)
