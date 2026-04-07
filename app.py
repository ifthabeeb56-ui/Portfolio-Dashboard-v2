import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. ഡാറ്റാബേസ് സെറ്റപ്പ് ---
def get_connection():
    return sqlite3.connect("habeeb_inv.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    # പഴയ ടേബിൾ ഉണ്ടെങ്കിൽ അത് നീക്കം ചെയ്യുന്നു (OperationalError ഒഴിവാക്കാൻ)
    conn.execute("DROP TABLE IF EXISTS portfolio")
    conn.execute("""
        CREATE TABLE portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            index_name TEXT,
            qty REAL,
            avg_price REAL,
            date_added TEXT
        )
    """)
    conn.commit()
    conn.close()

# ആപ്പ് ആദ്യമായി തുടങ്ങുമ്പോൾ മാത്രം ഡാറ്റാബേസ് ക്ലീൻ ചെയ്യുന്നു
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state['db_initialized'] = True

# --- 2. സ്റ്റോക്ക് ലിസ്റ്റ് ---
@st.cache_data
def get_stocks(index_type):
    try:
        if index_type == "Nifty 50":
            url = "https://en.wikipedia.org/wiki/NIFTY_50"
            df = pd.read_html(url)[2]
            return sorted(df['Symbol'].tolist())
        elif index_type == "Nifty 500":
            url = "https://en.wikipedia.org/wiki/List_of_Nifty_500_companies"
            df = pd.read_html(url)[0]
            return sorted(df['Symbol'].tolist())
        else:
            return ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    except:
        return ["RELIANCE", "TCS", "INFY"]

# --- 3. ലൈവ് പ്രൈസ് ---
@st.cache_data(ttl=300)
def fetch_price(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        return round(ticker.fast_info['lastPrice'], 2)
    except:
        return None

# --- 4. UI ---
st.set_page_config(page_title="Habeeb INV Pro", layout="wide")

# Sidebar
with st.sidebar:
    st.title("HABEEB INV")
    menu = st.radio("Menu", ["📊 Overview", "⚙️ Manage Assets"])

# Load Data
conn = get_connection()
df_portfolio = pd.read_sql_query("SELECT * FROM portfolio", conn)
conn.close()

if menu == "📊 Overview":
    st.title("🚀 Investment Overview")
    if not df_portfolio.empty:
        with st.spinner('Updating Market Prices...'):
            df_portfolio['Live Price'] = df_portfolio['symbol'].apply(fetch_price)
            df_portfolio['Live Price'] = df_portfolio['Live Price'].fillna(df_portfolio['avg_price'])
            
        df_portfolio['Invested'] = df_portfolio['qty'] * df_portfolio['avg_price']
        df_portfolio['Current Value'] = df_portfolio['qty'] * df_portfolio['Live Price']
        df_portfolio['PnL'] = df_portfolio['Current Value'] - df_portfolio['Invested']

        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invested", f"₹{df_portfolio['Invested'].sum():,.0f}")
        m2.metric("Market Value", f"₹{df_portfolio['Current Value'].sum():,.0f}")
        m3.metric("Net Profit/Loss", f"₹{df_portfolio['PnL'].sum():,.0f}")

        # Graphs
        c1, c2 = st.columns(2)
        with c1:
            fig_bar = px.bar(df_portfolio, x='symbol', y='PnL', color='PnL', title="Performance by Stock", template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(df_portfolio, names='index_name', values='Current Value', title="Allocation by Index", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.dataframe(df_portfolio[['symbol', 'index_name', 'qty', 'avg_price', 'Live Price', 'PnL']], use_container_width=True)
    else:
        st.info("നിങ്ങളുടെ പോർട്ട്‌ഫോളിയോ കാലിയാണ്. Manage Assets പേജിൽ പോയി സ്റ്റോക്കുകൾ ചേർക്കുക.")

elif menu == "⚙️ Manage Assets":
    st.title("Manage Assets")
    with st.form("add_stock", clear_on_submit=True):
        idx = st.selectbox("Select Index", ["Nifty 50", "Nifty 500"])
        sym = st.selectbox("Select Stock", get_stocks(idx))
        q = st.number_input("Quantity", min_value=0.1)
        p = st.number_input("Buy Price", min_value=1.0)
        
        if st.form_submit_button("Add to Portfolio"):
            conn = get_connection()
            conn.execute("INSERT INTO portfolio (symbol, index_name, qty, avg_price, date_added) VALUES (?,?,?,?,?)",
                         (sym, idx, q, p, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
            st.success(f"{sym} added!")
            st.rerun()
            
