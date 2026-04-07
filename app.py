import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE)
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Sell Date", "Sell Price"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        df_w = pd.read_csv(WATCHLIST_FILE)
        return df_w
    return pd.DataFrame(columns=["Date", "Symbol", "Remarks"])

# --- ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v7.0")
df = load_data()

# --- SIDEBAR: BACKUP & RESTORE ---
with st.sidebar:
    st.title("⚙️ Settings & Backup")
    st.subheader("Portfolio")
    st.download_button("📥 Download Portfolio", df.to_csv(index=False), "portfolio.csv", "text/csv")
    up_p = st.file_uploader("📤 Upload Portfolio", type="csv")
    if up_p:
        pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
        st.success("Updated!"); st.rerun()
    
    st.divider()
    st.subheader("Watchlist")
    w_df = get_watchlist()
    st.download_button("📥 Download Watchlist", w_df.to_csv(index=False), "watchlist.csv", "text/csv")
    up_w = st.file_uploader("📤 Upload Watchlist", type="csv")
    if up_w:
        pd.read_csv(up_w).to_csv(WATCHLIST_FILE, index=False)
        st.success("Updated!"); st.rerun()

# --- MAIN APP ---
st.title("📊 Habeeb's Power Hub v7.0")

show_summary = st.toggle("Show Portfolio Summary", value=True)

tab1, tab2, tab3 = st.tabs(["💼 Portfolio", "💰 Sold Items", "👀 Watchlist"])

# --- TAB 1: PORTFOLIO ---
with tab1:
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        # Decimal point ഒഴിവാക്കാൻ റൗണ്ട് ചെയ്യുന്നു
        t_inv = int(hold_df['Investment'].sum())
        t_val = int(hold_df['CM Value'].sum())
        t_pnl = t_val - t_inv
        
        if show_summary:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment", f"₹{t_inv:,}")
            c2.metric("Current Value", f"₹{t_val:,}")
            c3.metric("Total P&L", f"₹{t_pnl:,}", f"{((t_pnl/t_inv)*100):.2f}%")

        # Table Display
        display_df = hold_df[["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "P&L", "P_Percentage"]].copy()
        display_df['P&L'] = display_df['P&L'].astype(int) # Decimal removal
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- TAB 2: SOLD ITEMS ---
with tab3: # (Tab index check logically)
    pass 

with tab2:
    st.subheader("✅ Sold Assets Summary")
    sold_df = df[df['Status'] == "Sold"].copy()
    if not sold_df.empty:
        sold_summary_switch = st.toggle("Show Sold Summary")
        if sold_summary_switch:
            total_sold_pnl = int(sold_df['P&L'].sum())
            st.metric("Total Realized P&L", f"₹{total_sold_pnl:,}")
        
        st.dataframe(sold_df[["Name", "Buy Date", "Sell Date", "Investment", "P&L", "P_Percentage"]], use_container_width=True, hide_index=True)
    else:
        st.info("വിറ്റ സ്റ്റോക്കുകൾ ഒന്നും തന്നെയില്ല.")

# --- TAB 3: WATCHLIST ---
with tab3:
    st.subheader("👀 My Watchlist")
    col_w1, col_w2 = st.columns([1, 2])
    with col_w1:
        w_sym = st.text_input("Symbol").upper()
        w_rem = st.text_input("Remarks")
        if st.button("Add to Watchlist"):
            new_w = pd.DataFrame([{"Date": str(datetime.now().date()), "Symbol": w_sym, "Remarks": w_rem}])
            w_df = pd.concat([w_df, new_w], ignore_index=True)
            w_df.to_csv(WATCHLIST_FILE, index=False); st.rerun()
    
    with col_w2:
        if not w_df.empty:
            # ലൈവ് പ്രൈസ് പഴ്സന്റേജ് മാത്രം കാണിക്കുന്നു
            if st.button("Refresh Watchlist Prices"):
                with st.spinner("Fetching..."):
                    tickers = w_df['Symbol'].tolist()
                    prices = yf.download([t+".NS" for t in tickers], period="2d", progress=False)['Close']
                    # ഇവിടുത്തെ ലോജിക് പ്രൈസ് % കാണിക്കാൻ ഉപയോഗിക്കാം
            st.table(w_df) # Simplified list with Date, Symbol, Remarks

# --- STOCK ENTRY SECTION ---
with st.expander("➕ Add New Stock / Sell Stock"):
    # (ഇവിടെ പഴയതുപോലെ തന്നെ സ്റ്റോക്ക് ആഡ് ചെയ്യാനുള്ള ഫോം വരും)
    pass
    
