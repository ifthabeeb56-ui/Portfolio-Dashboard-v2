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
        # എല്ലാ കോളങ്ങളും കൃത്യമായ ഫോർമാറ്റിലാണെന്ന് ഉറപ്പാക്കുന്നു
        req_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"]
        for col in req_cols:
            if col not in df.columns:
                df[col] = 0.0 if col != "Sell_Date" else ""
            if col not in ["Sell_Date", "Status", "Name", "Account", "Category", "Remark"]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date", "Sell_Qty"])

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

# --- TAB 2: PORTFOLIO ---
with tab2:
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

        # View Mode Dropdown
        view_mode = st.selectbox("Select View Mode:", ["Detailed View", "Summary View"])
        style_func = lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 'color: red' if isinstance(x, (int, float)) and x < 0 else ''

        disp_df = hold_df.copy()
        disp_df.rename(columns={'QTY Available': 'Quantity'}, inplace=True)
        
        if view_mode == "Summary View":
            summ_df = disp_df.groupby(['Name', 'Account']).agg({'Quantity':'sum', 'Investment':'sum', 'CM Value':'sum', 'P&L':'sum', 'Today_PnL':'sum'}).reset_index()
            summ_df['P&L %'] = ((summ_df['P&L'] / summ_df['Investment']) * 100).round(2)
            st.dataframe(summ_df.style.map(style_func, subset=['P&L', 'P&L %']), use_container_width=True, hide_index=True)
        else:
            st.dataframe(disp_df.style.map(style_func, subset=['P&L', 'P_Percentage']), use_container_width=True, hide_index=True)

    # ADD / SELL SECTION
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
            h_list = df[df['Status']=='Holding']['Name'].unique()
            st_m = st.selectbox("Select Stock to Sell", ["None"] + list(h_list))
            if st_m != "None":
                # ആ സ്റ്റോക്കിന്റെ കയ്യിലുള്ള ടോട്ടൽ ക്വാണ്ടിറ്റി കണ്ടുപിടിക്കുന്നു
                available_qty = int(df[(df['Name'] == st_m) & (df['Status'] == 'Holding')]['QTY Available'].sum())
                st.info(f"Available Quantity: {available_qty}")
                
                s_qty = st.number_input("Sell Quantity", 1, available_qty)
                s_p = st.number_input("Selling Price", 0.0, key="sell_price_input")
                
                if st.button("🗑️ Confirm Sell"):
                    # വിൽക്കുന്ന ക്വാണ്ടിറ്റി കുറയ്ക്കുന്നു
                    for idx, row in df[(df['Name'] == st_m) & (df['Status'] == 'Holding')].iterrows():
                        if s_qty <= 0: break
                        
                        can_sell = min(s_qty, row['QTY Available'])
                        remaining = row['QTY Available'] - can_sell
                        
                        # പുതിയ 'Sold' എൻട്രി ചേർക്കുന്നു
                        sold_entry = row.copy()
                        sold_entry['Status'] = 'Sold'
                        sold_entry['Sell_Qty'] = can_sell
                        sold_entry['QTY Available'] = 0
                        sold_entry['Sell_Price'] = s_p
                        sold_entry['Sell_Date'] = datetime.now().strftime('%Y-%m-%d')
                        sold_entry['Investment'] = round(can_sell * row['Buy Price'], 2)
                        sold_entry['P&L'] = round((s_p - row['Buy Price']) * can_sell, 2)
                        sold_entry['P_Percentage'] = round((sold_entry['P&L'] / sold_entry['Investment']) * 100, 2) if sold_entry['Investment'] > 0 else 0
                        
                        df = pd.concat([df, pd.DataFrame([sold_entry])], ignore_index=True)
                        
                        # പഴയ എൻട്രി അപ്ഡേറ്റ് ചെയ്യുന്നു
                        if remaining > 0:
                            df.at[idx, 'QTY Available'] = remaining
                            df.at[idx, 'Investment'] = round(remaining * row['Buy Price'], 2)
                        else:
                            df.drop(idx, inplace=True)
                        
                        s_qty -= can_sell
                    
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success("Sold Successfully!"); time.sleep(1); st.rerun()

# --- TAB 3: SELL ITEMS ---
with tab3:
    st.subheader("💰 വിറ്റ സ്റ്റോക്കുകളുടെ വിവരങ്ങൾ")
    sold_items = df[df['Status'] == 'Sold'].copy()
    if not sold_items.empty:
        sell_view = st.radio("Sell Items View:", ["Details", "Summary"], horizontal=True)
        if sell_view == "Summary":
            s_summ = sold_items.groupby('Name').agg({'Sell_Qty':'sum', 'P&L':'sum', 'Investment':'sum'}).reset_index()
            s_summ['Gain %'] = (s_summ['P&L'] / s_summ['Investment'] * 100).round(2)
            st.dataframe(s_summ, use_container_width=True, hide_index=True)
        else:
            show_cols = ['Sell_Date', 'Name', 'Buy Price', 'Sell_Price', 'Sell_Qty', 'P&L', 'P_Percentage']
            st.dataframe(sold_items[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No items sold yet.")

# മറ്റ് ടാബുകൾ (Heatmap, Analytics, News, Watchlist) പഴയതുപോലെ തന്നെ തുടരും...
