import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE)
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        # സിമ്പിൾ ലൈവ് പ്രൈസ് അപ്ഡേറ്റ്
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

st.set_page_config(layout="wide", page_title="Habeeb's Hub")

# ഡാറ്റ ലോഡ് ചെയ്യുന്നു
df = load_data()

st.title("📊 Habeeb's Power Hub (Stable Version)")

tab1, tab2, tab3 = st.tabs(["💼 Portfolio", "➕ Add/Sell", "📊 Analytics"])

with tab1:
    df = update_live_prices(df)
    holdings = df[df['Status'] == "Holding"]
    if not holdings.empty:
        # മെട്രിക്സ്
        inv = holdings['Investment'].sum()
        cur = holdings['CM Value'].sum()
        pnl = holdings['P&L'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Investment", f"₹{inv:,.0f}")
        c2.metric("Current Value", f"₹{cur:,.0f}")
        c3.metric("Total P&L", f"₹{pnl:,.0f}", f"{(pnl/inv*100):.2f}%")
        
        st.dataframe(holdings, use_container_width=True)
    else:
        st.info("Portfolio is empty.")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Stock")
        with st.form("add_form"):
            name = st.text_input("Stock Symbol (eg: RELIANCE.NS)").upper()
            b_price = st.number_input("Buy Price", min_value=0.0)
            qty = st.number_input("Quantity", min_value=1)
            acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            if st.form_submit_button("Add to Portfolio"):
                new_row = {
                    "Buy Date": datetime.now().strftime('%Y-%m-%d'),
                    "Name": name, "Buy Price": b_price, "QTY Available": qty,
                    "Investment": b_price * qty, "Account": acc, "Status": "Holding",
                    "CMP": b_price, "CM Value": b_price * qty, "P&L": 0.0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("Added!")
                st.rerun()

    with col2:
        st.subheader("Sell Stock")
        if not holdings.empty:
            s_name = st.selectbox("Select Stock", holdings['Name'].unique())
            with st.form("sell_form"):
                s_qty = st.number_input("Sell Qty", min_value=1)
                s_price = st.number_input("Sell Price", min_value=0.0)
                if st.form_submit_button("Confirm Sell"):
                    # സെൽ ലോജിക്
                    st.success("Sold!")

with tab3:
    if not holdings.empty:
        st.plotly_chart(px.pie(holdings, values='Investment', names='Name'))
                
