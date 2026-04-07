import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        return sorted(pd.read_csv(url)['Symbol'].tolist())
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Data Management")
    if not df.empty:
        st.download_button("📥 Download CSV", df.to_csv(index=False), PORTFOLIO_FILE)
    up_file = st.file_uploader("📤 Upload CSV", type="csv")
    if up_file:
        pd.read_csv(up_file).to_csv(PORTFOLIO_FILE, index=False); st.rerun()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    h_df = df[df['Status'] == "Holding"].copy()
    if not h_df.empty:
        fig = px.treemap(h_df, path=['Name'], values='Investment', color='P_Percentage', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        # Metrics
        t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%")

        view_mode = st.radio("Display Mode:", ["Summary View", "Detailed View"], horizontal=True)
        
        # ഡിസ്പ്ലേയ്ക്കായി ഡാറ്റാ ക്ലീൻ ചെയ്യുന്നു (Decimal removal)
        disp = hold_df.copy()
        for col in ['QTY Available', 'Investment', 'P&L', 'CM Value']:
            disp[col] = disp[col].apply(lambda x: f"{int(x):,}")

        style_f = lambda x: 'color: #2ecc71' if isinstance(x, (int, float)) and x > 0 else 'color: #e74c3c' if isinstance(x, (int, float)) and x < 0 else ''

        if view_mode == "Summary View":
            summ = hold_df.groupby(['Name', 'Account']).agg({'QTY Available':'sum', 'CMP':'mean', 'Investment':'sum', 'P&L':'sum'}).reset_index()
            summ.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'P&L']
            st.dataframe(summ.style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)
        else:
            det = hold_df[['Buy Date', 'Name', 'Account', 'QTY Available', 'Buy Price', 'CMP', 'Investment', 'P&L']].copy()
            st.dataframe(det.style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)

    # --- ADD / SELL SECTION ---
    with st.expander("➕ Add / Sell Stock"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Add Stock")
            # സജഷൻ ലിസ്റ്റ്: നിലവിലുള്ള സ്റ്റോക്കുകൾ + Nifty 500
            existing_stocks = [s.replace(".NS", "") for s in hold_df['Name'].unique()]
            full_suggestions = sorted(list(set(existing_stocks + nifty500)))
            
            selected_s = st.selectbox("Search/Select Stock", full_suggestions)
            
            # ലൈവ് പ്രൈസ് തനിയെ എടുക്കുന്നു
            current_price = 0.0
            if selected_s:
                try:
                    ticker = yf.Ticker(selected_s + ".NS")
                    current_price = ticker.fast_info['lastPrice']
                    st.caption(f"Current Market Price: ₹{current_price:.2f}")
                except: pass

            with st.form("add_form"):
                buy_p = st.number_input("Buy Price", value=float(current_price))
                qty = st.number_input("Qty", min_value=1)
                acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
                if st.form_submit_button("Save"):
                    new_row = {"Name": selected_s + ".NS", "Buy Price": buy_p, "QTY Available": qty, "Investment": buy_p*qty, "Account": acc, "Status": "Holding", "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": current_price}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

        with c2:
            st.subheader("Sell Stock")
            st_sell = st.selectbox("Stock to Sell", ["None"] + list(hold_df['Name'].unique()))
            if st_sell != "None":
                avail_q = int(hold_df[hold_df['Name'] == st_sell]['QTY Available'].sum())
                s_qty = st.number_input("Sell Qty", 1, avail_q)
                s_pr = st.number_input("Sell Price", 0.1)
                if st.button("Confirm Sell"):
                    for idx, row in df[(df['Name'] == st_sell) & (df['Status'] == 'Holding')].iterrows():
                        if s_qty <= 0: break
                        can_sell = min(s_qty, row['QTY Available'])
                        sold_row = row.copy()
                        sold_row['Status'], sold_row['Sell_Qty'], sold_row['Sell_Price'] = 'Sold', can_sell, s_pr
                        sold_row['Sell_Date'] = datetime.now().strftime('%Y-%m-%d')
                        sold_row['P&L'] = (s_pr - row['Buy Price']) * can_sell
                        df = pd.concat([df, pd.DataFrame([sold_row])], ignore_index=True)
                        if row['QTY Available'] == can_sell: df.drop(idx, inplace=True)
                        else: 
                            df.at[idx, 'QTY Available'] -= can_sell
                            df.at[idx, 'Investment'] = df.at[idx, 'QTY Available'] * row['Buy Price']
                        s_qty -= can_sell
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3, 4, 5, 6 ---
with tab3:
    st.dataframe(df[df['Status'] == 'Sold'], use_container_width=True)
with tab4:
    if not hold_df.empty:
        st.plotly_chart(px.pie(hold_df, values='Investment', names='Account', title="Account Allocation"))
with tab5:
    st.info("Search News in Sidebar or select stock in Portfolio.")
with tab6:
    w_sym = st.text_input("Add to Watchlist").upper()
    if st.button("Add"):
        with open(WATCHLIST_FILE, "a") as f: f.write(w_sym + ".NS\n")
        st.success("Added!")
