import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import date
import os

# പേജ് കോൺഫിഗറേഷൻ
st.set_page_config(page_title="Habeeb's Power Hub", layout="wide")

# ഡാറ്റ ഫയലുകൾ ലോഡ് ചെയ്യുന്നു
PORTFOLIO_FILE = 'habeeb_portfolio.csv'
HISTORY_FILE = 'portfolio_history.csv'

def load_data(file):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame()

# സ്റ്റോക്ക് ലിസ്റ്റ് (ഇവിടെ ഉദാഹരണത്തിന് കുറച്ച് മാത്രം നൽകുന്നു, നിങ്ങൾക്ക് CSV ലിങ്ക് ചെയ്യാം)
nifty_stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"] 

st.title("🚀 Habeeb's Power Hub v7.0")

# --- SIDEBAR: പുതിയ സ്റ്റോക്ക് ആഡ് ചെയ്യാൻ ---
st.sidebar.header("Add New Investment")
category = st.sidebar.selectbox("Category", ["Equity", "ETF", "SGB", "Mutual Fund"])
account = st.sidebar.selectbox("Account", ["Habeeb", "RISU"])

# Autocomplete & Auto-fill Logic
ticker = st.sidebar.selectbox("Select Stock (Nifty 500)", nifty_stocks)

# ലൈവ് പ്രൈസ് എടുക്കുന്നു
try:
    stock_info = yf.Ticker(ticker)
    cmp = round(stock_info.history(period="1d")['Close'].iloc[-1], 2)
except:
    cmp = 0.0

buy_price = st.sidebar.number_input("Buy Price", value=float(cmp))
qty = st.sidebar.number_input("Quantity", min_value=1, value=1)
buy_date = st.sidebar.date_input("Purchase Date", date.today())

if st.sidebar.button("Add to Portfolio"):
    new_data = pd.DataFrame([{
        'Date': buy_date, 'Category': category, 'Account': account,
        'Stock': ticker, 'Qty': qty, 'Buy Price': buy_price, 'CMP': cmp
    }])
    df = load_data(PORTFOLIO_FILE)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(PORTFOLIO_FILE, index=False)
    st.sidebar.success("Saved Successfully!")

# --- MAIN DASHBOARD ---
df_p = load_data(PORTFOLIO_FILE)

if not df_p.empty:
    # കണക്കുകൂട്ടലുകൾ
    df_p['Current Value'] = df_p['Qty'] * df_p['CMP']
    df_p['Investment'] = df_p['Qty'] * df_p['Buy Price']
    df_p['P&L'] = df_p['Current Value'] - df_p['Investment']
    
    total_val = df_p['Current Value'].sum()
    total_pnl = df_p['P&L'].sum()

    # മെട്രിക്സ് പ്രദർശനം
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Investment", f"₹{df_p['Investment'].sum():,.2f}")
    col2.metric("Current Value", f"₹{total_val:,.2f}")
    col3.metric("Total P&L", f"₹{total_pnl:,.2f}", delta=f"{total_pnl:,.2f}")

    # --- വാല്യൂ ഹിസ്റ്ററി സേവിംഗ് ലോജിക് ---
    history_df = load_data(HISTORY_FILE)
    today = str(date.today())
    if history_df.empty or history_df.iloc[-1]['Date'] != today:
        new_hist = pd.DataFrame([{'Date': today, 'Total Value': total_val}])
        history_df = pd.concat([history_df, new_hist], ignore_index=True)
        history_df.to_csv(HISTORY_FILE, index=False)

    # --- ഗ്രാഫുകൾ ---
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        st.subheader("Category Distribution")
        fig_pie = px.pie(df_p, values='Current Value', names='Category', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with row2_col2:
        st.subheader("Portfolio Trend")
        if not history_df.empty:
            fig_line = px.line(history_df, x='Date', y='Total Value', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

    # --- ഡാറ്റ ടേബിൾ ---
    st.subheader("Portfolio Details")
    st.dataframe(df_p, use_container_width=True)

    # ഡൗൺലോഡ് ബട്ടൺ
    csv = df_p.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Portfolio CSV", csv, "my_portfolio.csv", "text/csv")

else:
    st.info("പോർട്ട്‌ഫോളിയോയിൽ സ്റ്റോക്കുകൾ ഒന്നുമില്ല. ഇടത് വശത്തുള്ള ഫോം ഉപയോഗിച്ച് ആഡ് ചെയ്യുക.")
