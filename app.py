import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

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
        # ആവശ്യമായ കോളങ്ങൾ ഉണ്ടെന്ന് ഉറപ്പുവരുത്തുന്നു
        req_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"]
        for col in req_cols:
            if col not in df.columns:
                df[col] = 0.0 if col != "Sell_Date" else ""
            if col not in ["Sell_Date", "Status", "Name", "Account", "Category", "Remark"]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

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
    except: st.sidebar.error("ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് പരാജയപ്പെട്ടു.")
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
watch_stocks = get_watchlist()
nifty500_list = get_nifty500_tickers()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Data Management")
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Portfolio", csv, PORTFOLIO_FILE, "text/csv")
    up_file = st.file_uploader("📤 Upload Portfolio CSV", type="csv")
    if up_file:
        pd.read_csv(up_file).to_csv(PORTFOLIO_FILE, index=False)
        st.success("Updated!"); st.rerun()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    if not hold_stocks_df.empty:
        fig = px.treemap(hold_stocks_df, path=['Name'], values='Investment', color='P_Percentage', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PORTFOLIO ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            t_today_pnl = hold_df['Today_PnL'].sum()
            t_today_pct = (t_today_pnl / (t_val - t_today_pnl) * 100) if (t_val - t_today_pnl) != 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Investment", f"₹{int(t_inv):,}")
            m2.metric("Current Value", f"₹{int(t_val):,}")
            m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            m4.metric("Today's P&L", f"₹{int(t_today_pnl):,}", f"{t_today_pct:.2f}%")

            view_mode = st.selectbox("View Mode:", ["Summary View", "Detailed View"], key="port_view")
            style_func = lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 'color: red' if isinstance(x, (int, float)) and x < 0 else ''

            if view_mode == "Summary View":
                summ_df = hold_df.groupby(['Name', 'Account']).agg({'QTY Available':'sum', 'Investment':'sum', 'CM Value':'sum', 'P&L':'sum', 'Today_PnL':'sum'}).reset_index()
                summ_df['P&L %'] = ((summ_df['P&L'] / summ_df['Investment']) * 100).round(2)
                # 1. Quantity column added here
                summ_df.rename(columns={'QTY Available': 'Quantity'}, inplace=True)
                st.dataframe(summ_df.style.map(style_func, subset=['P&L', 'P&L %']), use_container_width=True, hide_index=True)
            else:
                det_df = hold_df.copy()
                det_df.rename(columns={'QTY Available': 'Quantity'}, inplace=True)
                st.dataframe(det_df.style.map(style_func, subset=['P&L', 'P_Percentage']), use_container_width=True, hide_index=True)

    with st.expander("➕ Add/Sell/Update Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("Add Stock")
            b_date = st.date_input("Date", datetime.now())
            n_in = st.selectbox("Symbol", nifty500_list)
            b_p, q_y = st.number_input("Buy Price", 0.1), st.number_input("Qty", 1)
            acc_in = st.selectbox("Account", ["Habeeb", "RISU"])
            if st.button("💾 Save Stock"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Category": "Equity", "Buy Date": str(b_date), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": acc_in, "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Tax": 0, "Dividend": 0, "Today_PnL": 0, "Sell_Price": 0, "Sell_Date": "", "Sell_Qty": 0}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
        with c_b:
            st.subheader("Sell Stock")
            h_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_m = st.selectbox("Select Stock to Sell", ["None"] + h_list)
            if st_m != "None":
                # 2. Sell Quantity input added
                max_qty = int(df[(df['Name'] == st_m) & (df['Status'] == 'Holding')]['QTY Available'].sum())
                s_qty = st.number_input("Sell Quantity", 1, max_qty)
                s_p = st.number_input("Selling Price", 0.0)
                if st.button("🗑️ Confirm Sell"):
                    idx = df[(df['Name'] == st_m) & (df['Status'] == 'Holding')].index[0]
                    df.at[idx, 'Status'] = 'Sold'
                    df.at[idx, 'Sell_Price'] = s_p
                    df.at[idx, 'Sell_Qty'] = s_qty
                    df.at[idx, 'Sell_Date'] = datetime.now().strftime('%Y-%m-%d')
                    # Profit calculation based on sell qty
                    actual_inv = (df.at[idx, 'Buy Price'] * s_qty)
                    sell_val = (s_p * s_qty)
                    df.at[idx, 'P&L'] = round(sell_val - actual_inv, 2)
                    df.at[idx, 'P_Percentage'] = round((df.at[idx, 'P&L'] / actual_inv) * 100, 2) if actual_inv > 0 else 0
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: SELL ITEMS (NEW) ---
with tab3:
    st.subheader("💰 വിറ്റ സ്റ്റോക്കുകളുടെ വിവരങ്ങൾ")
    sold_df = df[df['Status'] == 'Sold'].copy()
    if not sold_df.empty:
        # 3. Sell items list with Summary/Details switch
        sell_view = st.radio("Sell View Mode:", ["Summary", "Details"], horizontal=True)
        
        if sell_view == "Summary":
            # Summary: Name and total profit
            sell_summ = sold_df.groupby('Name').agg({'Sell_Qty':'sum', 'P&L':'sum', 'Investment':'sum'}).reset_index()
            sell_summ['Gain %'] = (sell_summ['P&L'] / sell_summ['Investment'] * 100).round(2)
            st.dataframe(sell_summ.style.map(style_func, subset=['P&L', 'Gain %']), use_container_width=True, hide_index=True)
        else:
            # Details: Date, Name, Prices, Qty, Profit
            sell_det = sold_df[['Sell_Date', 'Name', 'Buy Price', 'Sell_Price', 'Sell_Qty', 'P&L', 'P_Percentage']].copy()
            sell_det.columns = ['Date', 'Name', 'Buy Price', 'Sell Price', 'Quantity', 'Profit', 'Gain %']
            st.dataframe(sell_det.style.map(style_func, subset=['Profit', 'Gain %']), use_container_width=True, hide_index=True)
    else:
        st.info("വിറ്റ സ്റ്റോക്കുകൾ ലഭ്യമല്ല.")

# --- TAB 4: ANALYTICS ---
with tab4:
    if not hold_stocks_df.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(hold_stocks_df, values='Investment', names='Account', title='Account Distribution'), use_container_width=True)
        c2.plotly_chart(px.bar(hold_stocks_df, x='Name', y='P&L', color='P&L', title='Stock-wise P&L'), use_container_width=True)

# --- TAB 5: NEWS ---
with tab5:
    n_stk = st.selectbox("Select Stock for News:", ["None"] + list(df['Name'].unique()))
    if n_stk != "None" and st.button("Get News"):
        try:
            gn = GoogleNews(lang='en', period='7d')
            gn.search(n_stk.replace(".NS", ""))
            res = gn.result()
            if res:
                trans = GoogleTranslator(source='en', target='ml')
                for r in res[:5]:
                    st.write(f"📢 **{r['title']}**")
                    st.caption(f"{r['date']} | [Read More]({r['link']})")
        except Exception as e: st.error(f"Error: {e}")

# --- TAB 6: WATCHLIST ---
with tab6:
    st.subheader("👀 My Watchlist")
    win = st.text_input("Add Symbol").upper().strip()
    if st.button("Add") and win:
        with open(WATCHLIST_FILE, "a") as f: f.write(win + ".NS\n")
        st.rerun()
    if watch_stocks:
        for s in watch_stocks:
            wc1, wc2 = st.columns([4, 1])
            wc1.write(f"📈 **{s}**")
            if wc2.button("Remove", key=f"del_{s}"):
                upd = [i for i in watch_stocks if i != s]
                with open(WATCHLIST_FILE, "w") as f:
                    for i in upd: f.write(i + "\n")
                st.rerun()
        
