import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# --- ഫയൽ ക്രമീകരണങ്ങൾ ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # ഡാറ്റാ ടൈപ്പുകൾ നമ്പറുകളാണെന്ന് ഉറപ്പാക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        # അക്കൗണ്ട് കോളം ഇല്ലെങ്കിൽ പുതിയത് ചേർക്കുന്നു
        if "Account" not in df.columns: df["Account"] = "Habeeb"
        return df
    return pd.DataFrame(columns=["Name", "Buy Date", "Buy Price", "QTY Available", "Investment", "Status", "Account"])

def update_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        data = yf.download(tickers, period="1d", progress=False)['Close']
        for idx, row in df.iterrows():
            if row['Status'] == "Holding":
                name = row['Name']
                val = data[name].iloc[-1] if len(tickers) > 1 else data.iloc[-1]
                df.at[idx, 'CMP'] = round(float(val), 2)
                df.at[idx, 'CM Value'] = round(df.at[idx, 'CMP'] * row['QTY Available'], 2)
                df.at[idx, 'P&L'] = round(df.at[idx, 'CM Value'] - row['Investment'], 2)
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: pass
    return df

st.title("📊 Habeeb's Power Hub v6.9")

df = load_data()
df = update_prices(df)

# --- PORTFOLIO LIST ---
hold_df = df[df['Status'] == "Holding"].copy()

if not hold_df.empty:
    st.subheader("💼 My Portfolio")
    
    # Account കോളം ഉൾപ്പെടുത്തിയ ക്ലീൻ ലിസ്റ്റ്
    display_df = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
    display_df.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'Profit/Loss']
    
    # ലാഭനഷ്ടങ്ങൾക്കനുസരിച്ച് നിറം മാറ്റാൻ
    def color_pnl(val):
        color = '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else 'white'
        return f'color: {color}'

    # ലിസ്റ്റ് ഡിസ്പ്ലേ (Updated with .map() for Pandas 2.0+)
    st.dataframe(
        display_df.style.map(color_pnl, subset=['Profit/Loss']), 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("പോർട്ട്‌ഫോളിയോയിൽ സ്റ്റോക്കുകൾ ഒന്നുമില്ല.")

# --- ADD SECTION ---
with st.expander("➕ Add New Stock"):
    with st.form("add_stock_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Stock Symbol (eg: RELIANCE.NS)").upper()
            price = st.number_input("Buy Price", min_value=0.0)
        with c2:
            qty = st.number_input("Quantity", min_value=1)
            acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"]) # അക്കൗണ്ട് തിരഞ്ഞെടുക്കാം
        
        if st.form_submit_button("Save Stock"):
            if name:
                new_row = {
                    "Name": name, "Buy Price": price, "QTY Available": qty, 
                    "Investment": price*qty, "Status": "Holding", "Account": acc,
                    "Buy Date": datetime.now().strftime('%Y-%m-%d')
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{name} added to {acc} account!")
                st.rerun()
