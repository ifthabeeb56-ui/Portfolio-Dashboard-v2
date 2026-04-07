import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# --- 1. ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

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
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        if "Status" not in df.columns: df["Status"] = "Holding"
        return df
    return pd.DataFrame(columns=["Name", "Buy Date", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status", "CMP"])

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9")
df = load_data()
nifty500 = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2 = st.tabs(["💼 Portfolio", "➕ Add Stock"])

# --- TAB 1: PORTFOLIO ---
with tab1:
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        # മുകളിലെ സംഖ്യകൾ (Decimal ഒഴിവാക്കി)
        inv = int(hold_df['Investment'].sum())
        pnl = int(hold_df['P&L'].sum())
        
        c1, c2 = st.columns(2)
        c1.metric("Total Investment", f"₹{inv:,}")
        c2.metric("Total P&L", f"₹{pnl:,}")

        # ഡിസ്‌പ്ലേ ലിസ്റ്റ് തയ്യാറാക്കുന്നു
        # എറർ വരാതിരിക്കാൻ astype(int) ന് പകരം round(0) ഉപയോഗിക്കുന്നു
        disp = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
        
        # ടേബിളിൽ കാണിക്കുമ്പോൾ മാത്രം ദശാംശം ഒഴിവാക്കാൻ പാണ്ഡാസ് സ്റ്റൈലിംഗ് ഉപയോഗിക്കുന്നു
        st.dataframe(
            disp.style.format({
                'QTY Available': '{:.0f}',
                'Investment': '{:.0f}',
                'P&L': '{:.0f}',
                'CMP': '{:.2f}'
            }).map(lambda x: f'color: {"#2ecc71" if x > 0 else "#e74c3c" if x < 0 else "white"}', subset=['P&L']),
            use_container_width=True, hide_index=True
        )

# --- TAB 2: ADD STOCK ---
with tab2:
    # നിഫ്റ്റി 500 സജഷൻ ലിസ്റ്റ്
    port_stocks = [s.replace(".NS", "") for s in df['Name'].unique()]
    search_list = sorted(list(set(port_stocks + nifty500)))
    
    selected = st.selectbox("സ്റ്റോക്ക് തിരഞ്ഞെടുക്കുക", search_list)
    
    # ലൈവ് പ്രൈസ് തനിയെ വരാൻ
    live_price = 0.0
    if selected:
        try:
            t = yf.Ticker(selected + ".NS")
            live_price = t.fast_info['lastPrice']
            st.info(f"ഇപ്പോഴത്തെ വില: ₹{live_price:.2f}")
        except: pass

    with st.form("add_new"):
        col1, col2 = st.columns(2)
        # ലൈവ് പ്രൈസ് ഡിഫോൾട്ട് ആയി വരുന്നു
        bp = col1.number_input("Buy Price", value=float(live_price))
        bq = col2.number_input("Quantity", min_value=1)
        acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
        
        if st.form_submit_button("Save"):
            new_row = {
                "Name": selected + ".NS", "Buy Price": bp, "QTY Available": bq,
                "Investment": bp * bq, "Account": acc, "Status": "Holding",
                "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": live_price,
                "CM Value": live_price * bq, "P&L": (live_price - bp) * bq
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.success("വിജയകരമായി ചേർത്തു!")
            st.rerun()
        
