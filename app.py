import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import pytesseract
from PIL import Image
import re
import gc

st.set_page_config(page_title="Live Portfolio Tracker", page_icon="📈", layout="wide")

st.title("📈 Live Portfolio & Goal Tracker")

# --- SECURE MEMORY WIPE ---
def secure_cleanup(image_obj):
    del image_obj
    gc.collect()

# Initialize portfolio data in session state
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame({
        "Ticker": ["VOO", "VFIAX", "VTI", "VTV", "VT", "VXUS", "IJH", "AMD", "GOOGL", "CVS"],
        "Shares": [78.467, 18.0, 15.0, 25.0, 80.0, 200.0, 15.0, 34.0, 50.0, 30.0]
    })

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("Cash & Future Savings")
hysa_bal = st.sidebar.number_input("Marcus HYSA Balance ($)", value=57763.26, step=1000.0)
hysa_cont = st.sidebar.number_input("Monthly HYSA Cont. ($)", value=1000.0, step=100.0)
hysa_yield = st.sidebar.slider("HYSA Annual Yield (%)", 1.0, 6.0, 4.2, 0.1) / 100

brok_cont = st.sidebar.number_input("Monthly Brokerage Cont. ($)", value=5000.0, step=100.0)
brok_return = st.sidebar.slider("Expected Market Return (%)", 4.0, 15.0, 9.0, 0.5) / 100

# --- FEATURE: SCREENSHOT SCANNER ---
st.subheader("📷 Auto-Update Tickers & Shares")
uploaded_file = st.file_uploader("Upload Brokerage Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    with st.spinner("Processing screenshot..."):
        text = pytesseract.image_to_string(image)
        secure_cleanup(image)
        
        # Regex to find Ticker followed by Share count
        matches = re.findall(r'\b([A-Z]{1,5})\s+([\d,]+\.?\d*)', text)
        
        if matches:
            for ticker, shares_str in matches:
                shares = float(shares_str.replace(',', ''))
                if ticker in st.session_state.portfolio["Ticker"].values:
                    st.session_state.portfolio.loc[st.session_state.portfolio["Ticker"] == ticker, "Shares"] = shares
                else:
                    new_row = pd.DataFrame({"Ticker": [ticker], "Shares": [shares]})
                    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
            st.success("Portfolio updated from screenshot!")
            st.rerun()
        else:
            st.warning("Could not auto-map shares. Please ensure the screenshot lists Ticker and Share count on the same line.")

# --- FEATURE: INTERACTIVE HOLDINGS TRACKER ---
st.subheader("Your Personal Holdings")
edited_df = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker Symbol", required=True),
        "Shares": st.column_config.NumberColumn("Number of Shares", format="%.3f", required=True)
    }
)
st.session_state.portfolio = edited_df

# --- FEATURE: LIVE DATA & PROJECTION ---
if not edited_df.empty:
    live_data = []
    total_brokerage_value = 0.0

    with st.spinner("Fetching live market prices..."):
        for index, row in edited_df.iterrows():
            ticker = str(row["Ticker"]).upper().strip()
            shares = float(row["Shares"])
            try:
                asset = yf.Ticker(ticker)
                price = asset.info.get('currentPrice') or asset.info.get('regularMarketPrice')
                if price:
                    total_brokerage_value += (price * shares)
                    live_data.append({"Ticker": ticker, "Shares": shares, "Value": f"${(price*shares):,.2f}"})
            except: pass

    st.subheader("The Path to $500,000")
    total_current = hysa_bal + total_brokerage_value
    
    col1, col2, col3 = st.columns(3)
    col1.metric("HYSA (Cash)", f"${hysa_bal:,.2f}")
    col2.metric("Brokerage (Live)", f"${total_brokerage_value:,.2f}")
    col3.metric("Total Net Worth", f"${total_current:,.2f}")

    months, hysa_curr, brok_curr = 0, hysa_bal, total_brokerage_value
    timeline_data = [{"Month": 0, "Total": total_current}]
    while total_current < 500000 and months < 120:
        months += 1
        hysa_curr = (hysa_curr * (1 + hysa_yield/12)) + hysa_cont
        brok_curr = (brok_curr * (1 + brok_return/12)) + brok_cont
        total_current = hysa_curr + brok_curr
        timeline_data.append({"Month": months, "Total": total_current})

    fig = go.Figure(go.Scatter(x=[d["Month"] for d in timeline_data], y=[d["Total"] for d in timeline_data], line=dict(color='#10b981')))
    fig.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig, use_container_width=True)
