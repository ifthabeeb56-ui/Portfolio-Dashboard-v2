import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        n500_df = pd.read_csv(url)
        return sorted(n500_df['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        req_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"]
        for col in req_cols:
            if col not in df.columns:
                df[col] = 0.0 if col != "Sell_Date" else ""
            if col not in ["Sell_Date", "Status", "Name", "Account", "Category", "Remark"]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"])

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="5d", progress=False)['Close']
        if live_data.empty: return df
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    stock_series = live_data[t_name].dropna() if len(tickers) > 1 else live_data.dropna()
                    if len(stock_series) >= 2:
                        new_p = float(stock_series.iloc[-1])
                        prev_p = float(stock_series.iloc[-2])
                        df.at[index, 'CMP'] = round(new_p, 2)
                        current_val = round(row['QTY Available'] * new_p, 2)
                        df.at[index, 'CM Value'] = current_val
                        df.at[index, 'Today_PnL'] = round((new_p - prev_p) * row['QTY Available'], 2)
                        net_pnl = (current_val + row['Dividend']) - (row['Investment'] + row['Tax'])
                        df.at[index, 'P&L'] = round(net_pnl, 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items"])

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
        
        m1, m2, m3 = st.columns(3)
        # 1. മെട്രിക്സിൽ Decimal ഒഴിവാക്കി
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")

        # ഡിസ്‌പ്ലേ ടേബിൾ തയ്യാറാക്കുന്നു
        disp_df = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
        
        # 2. ടേബിളിൽ Decimal ഒഴിവാക്കുന്നു (IntCasting Error വരാത്ത രീതിയിൽ)
        def to_int_safe(val):
            try: return f"{int(round(val)):,}"
            except: return "0"

        # കാണിക്കാൻ മാത്രമുള്ള കോളം പേരുകൾ മാറ്റുന്നു
        final_disp = pd.DataFrame()
        final_disp['Stock'] = disp_df['Name']
        final_disp['Account'] = disp_df['Account']
        final_disp['Qty'] = disp_df['QTY Available'].apply(lambda x: int(x))
        final_disp['LTP'] = disp_df['CMP'].round(2)
        final_disp['Investment'] = disp_df['Investment'].apply(lambda x: int(round(x)))
        final_disp['P&L'] = disp_df['P&L'].apply(lambda x: int(round(x)))

        style_func = lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 'color: red' if isinstance(x, (int, float)) and x < 0 else ''
        st.dataframe(final_disp.style.map(style_func, subset=['P&L']), use_container_width=True, hide_index=True)

    # --- ADD STOCK SECTION (ഇവിടെയാണ് Nifty 500 ആഡ് ചെയ്തത്) ---
    with st.expander("➕ Add Stock"):
        # നിലവിലുള്ള സ്റ്റോക്കുകളും Nifty 500 ഉം ചേർത്ത ലിസ്റ്റ്
        port_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
        full_list = sorted(list(set(port_stocks + nifty500_list)))
        
        sel_name = st.selectbox("Search/Select Stock", full_list)
        
        # ലൈവ് പ്രൈസ് തനിയെ വരാൻ
        curr_price = 0.0
        if sel_name:
            try:
                t = yf.Ticker(sel_name + ".NS")
                curr_price = t.fast_info['lastPrice']
                st.caption(f"Current Market Price: ₹{curr_price:.2f}")
            except: pass

        with st.form("add_new_stock"):
            c1, c2 = st.columns(2)
            buy_price = c1.number_input("Buy Price", value=float(curr_price))
            qty = c2.number_input("Qty", min_value=1)
            acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            
            if st.form_submit_button("Save"):
                sym = sel_name + ".NS" if ".NS" not in sel_name else sel_name
                new_row = {
                    "Category": "Equity", "Buy Date": datetime.now().strftime('%Y-%m-%d'), 
                    "Name": sym, "CMP": curr_price, "Buy Price": buy_price, "QTY Available": qty, 
                    "Account": acc, "Investment": round(qty*buy_price, 2), "CM Value": round(qty*curr_price, 2), 
                    "P&L": round((curr_price-buy_price)*qty, 2), "Status": "Holding", "Tax": 0, "Dividend": 0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("Saved!"); st.rerun()
            
