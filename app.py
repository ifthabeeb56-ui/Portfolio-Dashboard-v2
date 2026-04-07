import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        # Nifty 500 ലിസ്റ്റ് ഓൺലൈനായി എടുക്കുന്നു
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        return sorted(pd.read_csv(url)['Symbol'].tolist())
    except:
        # ഇന്റർനെറ്റ് ഇല്ലെങ്കിൽ പ്രധാനപ്പെട്ട കുറച്ച് സ്റ്റോക്കുകൾ മാത്രം
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "SBIN", "ICICIBANK", "HINDUNILVR"]

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
        fig = px.treemap(h_df, path=['Name'], values='Investment', color='P_Percentage', 
                         color_continuous_scale='RdYlGn', title="Portfolio Heatmap (Size by Investment)")
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
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100 if t_inv != 0 else 0):.2f}%")

        view_mode = st.radio("Display Mode:", ["Summary View", "Detailed View"], horizontal=True)
        
        disp = hold_df.copy()
        style_f = lambda x: 'color: #2ecc71' if isinstance(x, (int, float)) and x > 0 else 'color: #e74c3c' if isinstance(x, (int, float)) and x < 0 else ''

        if view_mode == "Summary View":
            summ = hold_df.groupby(['Name', 'Account']).agg({'QTY Available':'sum', 'CMP':'mean', 'Investment':'sum', 'P&L':'sum'}).reset_index()
            st.dataframe(summ.style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)
        else:
            st.dataframe(hold_df[['Buy Date', 'Name', 'Account', 'QTY Available', 'Buy Price', 'CMP', 'Investment', 'P&L']].style.map(style_f, subset=['P&L']), use_container_width=True, hide_index=True)

    # --- ADD / SELL SECTION ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("➕ Add Stock")
        # 🟢 SEARCH BAR & SUGGESTION LIST
        # നിലവിലുള്ള സ്റ്റോക്കുകളും Nifty 500 ഉം കൂടി ചേർക്കുന്നു
        existing_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
        full_suggestions = sorted(list(set(existing_stocks + nifty500)))
        
        selected_s = st.selectbox("Search Stock Name (Type to search)", full_suggestions, index=None, placeholder="Eg: RELIANCE")
        
        if selected_s:
            try:
                # ലൈവ് പ്രൈസ് കാണിക്കുന്നു
                ticker = yf.Ticker(selected_s + ".NS")
                current_price = round(ticker.fast_info['lastPrice'], 2)
                st.info(f"Market Price: ₹{current_price}")
            except:
                current_price = 0.0

            with st.form("add_form", clear_on_submit=True):
                buy_p = st.number_input("Buy Price", value=float(current_price))
                qty = st.number_input("Quantity", min_value=1, step=1)
                acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
                sub_btn = st.form_submit_button("Add to Portfolio")
                
                if sub_btn:
                    new_row = {
                        "Name": selected_s + ".NS", 
                        "Buy Price": buy_p, 
                        "QTY Available": qty, 
                        "Investment": buy_p*qty, 
                        "Account": acc, 
                        "Status": "Holding", 
                        "Buy Date": datetime.now().strftime('%Y-%m-%d'), 
                        "CMP": current_price,
                        "CM Value": current_price * qty,
                        "P&L": (current_price - buy_p) * qty,
                        "P_Percentage": ((current_price - buy_p) / buy_p * 100) if buy_p != 0 else 0
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"Added {selected_s} successfully!")
                    st.rerun()

    with c2:
        st.subheader("➖ Sell Stock")
        st_sell = st.selectbox("Select Stock to Sell", ["None"] + list(hold_df['Name'].unique()))
        if st_sell != "None":
            avail_q = int(hold_df[hold_df['Name'] == st_sell]['QTY Available'].sum())
            st.warning(f"Available: {avail_q} Qty")
            
            with st.form("sell_form"):
                s_qty = st.number_input("Sell Qty", 1, avail_q)
                s_pr = st.number_input("Sell Price", value=0.0)
                if st.form_submit_button("Confirm Sale"):
                    # സെല്ലിംഗ് ലോജിക്
                    temp_qty = s_qty
                    for idx, row in df[(df['Name'] == st_sell) & (df['Status'] == 'Holding')].iterrows():
                        if temp_qty <= 0: break
                        can_sell = min(temp_qty, row['QTY Available'])
                        
                        # Sold എൻട്രി ചേർക്കുന്നു
                        sold_row = row.copy()
                        sold_row['Status'], sold_row['QTY Available'], sold_row['Buy Price'] = 'Sold', can_sell, row['Buy Price']
                        sold_row['P&L'] = (s_pr - row['Buy Price']) * can_sell
                        sold_row['Buy Date'] = row['Buy Date']
                        df = pd.concat([df, pd.DataFrame([sold_row])], ignore_index=True)
                        
                        # മെയിൻ സ്റ്റോക്കിൽ നിന്ന് കുറയ്ക്കുന്നു
                        if row['QTY Available'] == can_sell:
                            df.drop(idx, inplace=True)
                        else:
                            df.at[idx, 'QTY Available'] -= can_sell
                            df.at[idx, 'Investment'] = df.at[idx, 'QTY Available'] * row['Buy Price']
                        temp_qty -= can_sell
                        
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"Sold {s_qty} of {st_sell}")
                    st.rerun()

# --- TAB 3: SOLD ITEMS ---
with tab3:
    sold_df = df[df['Status'] == 'Sold']
    if not sold_df.empty:
        st.write("### History of Realized P&L")
        st.dataframe(sold_df, use_container_width=True)
    else:
        st.info("No stocks sold yet.")

# --- TAB 4: ANALYTICS ---
with tab4:
    if not hold_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(hold_df, values='Investment', names='Account', title="Investment by Account"))
        with c2:
            st.plotly_chart(px.bar(hold_df, x='Name', y='P&L', color='P&L', title="Stock-wise Profit/Loss"))

# --- TAB 5: NEWS ---
with tab5:
    st.info("Yahoo Finance news integration is active via Ticker analysis.")
    search_n = st.text_input("Enter Stock Name for News", "RELIANCE")
    if st.button("Get News"):
        st.write(f"News for {search_n} coming soon...")

# --- TAB 6: WATCHLIST ---
with tab6:
    w_sym = st.text_input("Add Stock to Watchlist (Symbol Only)").upper()
    if st.button("Add to Watchlist"):
        with open(WATCHLIST_FILE, "a") as f: f.write(w_sym + ".NS\n")
        st.success(f"{w_sym} added to Watchlist!")
        
