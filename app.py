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
        df_n500 = pd.read_csv(url)
        return sorted(df_n500['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY"]

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # എല്ലാ സംഖ്യാ കോളങ്ങളും നമ്പറുകളാണെന്ന് ഉറപ്പാക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "Today_PnL"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
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
                    new_p = float(live_data[t_name].iloc[-1]) if len(tickers) > 1 else float(live_data.iloc[-1])
                    df.at[index, 'CMP'] = round(new_p, 2)
                    df.at[index, 'CM Value'] = round(row['QTY Available'] * new_p, 2)
                    df.at[index, 'P&L'] = round(df.at[index, 'CM Value'] - row['Investment'], 2)
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
        # Metrics Display
        t_inv = int(hold_df['Investment'].sum())
        t_val = int(hold_df['CM Value'].sum())
        t_pnl = int(hold_df['P&L'].sum())
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"₹{t_inv:,}")
        m2.metric("Current Value", f"₹{t_val:,}")
        m3.metric("Total P&L", f"₹{t_pnl:,}")

        # --- ഡിസിമൽ ഒഴിവാക്കിയുള്ള ഡിസ്‌പ്ലേ (Main Fix) ---
        disp_df = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
        
        # സംഖ്യകളെ Integer ആക്കി മാറ്റുന്നു
        disp_df['QTY Available'] = disp_df['QTY Available'].astype(int)
        disp_df['Investment'] = disp_df['Investment'].astype(int)
        disp_df['P&L'] = disp_df['P&L'].astype(int)
        disp_df['Live Price'] = disp_df['CMP'].round(2) # പ്രൈസ് മാത്രം 2 ഡെസിമൽ
        
        final_display = disp_df[['Name', 'Account', 'QTY Available', 'Live Price', 'Investment', 'P&L']]
        final_display.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'Profit/Loss']

        style_f = lambda x: 'color: #2ecc71' if isinstance(x, (int, float)) and x > 0 else 'color: #e74c3c' if isinstance(x, (int, float)) and x < 0 else ''
        st.dataframe(final_display.style.applymap(style_f, subset=['Profit/Loss']), use_container_width=True, hide_index=True)

    # --- ADD STOCK SECTION ---
    with st.expander("➕ Add New Stock"):
        # സജഷൻ ലിസ്റ്റ് (Portfolio + Nifty 500)
        existing_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
        full_list = sorted(list(set(existing_stocks + nifty500)))
        
        selected_s = st.selectbox("Search Stock", full_list)
        
        current_price = 0.0
        if selected_s:
            try:
                ticker = yf.Ticker(selected_s + ".NS")
                current_price = ticker.fast_info['lastPrice']
                st.write(f"Market Price: ₹{current_price:.2f}")
            except: pass

        with st.form("add_stock_form"):
            c1, c2 = st.columns(2)
            buy_p = c1.number_input("Buy Price", value=float(current_price))
            qty = c2.number_input("Quantity", min_value=1)
            acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            
            if st.form_submit_button("Save to Portfolio"):
                new_row = {
                    "Name": selected_s + ".NS", "Buy Price": buy_p, "QTY Available": qty, 
                    "Investment": buy_p * qty, "Status": "Holding", "Account": acc,
                    "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": current_price,
                    "CM Value": current_price * qty, "P&L": (current_price - buy_p) * qty
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("Stock Added!")
                st.rerun()

# --- TAB 1: HEATMAP ---
with tab1:
    if not hold_df.empty:
        fig = px.treemap(hold_df, path=['Name'], values='Investment', color='P&L', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)
                
