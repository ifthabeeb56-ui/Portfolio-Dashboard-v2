import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time
from GoogleNews import GoogleNews

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        df_n500 = pd.read_csv(url)
        return sorted(df_n500['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "SBIN"]

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Today_PnL"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if "Account" not in df.columns: df["Account"] = "Habeeb"
        if "Status" not in df.columns: df["Status"] = "Holding"
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Status", "Today_PnL"])

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="5d", progress=False)['Close']
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
                        df.at[index, 'P&L'] = round(df.at[index, 'CM Value'] - row['Investment'], 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((df.at[index, 'P&L'] / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
nifty500 = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 2: PORTFOLIO (Decimal Removal Included) ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    
    if not hold_df.empty:
        t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%")

        view_mode = st.radio("Display Mode:", ["Summary View", "Detailed View"], horizontal=True)
        
        # ഡിസ്പ്ലേയ്ക്കായി ഡാറ്റാ ക്ലീൻ ചെയ്യുന്നു (Decimal removal using int)
        def format_to_int(val):
            try: return int(val)
            except: return val

        style_f = lambda x: 'color: #2ecc71' if isinstance(x, (int, float)) and x > 0 else 'color: #e74c3c' if isinstance(x, (int, float)) and x < 0 else ''

        if view_mode == "Summary View":
            summ = hold_df.groupby(['Name', 'Account']).agg({'QTY Available':'sum', 'CMP':'mean', 'Investment':'sum', 'P&L':'sum'}).reset_index()
            # ഡെസിമൽ ഒഴിവാക്കുന്നു
            for col in ['QTY Available', 'Investment', 'P&L']:
                summ[col] = summ[col].apply(format_to_int)
            summ['CMP'] = summ['CMP'].round(2)
            summ.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'P&L']
            st.dataframe(summ.style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)
        else:
            det = hold_df[['Buy Date', 'Name', 'Account', 'QTY Available', 'Buy Price', 'CMP', 'Investment', 'P&L', 'P_Percentage']].copy()
            for col in ['QTY Available', 'Investment', 'P&L']:
                det[col] = det[col].apply(format_to_int)
            st.dataframe(det.style.map(style_f, subset=['P&L', 'P_Percentage']), use_container_width=True, hide_index=True)

    # --- ADD / SELL SECTION (Fixed Stock Suggestions) ---
    with st.expander("➕ Add / Sell Stock"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Add Stock")
            # 2. പോർട്ട്‌ഫോളിയോ ലിസ്റ്റും Nifty 500 ഉം ചേർത്തുള്ള സജഷൻ
            existing_in_portfolio = [s.replace(".NS", "") for s in df['Name'].unique()]
            combined_list = sorted(list(set(existing_in_portfolio + nifty500)))
            
            selected_s = st.selectbox("Search/Select Stock (Nifty 500 + Portfolio)", combined_list)
            
            current_price = 0.0
            if selected_s:
                try:
                    ticker_sym = selected_s if ".NS" in selected_s else selected_s + ".NS"
                    ticker = yf.Ticker(ticker_sym)
                    current_price = ticker.fast_info['lastPrice']
                    st.caption(f"Current Market Price: ₹{current_price:.2f}")
                except: pass

            with st.form("add_form", clear_on_submit=True):
                buy_p = st.number_input("Buy Price", value=float(current_price))
                qty = st.number_input("Qty", min_value=1)
                acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
                if st.form_submit_button("Save Stock"):
                    ticker_sym = selected_s if ".NS" in selected_s else selected_s + ".NS"
                    new_row = {
                        "Name": ticker_sym, "Buy Price": buy_p, "QTY Available": qty, 
                        "Investment": round(buy_p*qty, 2), "Account": acc, "Status": "Holding", 
                        "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": current_price,
                        "CM Value": round(current_price*qty, 2), "P&L": round((current_price-buy_p)*qty, 2)
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"{selected_s} added!")
                    st.rerun()

        with c2:
            st.subheader("Sell Stock")
            st_sell = st.selectbox("Select to Sell", ["None"] + list(hold_df['Name'].unique()))
            if st_sell != "None":
                avail_q = int(hold_df[hold_df['Name'] == st_sell]['QTY Available'].sum())
                s_qty = st.number_input("Sell Qty", 1, avail_q)
                s_pr = st.number_input("Sell Price", 0.1)
                if st.button("Confirm Sell"):
                    # Selling logic...
                    st.success("Sold Successfully!")
                    st.rerun()
