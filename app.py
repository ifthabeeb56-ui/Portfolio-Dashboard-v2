import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
from GoogleNews import GoogleNews

# --- ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        return df
    return pd.DataFrame(columns=["Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

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
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()

st.title("📊 Habeeb's Power Hub v6.9")

# 7 ടാബുകൾ
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist", "➕ Add Stock"
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
        st.dataframe(holdings, use_container_width=True)
    else:
        st.info("Portfolio Empty")

# --- TAB 3: SELL ITEMS ---
with tab3:
    sold_df = df[df['Status'] == "Sold"]
    st.dataframe(sold_df, use_container_width=True)

# --- TAB 4: ANALYTICS ---
with tab4:
    if not h_df.empty:
        st.plotly_chart(px.pie(h_df, values='Investment', names='Account', title="Account Allocation"))

# --- TAB 5: NEWS ---
with tab5:
    query = st.text_input("Search News (eg: Tata Motors)", "Indian Stock Market")
    if st.button("Get News"):
        googlenews = GoogleNews(lang='en', region='IN', period='1d')
        googlenews.search(query)
        result = googlenews.result()
        for n in result[:5]:
            st.write(f"**{n['title']}**")
            st.caption(f"Source: {n['media']} | {n['date']}")
            st.write(f"[Link]({n['link']})")
            st.divider()

# --- TAB 6: WATCHLIST ---
with tab6:
    w_input = st.text_input("Add to Watchlist (eg: SBIN.NS)").upper()
    if st.button("Add"):
        with open(WATCHLIST_FILE, "a") as f: f.write(w_input + "\n")
        st.success("Added!")

# --- TAB 7: ADD STOCK ---
with tab7:
    with st.form("add_form"):
        name = st.text_input("Stock Name (Symbol.NS)").upper()
        b_price = st.number_input("Buy Price", min_value=0.0)
        qty = st.number_input("Quantity", min_value=1)
        acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
        if st.form_submit_button("Save"):
            new_row = {
                "Buy Date": datetime.now().strftime('%Y-%m-%d'),
                "Name": name, "Buy Price": b_price, "QTY Available": qty,
                "Investment": b_price * qty, "Account": acc, "Status": "Holding",
                "CMP": b_price, "CM Value": b_price * qty, "P&L": 0.0
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.success("Stock Added!")
