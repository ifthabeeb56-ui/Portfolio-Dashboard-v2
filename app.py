import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

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
        # എല്ലാ സംഖ്യാ കോളങ്ങളും നിർബന്ധമായും നമ്പറുകളാക്കുന്നു, ഒഴിഞ്ഞവ 0 ആക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage"]
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
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9")
df = load_data()
nifty500 = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items"])

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
        m3.metric("Total P&L", f"₹{int(t_pnl):,}")

        # --- ഡിസ്‌പ്ലേ സെക്ഷൻ (എറർ വരാത്ത രീതിയിൽ ശരിയാക്കിയത്) ---
        disp_df = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
        
        # എറർ ഒഴിവാക്കാൻ നേരിട്ട് മാപ്പിംഗ് ഉപയോഗിക്കുന്നു
        def clean_int(val):
            try: return f"{int(round(val)):,}"
            except: return "0"

        # ലിസ്റ്റിൽ കാണിക്കുമ്പോൾ മാത്രം ദശാംശം ഒഴിവാക്കുന്നു
        final_table = pd.DataFrame()
        final_table['Stock'] = disp_df['Name']
        final_table['Account'] = disp_df['Account']
        final_table['Qty'] = disp_df['QTY Available'].apply(lambda x: int(x))
        final_table['Price'] = disp_df['CMP'].round(2)
        final_table['Investment'] = disp_df['Investment'].apply(lambda x: int(x))
        final_table['P&L'] = disp_df['P&L'].apply(lambda x: int(x))

        style_f = lambda x: 'color: #2ecc71' if isinstance(x, (int, float)) and x > 0 else 'color: #e74c3c' if isinstance(x, (int, float)) and x < 0 else ''
        st.dataframe(final_table.style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)

    # --- ADD STOCK SECTION ---
    with st.expander("➕ Add Stock"):
        # സജഷൻ: Portfolio + Nifty 500
        portfolio_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
        full_suggestions = sorted(list(set(portfolio_stocks + nifty500)))
        
        sel_stock = st.selectbox("Search Stock", full_suggestions)
        
        curr_mkt_price = 0.0
        if sel_stock:
            try:
                t_obj = yf.Ticker(sel_stock + ".NS")
                curr_mkt_price = t_obj.fast_info['lastPrice']
                st.caption(f"Market Price: ₹{curr_mkt_price:.2f}")
            except: pass

        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            buy_p = col1.number_input("Buy Price", value=float(curr_mkt_price))
            qty_v = col2.number_input("Quantity", min_value=1)
            acc_n = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            
            if st.form_submit_button("Save"):
                new_data = {
                    "Name": sel_stock + ".NS", "Buy Price": buy_p, "QTY Available": qty_v, 
                    "Investment": buy_p * qty_v, "Account": acc_n, "Status": "Holding",
                    "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": curr_mkt_price,
                    "CM Value": curr_mkt_price * qty_v, "P&L": (curr_mkt_price - buy_p) * qty_v
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("Stock Added!"); st.rerun()
        
