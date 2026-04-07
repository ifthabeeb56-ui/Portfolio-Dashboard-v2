import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data_v2.csv" # വാച്ച്ലിസ്റ്റിൽ ഡേറ്റ് ഉള്ളതുകൊണ്ട് ഫയൽ ഫോർമാറ്റ് മാറ്റി
HISTORY_FILE = "portfolio_history.csv"

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
        # Decimal ഒഴിവാക്കാൻ ചില കോളംസ് ഇന്റീജർ ആക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Sold P&L"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        return pd.read_csv(WATCHLIST_FILE)
    return pd.DataFrame(columns=["Symbol", "Added Date", "Added Price"])

def save_portfolio_history(total_val):
    today = str(datetime.now().date())
    h_df = pd.DataFrame(columns=["Date", "Total_Value"])
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
    if today in h_df['Date'].values:
        h_df.loc[h_df['Date'] == today, 'Total_Value'] = total_val
    else:
        new_entry = pd.DataFrame([{"Date": today, "Total_Value": total_val}])
        h_df = pd.concat([h_df, new_entry], ignore_index=True)
    h_df.to_csv(HISTORY_FILE, index=False)

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="1d", progress=False)
        if live_data.empty: return df
        
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    new_p = float(live_data['Close'][t_name].iloc[-1]) if len(tickers) > 1 else float(live_data['Close'].iloc[-1])
                    if new_p > 0:
                        df.at[index, 'CMP'] = round(new_p, 1)
                        current_val = round(row['QTY Available'] * new_p, 1)
                        df.at[index, 'CM Value'] = current_val
                        net_pnl = (current_val + row['Dividend']) - (row['Investment'] + row['Tax'])
                        df.at[index, 'P&L'] = round(net_pnl, 1)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

# --- ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.8", page_icon="📈")
df = load_data()
w_df = get_watchlist()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.8")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    hold_stocks = df[df['Status'] == "Holding"]['Name'].tolist()
    if hold_stocks:
        with st.spinner("Loading Heatmap..."):
            m_data = yf.download(hold_stocks, period="2d", progress=False)['Close']
            if not m_data.empty and len(m_data) > 1:
                m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values, "Price": m_data.iloc[-1].values})
                m_df = m_df.merge(df[df['Status'] == "Holding"][['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                fig = px.treemap(m_df, path=['Symbol'], values='Investment', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3])
                st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: PORTFOLIO ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        
        # Decimal മാറ്റി ഇന്റീജർ ആക്കി കാണിക്കുന്നു
        display_df = hold_df.copy()
        for col in ["Investment", "CM Value", "P&L", "QTY Available"]:
            display_df[col] = display_df[col].astype(int)

        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment", f"₹{int(t_inv)}")
            c2.metric("Current Value", f"₹{int(t_val)}")
            c3.metric("Total P&L", f"₹{int(t_pnl)}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    with st.expander("➕ Add / 📉 Sell / ⚙️ Manage"):
        tab_a, tab_b = st.columns(2)
        with tab_a:
            st.write("### Buy Stock")
            n_in = st.selectbox("Symbol", ["Custom"] + nifty500_list)
            if n_in == "Custom": n_in = st.text_input("Symbol Name").upper()
            b_p = st.number_input("Price", value=0.0)
            q_y = st.number_input("Qty", min_value=1)
            if st.button("Save Purchase"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Category": "Equity", "Buy Date": str(datetime.now().date()), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": "Habeeb", "Investment": q_y*b_p, "CM Value": q_y*b_p, "P&L": 0, "Status": "Holding", "Dividend": 0, "Tax": 0}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()

        with tab_b:
            st.write("### Sell Stock")
            sell_stock = st.selectbox("Select to Sell", ["None"] + list(df[df['Status']=='Holding']['Name'].unique()))
            if sell_stock != "None":
                max_q = int(df[df['Name'] == sell_stock]['QTY Available'].sum())
                s_q = st.number_input("Sell Qty", min_value=1, max_value=max_q)
                s_p = st.number_input("Sell Price", value=0.0)
                if st.button("Confirm Sale"):
                    # ലളിതമായ സെല്ലിംഗ് ലോജിക്
                    idx = df[df['Name'] == sell_stock].index[0]
                    buy_p = df.at[idx, 'Buy Price']
                    realized_pnl = (s_p - buy_p) * s_q
                    df.at[idx, 'QTY Available'] -= s_q
                    df.at[idx, 'Investment'] = df.at[idx, 'QTY Available'] * buy_p
                    if df.at[idx, 'QTY Available'] <= 0:
                        df.at[idx, 'Status'] = 'Sold'
                    st.success(f"Sold! Realized P&L: ₹{realized_pnl}")
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.rerun()

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 Watchlist with Date Tracking")
    c1, c2 = st.columns([2, 1])
    with c1:
        w_sym = st.text_input("Ticker (eg: RELIANCE)").upper().strip()
        if st.button("Add to Watchlist"):
            if w_sym:
                sym = w_sym + ".NS" if ".NS" not in w_sym else w_sym
                try:
                    curr_p = yf.Ticker(sym).fast_info['last_price']
                    new_w = pd.DataFrame([{"Symbol": sym, "Added Date": str(datetime.now().date()), "Added Price": curr_p}])
                    w_df = pd.concat([w_df, new_w], ignore_index=True)
                    w_df.to_csv(WATCHLIST_FILE, index=False)
                    st.rerun()
                except: st.error("Stock price not found!")

    if not w_df.empty:
        st.write("### Performance since Added")
        for i, row in w_df.iterrows():
            try:
                live_p = yf.Ticker(row['Symbol']).fast_info['last_price']
                chg = ((live_p - row['Added Price']) / row['Added Price']) * 100
                cols = st.columns([2, 2, 2, 2])
                cols[0].write(f"**{row['Symbol']}**")
                cols[1].write(f"Added: {row['Added Date']}")
                cols[2].write(f"Price: ₹{live_p:.2f}")
                cols[3].metric("Change %", f"{chg:.2f}%", delta=f"{chg:.2f}%")
                st.divider()
            except: continue
    
