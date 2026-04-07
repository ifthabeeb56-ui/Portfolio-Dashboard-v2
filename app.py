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
        # ഡാറ്റാ ടൈപ്പുകൾ നമ്പറുകളാണെന്ന് ഉറപ്പാക്കുന്നു (TypeError ഒഴിവാക്കാൻ)
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L"]
        for col in num_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        # അക്കൗണ്ട് കോളം ഇല്ലെങ്കിൽ പുതിയത് ഉണ്ടാക്കുന്നു
        if "Account" not in df.columns: df["Account"] = "General"
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
                current_price = data[name].iloc[-1] if len(tickers) > 1 else data.iloc[-1]
                df.at[idx, 'CMP'] = round(float(current_price), 2)
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
    # Account കോളം കൂടി ലിസ്റ്റിൽ ഉൾപ്പെടുത്തി
    display_df = hold_df[['Name', 'Account', 'QTY Available', 'CMP', 'Investment', 'P&L']].copy()
    display_df.columns = ['Stock', 'Account', 'Qty', 'Live Price', 'Investment', 'Profit/Loss']
    
    # കളർ കോഡിംഗ് (ലാഭം പച്ച, നഷ്ടം ചുവപ്പ്)
    def color_pnl(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'white'
        return f'color: {color}'

    st.dataframe(display_df.style.applymap(color_pnl, subset=['Profit/Loss']), 
                 use_container_width=True, hide_index=True)

# --- ADD SECTION ---
with st.expander("➕ Add New Stock"):
    with st.form("add_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Symbol (eg: RELIANCE.NS)")
            b_price = st.number_input("Buy Price", 0.0)
        with col_b:
            qty = st.number_input("Qty", 1)
            acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"]) # അക്കൗണ്ട് സെലക്ഷൻ
        
        if st.form_submit_button("Save Stock"):
            new_data = {
                "Name": name.upper(), 
                "Buy Price": b_price, 
                "QTY Available": qty, 
                "Investment": b_price*qty, 
                "Status": "Holding", 
                "Account": acc, 
                "Buy Date": datetime.now().strftime('%Y-%m-%d')
            }
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.success(f"{name} added to {acc} account!")
            st.rerun()

# --- SELL SECTION ---
with st.expander("🔄 Sell Stock"):
    # സ്റ്റോക്കിനൊപ്പം അക്കൗണ്ട് പേരും കാണിക്കുന്നു
    df['Label'] = df['Name'] + " (" + df['Account'] + ")"
    sell_label = st.selectbox("വിൽക്കേണ്ട സ്റ്റോക്ക് തിരഞ്ഞെടുക്കുക", ["None"] + list(df[df['Status']=='Holding']['Label'].unique()))
    
    if sell_label != "None":
        selected_stock = sell_label.split(" (")[0]
        selected_acc = sell_label.split(" (")[1].replace(")", "")
        
        # കൃത്യമായ സ്റ്റോക്കും അക്കൗണ്ടും ഫിൽട്ടർ ചെയ്യുന്നു
        current_holding = df[(df['Name'] == selected_stock) & (df['Account'] == selected_acc) & (df['Status'] == 'Holding')]
        total_qty = int(current_holding['QTY Available'].sum())
        
        st.info(f"Available in {selected_acc}: {total_qty}")
        
        c1, c2 = st.columns(2)
        qty_to_sell = c1.number_input("വിൽക്കേണ്ട എണ്ണം", 1, total_qty)
        s_price = c2.number_input("വിൽക്കുന്ന വില", 0.0)
            
        if st.button("✅ Confirm Sell"):
            for idx, row in current_holding.iterrows():
                if qty_to_sell <= 0: break
                can_sell = min(qty_to_sell, row['QTY Available'])
                
                # Sold Entry
                sold_entry = row.copy()
                sold_entry['Status'], sold_entry['QTY Available'], sold_entry['Sell_Price'] = 'Sold', can_sell, s_price
                sold_entry['Sell_Date'] = datetime.now().strftime('%Y-%m-%d')
                df = pd.concat([df, pd.DataFrame([sold_entry])], ignore_index=True)
                
                # Update Holding
                if row['QTY Available'] == can_sell: df.drop(idx, inplace=True)
                else: 
                    df.at[idx, 'QTY Available'] -= can_sell
                    df.at[idx, 'Investment'] = df.at[idx, 'QTY Available'] * row['Buy Price']
                qty_to_sell -= can_sell
                
            df.drop(columns=['Label'], inplace=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.success("Sold!")
            st.rerun()
            
