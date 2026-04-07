import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
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
        # സംഖ്യകൾ എല്ലാം നമ്പറുകളാണെന്ന് ഉറപ്പാക്കുന്നു, ഒഴിഞ്ഞവ 0 ആക്കുന്നു
        for col in ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        return df
    return pd.DataFrame(columns=["Name", "Buy Date", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status", "CMP"])

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9")
st.title("📊 Habeeb's Power Hub v6.9")

df = load_data()
nifty500 = get_nifty500_tickers()

# --- PORTFOLIO DISPLAY ---
hold_df = df[df['Status'] == "Holding"].copy()

if not hold_df.empty:
    st.subheader("💼 My Portfolio")
    
    # 1. ഡെസിമൽ ഒഴിവാക്കി ഡിസ്‌പ്ലേ ലിസ്റ്റ് ഉണ്ടാക്കുന്നു
    disp_df = pd.DataFrame()
    disp_df['Stock'] = hold_df['Name']
    disp_df['Account'] = hold_df['Account']
    disp_df['Qty'] = hold_df['QTY Available'].apply(lambda x: int(round(x)))
    disp_df['Price'] = hold_df['CMP'].round(2)
    disp_df['Investment'] = hold_df['Investment'].apply(lambda x: int(round(x)))
    disp_df['P&L'] = hold_df['P&L'].apply(lambda x: int(round(x)))

    def color_pnl(val):
        return f'color: {"#2ecc71" if val > 0 else "#e74c3c" if val < 0 else "white"}'

    st.dataframe(disp_df.style.map(color_pnl, subset=['P&L']), use_container_width=True, hide_index=True)

# --- ADD STOCK SECTION ---
st.divider()
with st.expander("➕ Add New Stock", expanded=True):
    # 2. പോർട്ട്‌ഫോളിയോ + നിഫ്റ്റി 500 സജഷൻ
    port_list = [s.replace(".NS", "") for s in df['Name'].unique()]
    full_list = sorted(list(set(port_list + nifty500)))
    
    sel_stock = st.selectbox("Search Stock", full_list)
    
    # ലൈവ് പ്രൈസ് എടുക്കുന്നു
    live_p = 0.0
    if sel_stock:
        try:
            ticker = yf.Ticker(sel_stock + ".NS")
            live_p = ticker.fast_info['lastPrice']
            st.info(f"Current Price: ₹{live_p:.2f}")
        except: pass

    with st.form("add_form"):
        c1, c2 = st.columns(2)
        # 3. ലൈവ് പ്രൈസ് തനിയെ വരുന്നു
        b_price = c1.number_input("Buy Price", value=float(live_p))
        b_qty = c2.number_input("Quantity", min_value=1)
        b_acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
        
        if st.form_submit_button("Save Stock"):
            new_row = {
                "Name": sel_stock + ".NS", "Buy Price": b_price, "QTY Available": b_qty,
                "Investment": b_price * b_qty, "Account": b_acc, "Status": "Holding",
                "Buy Date": datetime.now().strftime('%Y-%m-%d'), "CMP": live_p,
                "CM Value": live_p * b_qty, "P&L": (live_p - b_price) * b_qty
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.success("സേവ് ചെയ്തു!"); st.rerun()
