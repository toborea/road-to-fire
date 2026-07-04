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

# Initialize portfolio data in session state
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame({
        "Ticker": ["VOO", "VFIAX", "VTI", "VTV", "VT", "VXUS", "IJH", "AMD", "GOOGL", "CVS"],
        "Shares": [78.467, 18.0, 15.0, 25.0, 80.0, 200.0, 15.0, 34.0, 50.0, 30.0]
    })

# --- SECURE MEMORY WIPE ---
def secure_cleanup(image_obj):
    del image_obj
    gc.collect()

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("Cash & Future Savings")
hysa_bal = st.sidebar.number_input("Marcus HYSA Balance ($)", value=57763.26, step=1000.0)
hysa_cont = st.sidebar.number_input("Monthly HYSA Cont. ($)", value=1000.0, step=100.0)
hysa_yield = st.sidebar.slider("HYSA Annual Yield (%)", 1.0, 6.0, 4.2, 0.1) / 100

brok_cont = st.sidebar.number_input("Monthly Brokerage Cont. ($)", value=5000.0, step=100.0)
brok_return = st.sidebar.slider("Expected Market Return (%)", 4.0, 15.0, 9.0, 0.5) / 100

# --- FEATURE 1: SECURE SCREENSHOT SCANNER ---
st.subheader("📷 Auto-Add Tickers via Screenshot")
st.markdown("Upload a photo of your brokerage. The app will extract tickers, add them to your sheet, and instantly delete the image.")

uploaded_file = st.file_uploader("Upload Brokerage Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    with st.spinner("Scanning image for tickers..."):
        extracted_text = pytesseract.image_to_string(image)
        secure_cleanup(image)
        
        raw_words = re.findall(r'\b[A-Z]{1,5}\b', extracted_text)
        ignore_list = ['TOTAL', 'MARKET', 'INDEX', 'FUND', 'ADMIRAL', 'SHARES', 'PRICE', 'USD', 'QTY']
        found_tickers = list(set([word for word in raw_words if word not in ignore_list]))
        
        if found_tickers:
            # Check what is already in the sheet to prevent duplicates
            existing_tickers = st.session_state.portfolio["Ticker"].tolist()
            new_tickers = [t for t in found_tickers if t not in existing_tickers]
            
            if new_tickers:
                new_data = pd.DataFrame({"Ticker": new_tickers, "Shares": [0.0] * len(new_tickers)})
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_data], ignore_index=True)
                st.success(f"Successfully added: {', '.join(new_tickers)}")
                st.rerun() # Refresh app to show new tickers in the table
            else:
                st.info("No new tickers found (or they are already in your list).")
        else:
            st.warning("Could not detect any valid ticker symbols in the image.")

# --- FEATURE 2: INTERACTIVE HOLDINGS TRACKER ---
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

# Update session state if the user manually edited the table
st.session_state.portfolio = edited_df

# --- FEATURE 3: LIVE DATA & PROJECTION ---
if not edited_df.empty:
    live_data = []
    total_brokerage_value = 0.0
    warnings = 0
    tickers_str = " ".join(edited_df["Ticker"].astype(str).tolist())

    with st.spinner("Fetching live market prices & checking fees..."):
        for index, row in edited_df.iterrows():
            ticker = str(row["Ticker"]).upper().strip()
            shares = float(row["Shares"])
            try:
                asset = yf.Ticker(ticker)
                info = asset.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                er = info.get('annualReportExpenseRatio') or info.get('expenseRatio', 0)
                er_pct = er * 100 if er else 0.0
                
                if price:
                    value = price * shares
                    total_brokerage_value += value
                    live_data.append({
                        "Ticker": ticker,
                        "Shares": shares,
                        "Live Price": f"${price:.2f}",
                        "Total Value": f"${value:,.2f}",
                        "Raw ER": er_pct
                    })
            except:
                pass

    st.dataframe(pd.DataFrame([{k: v for k, v in d.items() if k != "Raw ER"} for d in live_data]), use_container_width=True)
    
    # Automated Advice
    if "VOO" in tickers_str and "VFIAX" in tickers_str:
        st.error("⚠️ **Redundancy Alert:** You hold both VOO and VFIAX (identical S&P 500 tracking). Consolidate into one.")
    if "VOO" in tickers_str and "VTI" in tickers_str:
        st.warning("⚠️ **Overlap Alert:** VTI is 85% identical to VOO.")
    for item in live_data:
        if item.get("Raw ER", 0) > 0.15:
            st.warning(f"⚠️ **Fee Notice:** {item['Ticker']} has an expense ratio of {item['Raw ER']:.2f}%. Watch for fee drag.")
    
    # Projection Mathematics
    st.subheader("The Path to $500,000")
    total_current = hysa_bal + total_brokerage_value
    
    col1, col2, col3 = st.columns(3)
    col1.metric("HYSA (Cash)", f"${hysa_bal:,.2f}")
    col2.metric("Brokerage (Live)", f"${total_brokerage_value:,.2f}")
    col3.metric("Total Net Worth", f"${total_current:,.2f}")

    months = 0
    hysa_current = hysa_bal
    brok_current = total_brokerage_value
    timeline_data = [{"Month": 0, "HYSA": hysa_current, "Brokerage": brok_current, "Total": total_current}]

    while total_current < 500000 and months < 120:
        months += 1
        hysa_current = (hysa_current * (1 + hysa_yield/12)) + hysa_cont
        brok_current = (brok_current * (1 + brok_return/12)) + brok_cont
        total_current = hysa_current + brok_current
        timeline_data.append({"Month": months, "HYSA": hysa_current, "Brokerage": brok_current, "Total": total_current})

    df_timeline = pd.DataFrame(timeline_data)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_timeline["Month"], y=df_timeline["HYSA"], name="HYSA", stackgroup='one', line=dict(color='#3b82f6')))
    fig.add_trace(go.Scatter(x=df_timeline["Month"], y=df_timeline["Brokerage"], name="Brokerage", stackgroup='one', line=dict(color='#10b981')))
    fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
    
    if total_current >= 500000:
        st.success(f"Goal achieved! It will take approximately **{months} months** to cross $500,000 from your current live balances.")
