import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import pytesseract
from PIL import Image
import re
import gc

# Page Setup
st.set_page_config(page_title="Live Portfolio Tracker", page_icon="📈", layout="wide")
st.title("📈 Live Portfolio & Goal Tracker")

# Memory Management
def secure_cleanup(image_obj):
    del image_obj
    gc.collect()

# Initialize session state for portfolio
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame({
        "Ticker": ["VOO", "VFIAX", "VTI", "VTV", "VT", "VXUS", "IJH", "AMD", "GOOGL", "CVS"],
        "Shares": [78.467, 18.0, 15.0, 25.0, 80.0, 200.0, 15.0, 34.0, 50.0, 30.0]
    })

# --- SIDEBAR: FINANCIAL INPUTS ---
st.sidebar.header("Cash & Future Savings")
hysa_bal = st.sidebar.number_input("Marcus HYSA Balance ($)", value=57763.26, step=1000.0)
hysa_cont = st.sidebar.number_input("Monthly HYSA Cont. ($)", value=1000.0, step=100.0)
hysa_yield = st.sidebar.slider("HYSA Annual Yield (%)", 1.0, 6.0, 4.2, 0.1) / 100
brok_cont = st.sidebar.number_input("Monthly Brokerage Cont. ($)", value=5000.0, step=100.0)
brok_return = st.sidebar.slider("Expected Market Return (%)", 4.0, 15.0, 9.0, 0.5) / 100

# --- FEATURE: MULTI-FILE SCREENSHOT SCANNER ---
st.subheader("📷 Auto-Update Tickers & Shares")
uploaded_files = st.file_uploader("Upload Brokerage Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        with st.spinner(f"Processing {uploaded_file.name}..."):
            # Extract text from image
            text = pytesseract.image_to_string(image)
            secure_cleanup(image)
            
            # This logic splits the text by lines to look for the pattern line-by-line
            lines = text.split('\n')
            found_data = False
            
            for line in lines:
                # Look for lines that contain a ticker and a number
                # Regex looks for Ticker (uppercase, 1-5 letters) followed by some characters, then a decimal number
                match = re.search(r'\b([A-Z]{1,5})\b.*?\b(\d{1,3}(?:,\d{3})*\.\d{3})\b', line)
                
                if match:
                    ticker = match.group(1)
                    shares_str = match.group(2).replace(',', '')
                    shares = float(shares_str)
                    
                    if ticker in ['LIST', 'TABLE', 'TOTAL', 'NAME', 'QTY']:
                        continue
                        
                    if ticker in st.session_state.portfolio["Ticker"].values:
                        st.session_state.portfolio.loc[st.session_state.portfolio["Ticker"] == ticker, "Shares"] = shares
                    else:
                        new_row = pd.DataFrame({"Ticker": [ticker], "Shares": [shares]})
                        st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
                    found_data = True
            
            if found_data:
                st.success(f"Successfully processed {uploaded_file.name}")
            else:
                st.warning(f"Could not map data in {uploaded_file.name}. OCR text was: {text[:100]}...") # Debug info
    st.rerun()

# --- FEATURE: MASTER PORTFOLIO EDITOR ---
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

# --- FEATURE: LIVE ANALYSIS & PROJECTION ---
if not edited_df.empty:
    total_brokerage_value = 0.0
    with st.spinner("Fetching live prices..."):
        for _, row in edited_df.iterrows():
            try:
                price = yf.Ticker(str(row["Ticker"])).info.get('currentPrice') or 0
                total_brokerage_value += (price * float(row["Shares"]))
            except: pass

    st.subheader("The Path to $500,000")
    total_current = hysa_bal + total_brokerage_value
    col1, col2, col3 = st.columns(3)
    col1.metric("Cash", f"${hysa_bal:,.2f}")
    col2.metric("Brokerage", f"${total_brokerage_value:,.2f}")
    col3.metric("Total", f"${total_current:,.2f}")

    # Calculation loop
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
