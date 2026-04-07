import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v3.csv"
HISTORY_FILE = "portfolio_history_v3.csv"

# --- 2. ഫങ്ക്ഷനുകൾ ---
def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    else:
        columns = ["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status"]
        return pd.DataFrame(columns=columns)

def get_malayalam_news(stock_symbol):
    try:
        clean_name = stock_symbol.replace(".NS", "").replace(".BO", "")
        googlenews = GoogleNews(lang='en', period='1d')
        googlenews.search(f"{clean_name} share news India")
        results = googlenews.result()
        
        news_list = []
        for item in results[:3]:
            english_title = item['title']
            mal_title = GoogleTranslator(source='auto', target='ml').translate(english_title)
            news_list.append({"title": mal_title, "link": item['link']})
        return news_list
    except:
        return []

# --- 3. ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub", page_icon="📈")
st.title("📊 Habeeb's Power Screener & Portfolio Management")

df = load_data()

tab1, tab2, tab3 = st.tabs(["🔍 Stock Screener", "💼 Portfolio Manager", "📰 മലയാളം വാർത്തകൾ"])

# --- TAB 1: SCREENER (HEAT MAP) ---
with tab1:
    st.subheader("Nifty Market Heat Map")
    watch_list = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]
    if st.button("🚀 Refresh Heat Map"):
        with st.spinner("Fetching Data..."):
            try:
                data = yf.download(watch_list, period="5d")['Close']
                if not data.empty:
                    last_price = data.iloc[-1]
                    prev_price = data.iloc[-2]
                    changes = ((last_price - prev_price) / prev_price) * 100
                    
                    heat_df = pd.DataFrame({
                        "Symbol": watch_list, 
                        "Change %": changes.values, 
                        "Price": last_price.values
                    })
                    fig = px.treemap(heat_df, path=['Symbol'], values='Price', color='Change %',
                                     color_continuous_scale='RdYlGn', title="Market Status")
                    st.plotly_chart(fig, use_container_width=True)
            except:
                st.error("ഡാറ്റ ലഭ്യമാക്കുന്നതിൽ തടസ്സം നേരിട്ടു.")

# --- TAB 2: PORTFOLIO MANAGER ---
with tab2:
    if not df.empty:
        # ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് ലോജിക്
        tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
        if tickers:
            with st.spinner("Updating Live Prices..."):
                try:
                    # ലേറ്റസ്റ്റ് വിലകൾ എടുക്കുന്നു
                    live_data = yf.download(tickers, period="5d", progress=False)['Close']
                    for index, row in df.iterrows():
                        if row['Status'] == "Holding":
                            t_name = row['Name']
                            # ഒന്നിലധികം ടിക്കറുകൾ ഉണ്ടെങ്കിൽ live_data ഒരു DataFrame ആയിരിക്കും
                            if len(tickers) > 1:
                                new_p = live_data[t_name].iloc[-1]
                            else:
                                new_p = live_data.iloc[-1]
                                
                            df.at[index, 'CMP'] = new_p
                            df.at[index, 'CM Value'] = row['QTY Available'] * new_p
                            df.at[index, 'P&L'] = (df.at[index, 'CM Value'] + row['Dividend']) - row['Investment']
                            if row['Investment'] > 0:
                                df.at[index, 'P_Percentage'] = (df.at[index, 'P&L'] / row['Investment']) * 100
                except Exception as e:
                    st.warning(f"ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് ചെയ്യാൻ സാധിച്ചില്ല. Error: {e}")

        # ഡിസ്‌പ്ലേയ്ക്കായി ഹോൾഡിംഗ് ഡാറ്റ ഫിൽട്ടർ ചെയ്യുന്നു
        hold_df = df[df['Status'] == "Holding"].copy()
        hold_df['Chart Link'] = hold_df['Name'].apply(lambda x: f"https://www.tradingview.com/chart/?symbol=NSE:{x.replace('.NS', '')}")
        
        st.subheader("📋 My Portfolio")
        st.dataframe(hold_df, column_config={
            "Chart Link": st.column_config.LinkColumn("Chart", display_text="Open 📈"),
            "P_Percentage": st.column_config.NumberColumn("% P&L", format="%.2f%%"),
            "CMP": "Live Price",
            "P&L": "Profit/Loss",
            "CM Value": "Current Value"
        }, hide_index=True, use_container_width=True)

    # എൻട്രി ഫോം
    with st.expander("➕ പുതിയ ഇൻവെസ്റ്റ്മെന്റ് / ഡിവിഡന്റ് ചേർക്കുക"):
        c1, c2, c3 = st.columns(3)
        with c1:
            cat_in = st.selectbox("Category", ["Equity", "ETF", "SGB", "Gold"])
            name_raw = st.text_input("Stock Symbol (eg: SBIN)")
            name_in = name_raw.upper().strip()
            if name_in and not (".NS" in name_in or ".BO" in name_in):
                name_in += ".NS"
            buy_p = st.number_input("Buy Price", min_value=0.0)
        with c2:
            qty = st.number_input("Quantity", min_value=1)
            buy_dt = st.date_input("Date", datetime.now())
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
        with c3:
            stts = st.selectbox("Status", ["Holding", "Sold"])
            div = st.number_input("Dividend (₹)", value=0.0)
            tax = st.number_input("Tax/Charges (₹)", value=0.0)

        if st.button("💾 Save Entry"):
            if name_in:
                total_inv = (qty * buy_p) + tax
                new_row = {
                    "Category": cat_in, "Buy Date": str(buy_dt), "Name": name_in, 
                    "CMP": buy_p, "Buy Price": buy_p, "QTY Available": qty, 
                    "Account": acc, "Investment": total_inv, "CM Value": total_inv, 
                    "P&L": 0, "P_Percentage": 0, "Tax": tax, "Dividend": div, 
                    "Remark": "", "Status": stts
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{name_in} വിജയകരമായി ചേർത്തു!")
                st.rerun()

# --- TAB 3: മലയാളം വാർത്തകൾ ---
with tab3:
    st.subheader("📰 തത്സമയ സ്റ്റോക്ക് വാർത്തകൾ")
    if not df.empty:
        stock_list = sorted(df['Name'].unique().tolist())
        selected_stock = st.selectbox("ഏത് സ്റ്റോക്കിനെക്കുറിച്ചുള്ള വാർത്തയാണ് വേണ്ടത്?", stock_list)
        if st.button("മലയാളത്തിൽ വാർത്തകൾ കാണുക"):
            with st.spinner("വാർത്തകൾ ശേഖരിക്കുന്നു..."):
                news = get_malayalam_news(selected_stock)
                if news:
                    for n in news:
                        st.info(f"🔹 {n['title']}")
                        st.write(f"🔗 [പൂർണ്ണരൂപം വായിക്കാം]({n['link']})")
                        st.divider()
                else:
                    st.warning("പുതിയ വാർത്തകൾ ഒന്നും കണ്ടെത്താനായില്ല.")
                   
