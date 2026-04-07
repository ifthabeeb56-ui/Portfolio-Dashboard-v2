import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

# ഡാറ്റ ലോഡ് ചെയ്യാനുള്ള ഫങ്ക്ഷൻ
def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        return df
    return pd.DataFrame(columns=["Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

# ലൈവ് പ്രൈസ് അപ്ഡേറ്റ് ഫങ്ക്ഷൻ
def update_live_prices(df):
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

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v7.0", page_icon="🚀")
df = load_data()

st.title("🚀 Habeeb's Ultimate Power Hub")

# പത്ത് ടാബുകൾ
tabs = st.tabs([
    "📊 Heatmap", "💼 Portfolio", "💰 Sales", "📈 Analytics", 
    "📰 News", "👀 Watchlist", "➕ Add Stock", "🔄 Translator", 
    "🧮 Calculator", "📂 Data"
])

# --- TAB 1: HEATMAP ---
with tabs[0]:
    h_df = df[df['Status'] == "Holding"].copy()
    if not h_df.empty:
        fig = px.treemap(h_df, path=['Account', 'Name'], values='Investment', color='P&L', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PORTFOLIO ---
with tabs[1]:
    df = update_live_prices(df)
    holdings = df[df['Status'] == "Holding"]
    if not holdings.empty:
        st.subheader("Current Holdings")
        st.dataframe(holdings, use_container_width=True)
        # Metrics
        t_inv = holdings['Investment'].sum()
        t_val = holdings['CM Value'].sum()
        st.sidebar.metric("Total Net Worth", f"₹{t_val:,.2f}", f"₹{t_val-t_inv:,.2f}")

# --- TAB 3: SALES ---
with tabs[2]:
    sold_df = df[df['Status'] == "Sold"]
    if not sold_df.empty:
        st.dataframe(sold_df, use_container_width=True)
        st.success(f"Total Profit Realized: ₹{sold_df['P&L'].sum():,.2f}")

# --- TAB 4: ANALYTICS ---
with tabs[3]:
    if not h_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(h_df, values='Investment', names='Account', title="Account Allocation"))
        with c2:
            st.plotly_chart(px.bar(h_df, x='Name', y='P&L', color='P&L', title="Stock-wise P&L"))

# --- TAB 5: NEWS ---
with tabs[4]:
    q = st.text_input("Enter Topic for News", "Nifty 50 News")
    if st.button("Search News"):
        gn = GoogleNews(lang='en', region='IN', period='1d')
        gn.search(q)
        for item in gn.result()[:8]:
            st.write(f"### {item['title']}")
            st.write(f"*{item['date']}* - {item['media']}")
            st.write(f"[Read More]({item['link']})")
            st.divider()

# --- TAB 6: WATCHLIST ---
with tabs[5]:
    w_stock = st.text_input("Stock Symbol to Watch (eg: TATASTEEL.NS)").upper()
    if st.button("Add to Watchlist"):
        with open(WATCHLIST_FILE, "a") as f: f.write(w_stock + "\n")
        st.success("Added!")
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            st.text(f.read())

# --- TAB 7: ADD STOCK ---
with tabs[6]:
    st.subheader("Add New Purchase")
    with st.form("add_stock_full"):
        col1, col2 = st.columns(2)
        with col1:
            n = st.text_input("Stock Symbol (NSE)").upper()
            p = st.number_input("Buy Price", min_value=0.0)
        with col2:
            q = st.number_input("Quantity", min_value=1)
            a = st.selectbox("Account", ["Habeeb", "RISU", "Family", "Bank"])
        if st.form_submit_button("Save Entry"):
            new_entry = {
                "Buy Date": datetime.now().strftime('%Y-%m-%d'),
                "Name": n if ".NS" in n else n + ".NS",
                "Buy Price": p, "QTY Available": q, "Investment": p*q,
                "Account": a, "Status": "Holding", "CMP": p, "CM Value": p*q, "P&L": 0.0
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()

# --- TAB 8: TRANSLATOR ---
with tabs[7]:
    text = st.text_area("Enter Text to Translate")
    lang = st.radio("To Language", ["Malayalam", "English"])
    if st.button("Translate"):
        target = 'ml' if lang == "Malayalam" else 'en'
        translated = GoogleTranslator(source='auto', target=target).translate(text)
        st.success(translated)

# --- TAB 9: CALCULATOR ---
with tabs[8]:
    st.subheader("SIP Calculator")
    monthly = st.number_input("Monthly Investment", 500)
    rate = st.slider("Expected Return (%)", 1, 30, 12)
    years = st.slider("Years", 1, 40, 10)
    if st.button("Calculate"):
        n = years * 12
        r = (rate/100)/12
        m_val = monthly * ((((1 + r)**n) - 1) / r) * (1 + r)
        st.write(f"### Future Value: ₹{m_val:,.2f}")

# --- TAB 10: DATA MANAGER ---
with tabs[9]:
    st.download_button("Download CSV File", df.to_csv(index=False), "my_portfolio.csv")
    up = st.file_uploader("Upload New CSV")
    if up:
        pd.read_csv(up).to_csv(PORTFOLIO_FILE, index=False)
        st.success("File Updated!")
                 
