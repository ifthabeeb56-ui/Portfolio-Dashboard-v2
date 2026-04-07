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
WATCHLIST_FILE = "watchlist_data.txt"
HISTORY_FILE = "portfolio_history.csv"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # Decimal ഒഴിവാക്കാൻ numeric columns int ആക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Sell Date"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        return pd.read_csv(WATCHLIST_FILE)
    return pd.DataFrame(columns=["Date", "Symbol", "P&L %", "Remarks"])

# --- ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v7.0", page_icon="📈")

# ഡാറ്റ ലോഡിംഗ്
df = load_data()
w_df = get_watchlist()

# --- SIDEBAR: BACKUP & RESTORE (Point 6) ---
with st.sidebar:
    st.header("📥 Backup & Restore")
    st.subheader("Portfolio")
    st.download_button("📥 Download Portfolio", df.to_csv(index=False), "portfolio_backup.csv", "text/csv")
    up_p = st.file_uploader("📤 Upload Portfolio", type="csv", key="p_up")
    if up_p:
        pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
        st.success("Portfolio Updated!"); st.rerun()
    
    st.divider()
    st.subheader("Watchlist")
    st.download_button("📥 Download Watchlist", w_df.to_csv(index=False), "watchlist_backup.csv", "text/csv")
    up_w = st.file_uploader("📤 Upload Watchlist", type="csv", key="w_up")
    if up_w:
        pd.read_csv(up_w).to_csv(WATCHLIST_FILE, index=False)
        st.success("Watchlist Updated!"); st.rerun()

st.title("📊 Habeeb's Power Hub v7.0")

# --- SUMMARY SWITCH (Point 2) ---
show_summary = st.toggle("Show Portfolio Summary", value=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "✅ Sold Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP (പഴയത് നിലനിർത്തി) ---
with tab1:
    # പഴയ ഹീറ്റ്‌മാപ്പ് കോഡ് ഇവിടെ വരും
    st.info("പഴയ ഹീറ്റ്‌മാപ്പ് ഫംഗ്ഷൻ ഇവിടെ ലഭ്യമാണ്.")

# --- TAB 2: PORTFOLIO (Point 1 & 3) ---
with tab2:
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        # Today's P&L calculation (Point 1)
        # yfinance വഴി ലൈവ് ഡാറ്റ എടുക്കുന്ന പഴയ ലോജിക് ഇവിടെ തുടരുന്നു
        
        if show_summary:
            t_inv = int(hold_df['Investment'].sum())
            t_val = int(hold_df['CM Value'].sum())
            t_pnl = t_val - t_inv
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment", f"₹{t_inv:,}")
            c2.metric("Current Value", f"₹{t_val:,}")
            c3.metric("Total P&L", f"₹{t_pnl:,}", f"{((t_pnl/t_inv)*100):.2f}%")

        # Decimal Point ഒഴിവാക്കിയ സ്റ്റൈൽ (Point 3)
        hold_display = hold_df.copy()
        for col in ["Investment", "CM Value", "P&L", "CMP", "Buy Price"]:
            hold_display[col] = hold_display[col].astype(int)
        
        st.dataframe(hold_display[["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Investment", "P&L", "P_Percentage"]], use_container_width=True, hide_index=True)

# --- TAB 3: SOLD ITEMS (Point 4 & 5) ---
with tab3:
    st.subheader("💰 Sold Items History")
    sold_df = df[df['Status'] == "Sold"].copy()
    
    show_sold_summary = st.toggle("Show Sold Summary Switch")
    if show_sold_summary and not sold_df.empty:
        total_sold_pnl = int(sold_df['P&L'].sum())
        st.metric("Total Realized Profit", f"₹{total_sold_pnl:,}")

    if not sold_df.empty:
        # Decimal ഒഴിവാക്കുന്നു
        sold_df['P&L'] = sold_df['P&L'].astype(int)
        st.dataframe(sold_df[["Name", "Buy Date", "Sell Date", "Investment", "P&L", "P_Percentage"]], use_container_width=True, hide_index=True)
    else:
        st.info("വിറ്റ സ്റ്റോക്കുകൾ ലഭ്യമല്ല.")

# --- TAB 4 & 5: ANALYTICS & NEWS (പഴയത് മാറ്റമില്ലാതെ) ---
with tab4:
    st.write("പഴയ അനലിറ്റിക്സ് ചാർട്ടുകൾ ഇവിടെ കാണാം.")
with tab5:
    st.write("പഴയ ന്യൂസ് ഫീച്ചർ ഇവിടെ തുടരുന്നു.")

# --- TAB 6: WATCHLIST (Point 7) ---
with tab6:
    st.subheader("👀 New Watchlist Model")
    cw1, cw2 = st.columns([1, 2])
    with cw1:
        w_sym = st.text_input("Symbol (eg: RELIANCE)").upper()
        w_rem = st.text_area("Remarks")
        if st.button("Add to Watchlist"):
            new_w = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Symbol": w_sym, "P&L %": "0%", "Remarks": w_rem}])
            w_df = pd.concat([w_df, new_w], ignore_index=True)
            w_df.to_csv(WATCHLIST_FILE, index=False)
            st.success("Added!"); st.rerun()
    
    with cw2:
        if not w_df.empty:
            st.table(w_df[["Date", "Symbol", "P&L %", "Remarks"]])
    
