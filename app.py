import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import time
import plotly.express as px
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        return sorted(pd.read_csv(url)['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "SBIN", "INFY"]

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # നിർബന്ധമായും നമ്പറുകൾ ആകേണ്ട കോളങ്ങൾ
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Today_PnL", "Sell_Price", "Sell_Qty"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        if "Status" not in df.columns: df["Status"] = "Holding"
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Status", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"])

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
                        df.at[index, 'CM Value'] = round(row['QTY Available'] * new_p, 2)
                        df.at[index, 'Today_PnL'] = round((new_p - prev_p) * row['QTY Available'], 2)
                        net_pnl = (df.at[index, 'CM Value'] + row['Dividend']) - (row['Investment'] + row['Tax'])
                        df.at[index, 'P&L'] = round(net_pnl, 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: st.sidebar.warning("Live Update Error")
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
nifty500_list = get_nifty500_tickers()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Data Management")
    if not df.empty:
        st.download_button("📥 Download Portfolio", df.to_csv(index=False).encode('utf-8'), "portfolio.csv", "text/csv")
    up_file = st.file_uploader("📤 Upload Portfolio CSV", type="csv")
    if up_file:
        pd.read_csv(up_file).to_csv(PORTFOLIO_FILE, index=False)
        st.rerun()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    hold_df_h = df[df['Status'] == "Holding"].copy()
    if not hold_df_h.empty:
        fig = px.treemap(hold_df_h, path=['Name'], values='Investment', color='P_Percentage', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
        t_today = hold_df['Today_PnL'].sum()
        t_today_pct = (t_today / (t_val - t_today) * 100) if (t_val - t_today) != 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%")
        m4.metric("Today's P&L", f"₹{int(t_today):,}", f"{t_today_pct:.2f}%")

        # Switch for Summary/Detailed
        v_mode = st.radio("Display Mode:", ["Summary View", "Detailed View"], horizontal=True)
        style_func = lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 'color: red' if isinstance(x, (int, float)) and x < 0 else ''

        if v_mode == "Summary View":
            summ = hold_df.groupby(['Name']).agg({'QTY Available':'sum', 'CMP':'mean', 'Investment':'sum', 'CM Value':'sum', 'P&L':'sum'}).reset_index()
            summ.columns = ['Stock', 'Qty', 'Live Price', 'Investment', 'Cur. Value', 'P&L']
            summ['P&L %'] = (summ['P&L'] / summ['Investment'] * 100).round(2)
            st.dataframe(summ.style.map(style_func, subset=['P&L', 'P&L %']), use_container_width=True, hide_index=True)
        else:
            det = hold_df[['Buy Date', 'Name', 'QTY Available', 'Buy Price', 'CMP', 'Investment', 'P&L', 'P_Percentage']].copy()
            det.columns = ['Date', 'Stock', 'Qty', 'Buy Price', 'Live Price', 'Investment', 'P&L', 'Gain %']
            st.dataframe(det.style.map(style_func, subset=['P&L', 'Gain %']), use_container_width=True, hide_index=True)

    with st.expander("➕ Add / Sell Stock"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Add Stock")
            n_in = st.selectbox("Symbol", nifty500_list)
            b_p = st.number_input("Buy Price", 0.1)
            qty = st.number_input("Qty", 1)
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
            if st.button("💾 Save"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Name": sym, "Buy Price": b_p, "QTY Available": qty, "Investment": b_p*qty, "Status": "Holding", "Account": acc, "Buy Date": datetime.now().strftime('%Y-%m-%d')}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
        with c2:
            st.subheader("Sell Stock")
            st_sel = st.selectbox("Select Stock", ["None"] + list(hold_df['Name'].unique()))
            if st_sel != "None":
                avail = int(hold_df[hold_df['Name']==st_sel]['QTY Available'].sum())
                s_qty = st.number_input("Sell Quantity", 1, avail)
                s_pr = st.number_input("Sell Price", 0.1)
                if st.button("🗑️ Confirm Sell"):
                    for idx, row in df[(df['Name']==st_sel) & (df['Status']=='Holding')].iterrows():
                        if s_qty <= 0: break
                        can_sell = min(s_qty, row['QTY Available'])
                        # Create Sold Entry
                        sold_row = row.copy()
                        sold_row['Status'], sold_row['Sell_Qty'], sold_row['Sell_Price'] = 'Sold', can_sell, s_pr
                        sold_row['Sell_Date'] = datetime.now().strftime('%Y-%m-%d')
                        sold_row['P&L'] = round((s_pr - row['Buy Price']) * can_sell, 2)
                        df = pd.concat([df, pd.DataFrame([sold_row])], ignore_index=True)
                        # Update Holding
                        if row['QTY Available'] == can_sell: df.drop(idx, inplace=True)
                        else: 
                            df.at[idx, 'QTY Available'] -= can_sell
                            df.at[idx, 'Investment'] = df.at[idx, 'QTY Available'] * row['Buy Price']
                        s_qty -= can_sell
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: SELL ITEMS ---
with tab3:
    st.subheader("💰 Sell History")
    sold_df = df[df['Status'] == 'Sold'].copy()
    if not sold_df.empty:
        st.dataframe(sold_df[['Sell_Date', 'Name', 'Sell_Qty', 'Buy Price', 'Sell_Price', 'P&L']], use_container_width=True, hide_index=True)

# --- TAB 4: ANALYTICS ---
with tab4:
    if not hold_df_h.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(hold_df_h, values='Investment', names='Account', title='Account Distribution'), use_container_width=True)
        c2.plotly_chart(px.bar(hold_df_h, x='Name', y='P&L', color='P&L', title='Stock-wise P&L'), use_container_width=True)

# --- TAB 5: NEWS ---
with tab5:
    n_stk = st.selectbox("Stock News:", ["None"] + list(df['Name'].unique()))
    if n_stk != "None" and st.button("Get News"):
        try:
            gn = GoogleNews(lang='en', period='7d')
            gn.search(n_stk.replace(".NS", ""))
            res = gn.result()
            if res:
                trans = GoogleTranslator(source='en', target='ml')
                for r in res[:5]:
                    st.write(f"📢 **{r['title']}**")
                    with st.expander("Translation"): st.write(trans.translate(r['title']))
                    st.caption(f"{r['date']} | [Read More]({r['link']})")
        except: st.error("News load failed.")

# --- TAB 6: WATCHLIST ---
with tab6:
    st.subheader("👀 Watchlist")
    w_in = st.text_input("Add Symbol").upper()
    if st.button("Add to Watchlist") and w_in:
        with open(WATCHLIST_FILE, "a") as f: f.write(w_in + ".NS\n")
        st.rerun()
