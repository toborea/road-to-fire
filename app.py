import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import pytesseract
from PIL import Image
import re
import gc
from datetime import datetime

# Page Setup
st.set_page_config(page_title="Live Portfolio Tracker", page_icon="📈", layout="wide")
st.title("📈 Live Portfolio & Goal Tracker")

# Memory Management
def secure_cleanup(image_obj):
    del image_obj
    gc.collect()

# Initialize session state
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame({
        "Ticker": ["VOO", "VFIAX", "VTI", "VTV", "VT", "VXUS", "IJH", "AMD", "GOOGL", "CVS"],
        "Shares": [78.467, 18.0, 15.0, 25.0, 80.0, 200.0, 15.0, 34.0, 50.0, 30.0]
    })

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Date", "HYSA", "Brokerage", "Total"])

# --- SIDEBAR: FINANCIAL INPUTS ---
st.sidebar.header("Cash & Future Savings")
hysa_bal = st.sidebar.number_input("Marcus HYSA Balance ($)", value=57763.26, step=1000.0)
hysa_cont = st.sidebar.number_input("Monthly HYSA Cont. ($)", value=1000.0, step=100.0)
hysa_yield = st.sidebar.slider("HYSA Annual Yield (%)", 1.0, 6.0, 4.2, 0.1) / 100
brok_cont = st.sidebar.number_input("Monthly Brokerage Cont. ($)", value=5000.0, step=100.0)
brok_return = st.sidebar.slider("Expected Market Return (%)", 4.0, 15.0, 9.0, 0.5) / 100

# --- FEATURE: SCREENSHOT SCANNER ---
st.subheader("📷 Auto-Update Tickers & Shares")
uploaded_files = st.file_uploader("Upload Brokerage Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        with st.spinner(f"Processing {uploaded_file.name}..."):
            text = pytesseract.image_to_string(image)
            secure_cleanup(image)
            lines = text.split('\n')
            found_data = False
            for line in lines:
                match = re.search(r'\b([A-Z]{1,5})\b.*?\b(\d{1,3}(?:,\d{3})*\.\d{3})\b', line)
                if match:
                    ticker = match.group(1)
                    shares_str = match.group(2).replace(',', '')
                    shares = float(shares_str)
                    if ticker in ['LIST', 'TABLE', 'TOTAL', 'NAME', 'QTY', 'PRICE']: continue
                    
                    if ticker in st.session_state.portfolio["Ticker"].values:
                        st.session_state.portfolio.loc[st.session_state.portfolio["Ticker"] == ticker, "Shares"] = shares
                    else:
                        new_row = pd.DataFrame({"Ticker": [ticker], "Shares": [shares]})
                        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
                    found_data = True
            if found_data: st.success(f"Successfully processed {uploaded_file.name}")
            else: st.warning(f"Could not map data in {uploaded_file.name}.")
    st.rerun()

# --- FEATURE: MASTER PORTFOLIO EDITOR ---
st.subheader("Your Personal Holdings")
edited_df = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic",
    use_container_width=True,
    column_order=["Ticker", "Shares"],
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker Symbol", required=True),
        "Shares": st.column_config.NumberColumn("Number of Shares", format="%.3f", required=True)
    }
)
st.session_state.portfolio = edited_df

# --- FEATURE: LIVE ANALYSIS & TICKER PRICES ---
st.subheader("Current Holdings & Live Prices")
live_details = []
total_brokerage_value = 0.0
tickers_str = " ".join(edited_df["Ticker"].astype(str).tolist())

with st.spinner("Fetching live prices..."):
    for _, row in edited_df.iterrows():
        try:
            ticker = str(row["Ticker"]).upper().strip()
            shares = float(row["Shares"])
            asset = yf.Ticker(ticker)
            price = asset.info.get('currentPrice') or asset.info.get('regularMarketPrice')
            er = asset.info.get('annualReportExpenseRatio') or asset.info.get('expenseRatio', 0)
            if price:
                total_brokerage_value += (price * shares)
                live_details.append({
                    "Ticker": ticker, 
                    "Shares": shares, 
                    "Live Price": f"${price:,.2f}", 
                    "Total Value": f"${(price * shares):,.2f}", 
                    "ER": er*100
                })
        except: pass

# Display live price table
if live_details:
    st.table(pd.DataFrame(live_details).set_index("Ticker"))

# Advice
st.subheader("Automated Portfolio Advice")
if "VOO" in tickers_str and "VFIAX" in tickers_str: st.error("⚠️ Redundancy: Consolidate VOO and VFIAX.")
if "VOO" in tickers_str and "VTI" in tickers_str: st.warning("⚠️ Overlap: VTI is 85% identical to VOO.")
for item in live_details:
    if item.get("ER", 0) > 0.15: st.warning(f"⚠️ Fee Notice: {item['Ticker']} has an expense ratio of {item.get('ER', 0):.2f}%.")

# --- FEATURE: SNAPSHOTS & PROJECTION ---
st.subheader("Current Values & Net Worth")
col1, col2, col3 = st.columns(3)
col1.metric("Cash (HYSA)", f"${hysa_bal:,.2f}")
col2.metric("Brokerage (Live)", f"${total_brokerage_value:,.2f}")
col3.metric("Total Net Worth", f"${(hysa_bal + total_brokerage_value):,.2f}")

st.subheader("Historical Snapshots & Projection")
if st.button("💾 Save Current Net Worth Snapshot"):
    new_snapshot = pd.DataFrame({
        "Date": [datetime.now().strftime("%Y-%m-%d")], 
        "HYSA": [hysa_bal], 
        "Brokerage": [total_brokerage_value], 
        "Total": [hysa_bal + total_brokerage_value]
    })
    st.session_state.history = pd.concat([st.session_state.history, new_snapshot], ignore_index=True)

# History Plot
if not st.session_state.history.empty:
    st.write("### Your Progress")
    st.line_chart(st.session_state.history.set_index("Date")[["HYSA", "Brokerage", "Total"]])

# Future Projection Chart
st.write("### Future Projection to $500k")
months, hysa_curr, brok_curr = 0, hysa_bal, total_brokerage_value
proj_data = [{"Month": 0, "HYSA": hysa_curr, "Brokerage": brok_curr}]
while (hysa_curr + brok_curr) < 500000 and months < 120:
    months += 1
    hysa_curr = (hysa_curr * (1 + hysa_yield/12)) + hysa_cont
    brok_curr = (brok_curr * (1 + brok_return/12)) + brok_cont
    proj_data.append({"Month": months, "HYSA": hysa_curr, "Brokerage": brok_curr})

df_proj = pd.DataFrame(proj_data).set_index("Month")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_proj.index, y=df_proj["HYSA"], name="HYSA", stackgroup='one', line=dict(color='#3b82f6')))
fig.add_trace(go.Scatter(x=df_proj.index, y=df_proj["Brokerage"], name="Brokerage", stackgroup='one', line=dict(color='#10b981')))
fig.update_layout(template="plotly_dark", height=400, xaxis_title="Months", yaxis_title="Total Value ($)")
st.plotly_chart(fig, use_container_width=True)
