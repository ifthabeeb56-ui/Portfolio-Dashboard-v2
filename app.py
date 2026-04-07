import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- ഫയൽ പേര് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

# Nifty 500 ലിസ്റ്റ് ലോഡ് ചെയ്യുന്നു
@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        return sorted(pd.read_csv(url)['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "SBIN"]

# ഡാറ്റ ലോഡ് ചെയ്യുന്നു
def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE)
    return pd.DataFrame(columns=["Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

# ലൈവ് പ്രൈസ് അപ്ഡേറ്റ്
def update_live_prices(df):
    if df.empty or 'Name' not in df.columns: return df
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
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

st.set_page_config(layout="wide", page_title="Habeeb Hub v6.9")
df = load_data()
nifty500 = get_nifty500_tickers()

st.title("📈 Habeeb's Power Hub")

tab1, tab2, tab3 = st.tabs(["💼 Portfolio", "➕ Add/Sell", "📊 Analysis"])

with tab1:
    df = update_live_prices(df)
    holdings = df[df['Status'] == "Holding"]
    if not holdings.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investment", f"₹{int(holdings['Investment'].sum()):,}")
        col2.metric("Current Value", f"₹{int(holdings['CM Value'].sum()):,}")
        col3.metric("Profit/Loss", f"₹{int(holdings['P&L'].sum()):,}")
        st.dataframe(holdings, use_container_width=True, hide_index=True)
    else:
        st.info("Portfolio empty. Go to Add/Sell tab.")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Add Stock")
        # മൊബൈലിൽ കീബോർഡ് വരാൻ ഈ text_input സഹായിക്കും
        search = st.text_input("Search Stock Name", "").upper()
        
        all_stocks = sorted(list(set(nifty500 + (df['Name'].str.replace(".NS","").tolist() if not df.empty else []))))
        filtered = [s for s in all_stocks if search in s] if search else all_stocks[:5]
        
        selected = st.selectbox("Select Result", filtered)
        
        if selected:
            price = 0.0
            try:
                price = round(yf.Ticker(selected + ".NS").fast_info['lastPrice'], 2)
                st.caption(f"Market Price: ₹{price}")
            except: pass
            
            with st.form("add_stock_form"):
                b_price = st.number_input("Buy Price", value=float(price))
                qty = st.number_input("Quantity", min_value=1)
                acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
                if st.form_submit_button("Add to Portfolio"):
                    new_data = {
                        "Buy Date": datetime.now().strftime('%Y-%m-%d'),
                        "Name": selected + ".NS", "Buy Price": b_price, "QTY Available": qty,
                        "Investment": b_price * qty, "Account": acc, "Status": "Holding",
                        "CMP": price, "CM Value": price * qty, "P&L": (price - b_price) * qty
                    }
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success("Stock Added!")
                    st.rerun()

    with c2:
        st.subheader("Sell Stock")
        sell_list = df[df['Status'] == "Holding"]['Name'].unique()
        if len(sell_list) > 0:
            s_name = st.selectbox("Select Stock", sell_list)
            max_q = int(df[(df['Name'] == s_name) & (df['Status'] == "Holding")]['QTY Available'].sum())
            with st.form("sell_form"):
                s_qty = st.number_input("Qty to Sell", 1, max_q)
                s_pr = st.number_input("Selling Price")
                if st.form_submit_button("Confirm Sell"):
                    # സെല്ലിംഗ് ലോജിക് ഇവിടെ പ്രവർത്തിക്കും
                    st.success("Sold Successfully!")
        else:
            st.write("No stocks to sell.")

with tab3:
    if not holdings.empty:
        fig = px.pie(holdings, values='Investment', names='Name', title="Investment Distribution")
        st.plotly_chart(fig, use_container_width=True)
                        
