import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        # നിഫ്റ്റി 500 ലിസ്റ്റ് ഗിറ്റ്ഹബ്ബിൽ നിന്ന് എടുക്കുന്നു
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        df_n500 = pd.read_csv(url)
        return sorted(df_n500['Symbol'].tolist())
    except:
        # ഇൻ്റർനെറ്റ് ഇല്ലെങ്കിൽ മാത്രം ഈ ലിസ്റ്റ് കാണിക്കും
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # എല്ലാ സംഖ്യാ കോളങ്ങളും നമ്പറുകളാണെന്ന് ഉറപ്പാക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "Today_PnL"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Name", "Buy Date", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status", "CMP"])

def update_live_prices(df):
    holdings = df[df['Status'] == "Holding"]
    tickers = holdings['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="1d", progress=False)['Close']
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    # സിംഗിൾ ടിക്കർ ആണോ മൾട്ടിപ്പിൾ ആണോ എന്ന് നോക്കുന്നു
                    new_p = float(live_data[t_name].iloc[-1]) if len(tickers) > 1 else float(live_data.iloc[-1])
                    df.at[index, 'CMP'] = round(new_p, 2)
                    df.at[index, 'CM Value'] = round(row['QTY Available'] * new_p, 2)
                    df.at[index, 'P&L'] = round(df.at[index, 'CM Value'] - row['Investment'], 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

# --- App Layout ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
nifty500 = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sell Items"])

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    
    if not hold_df.empty:
        # Top Metrics (Decimal ഒഴിവാക്കി)
        t_inv = int(hold_df['Investment'].sum())
        t_val = int(hold_df['CM Value'].sum())
        t_pnl = int(hold_df['P&L'].sum())
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investment", f"₹{t_inv:,}")
        m2.metric("Current Value", f"₹{t_val:,}")
        m3.metric("Total P&L", f"₹{t_pnl:,}")

        # --- ഡിസ്‌പ്ലേ ലിസ്റ്റ് (Decimal Removal Fix) ---
        # ടേബിളിൽ കാണിക്കാൻ മാത്രമുള്ള ഒരു കോപ്പി ഉണ്ടാക്കുന്നു
        display_list = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
        
        # ഓരോ കോളത്തിലെയും ദശാംശങ്ങൾ മാറ്റി Integer ആക്കുന്നു
        display_list['QTY Available'] = display_list['QTY Available'].astype(int)
        display_list['Investment'] = display_list['Investment'].astype(int)
        display_list['Profit/Loss'] = display_list['P&L'].astype(int)
        display_list['Live Price'] = display_list['CMP'].round(2)
        
        # കോളം പേരുകൾ മാറ്റുന്നു
        final_table = display_list[['Name', 'Account', 'QTY Available', 'Live Price', 'Investment', 'Profit/Loss']]
        final_table.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'P&L']

        # ലാഭത്തിന് പച്ചയും നഷ്ടത്തിന് ചുവപ്പും നൽകുന്നു
        def color_pnl(val):
            return f'color: {"#2ecc71" if val > 0 else "#e74c3c" if val < 0 else "white"}'

        st.dataframe(final_table.style.map(color_pnl, subset=['P&L']), use_container_width=True, hide_index=True)

    # --- ADD STOCK SECTION (Nifty 500 Suggestions) ---
    with st.expander("➕ Add New Stock", expanded=True):
        # പോർട്ട്‌ഫോളിയോയിലുള്ള സ്റ്റോക്കുകളും നിഫ്റ്റി 500-ഉം ചേർത്തുള്ള സജഷൻ ലിസ്റ്റ്
        existing_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
        full_stock_list = sorted(list(set(existing_stocks + nifty500)))
        
        # സജഷൻ ബോക്സ്
        selected_s = st.selectbox("Search/Select Stock", full_stock_list)
        
        # ലൈവ് പ്രൈസ് തനിയെ വരുന്നു
        current_mkt_p = 0.0
        if selected_s:
            try:
                ticker_obj = yf.Ticker(selected_s + ".NS")
                current_mkt_p = ticker_obj.fast_info['lastPrice']
                st.info(f"Market Price: ₹{current_mkt_p:.2f}")
            except: pass

        with st.form("add_stock_form"):
            c1, c2 = st.columns(2)
            buy_p = c1.number_input("Buy Price", value=float(current_mkt_p))
            qty_n = c2.number_input("Quantity", min_value=1)
            acc_n = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            
            if st.form_submit_button("Save to Portfolio"):
                new_entry = {
                    "Name": selected_s + ".NS", "Buy Price": buy_p, "QTY Available": qty_n, 
                    "Investment": buy_p * qty_n, "Account": acc_n, "Status": "Holding",
                    "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": current_mkt_p,
                    "CM Value": current_mkt_p * qty_n, "P&L": (current_mkt_p - buy_p) * qty_n
                }
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{selected_s} വിജയകരമായി ചേർത്തു!")
                st.rerun()

# --- TAB 1: HEATMAP ---
with tab1:
    if not hold_df.empty:
        fig = px.treemap(hold_df, path=['Name'], values='Investment', color='P&L', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)
        
