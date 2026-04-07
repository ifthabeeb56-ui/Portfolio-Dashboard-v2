import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # നമ്പറുകൾ കൃത്യമാണെന്ന് ഉറപ്പുവരുത്തുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

def update_live_prices(df):
    holdings = df[df['Status'] == "Holding"]
    tickers = holdings['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="1d", progress=False)['Close'].iloc[-1]
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                current_p = float(live_data[t_name]) if len(tickers) > 1 else float(live_data)
                df.at[index, 'CMP'] = round(current_p, 2)
                df.at[index, 'CM Value'] = round(row['QTY Available'] * current_p, 2)
                df.at[index, 'P&L'] = round(df.at[index, 'CM Value'] - row['Investment'], 2)
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()

st.title("📊 Habeeb's Power Hub v6.9")

# ടാബുകൾ
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist"
])

# --- TAB 1: HEATMAP ---
with tab1:
    h_df = df[df['Status'] == "Holding"].copy()
    if not h_df.empty:
        fig = px.treemap(h_df, path=['Name'], values='Investment', color='P&L', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    holdings = df[df['Status'] == "Holding"]
    
    if not holdings.empty:
        # മെട്രിക്സ്
        t_inv = holdings['Investment'].sum()
        t_val = holdings['CM Value'].sum()
        t_pnl = holdings['P&L'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{(t_pnl/t_inv*100):.2f}%")
        
        st.dataframe(holdings[['Buy Date', 'Name', 'Account', 'QTY Available', 'Buy Price', 'CMP', 'Investment', 'P&L']], use_container_width=True, hide_index=True)

    # ADD STOCK SECTION
    with st.expander("➕ Add New Stock"):
        with st.form("add_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Stock Symbol (eg: RELIANCE.NS)").upper()
                b_price = st.number_input("Buy Price", min_value=0.0)
            with col2:
                qty = st.number_input("Quantity", min_value=1)
                acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            if st.form_submit_button("Save Stock"):
                new_row = {
                    "Buy Date": datetime.now().strftime('%Y-%m-%d'),
                    "Name": name if ".NS" in name else name + ".NS",
                    "Buy Price": b_price, "QTY Available": qty, "Investment": b_price * qty,
                    "Account": acc, "Status": "Holding", "CMP": b_price, "CM Value": b_price * qty, "P&L": 0.0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("Added Successfully!")
                st.rerun()

# --- TAB 3: SELL ITEMS ---
with tab3:
    st.dataframe(df[df['Status'] == "Sold"], use_container_width=True)

# --- TAB 4: ANALYTICS ---
with tab4:
    if not h_df.empty:
        st.plotly_chart(px.pie(h_df, values='Investment', names='Account', title="Account Allocation"))

# --- TAB 5: NEWS ---
with tab5:
    st.info("News feature will be updated with API Key.")

# --- TAB 6: WATCHLIST ---
with tab6:
    w_in = st.text_input("Add to Watchlist").upper()
    if st.button("Add"):
        with open(WATCHLIST_FILE, "a") as f: f.write(w_in + "\n")
        st.success("Added!")
    
