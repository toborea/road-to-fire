import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Road to $500k", page_icon="📈", layout="wide")

st.title("📈 Road to $500k: Mobile Investment Aid")
st.markdown("Optimized for iOS. Track your trajectory and analyze asset overlaps in real-time.")

# --- SIDEBAR: SIMULATION CONTROLS ---
st.sidebar.header("Calculation Settings")

hysa_bal = st.sidebar.number_input("Marcus HYSA Balance ($)", value=57763.26, step=1000.0)
hysa_cont = st.sidebar.number_input("Monthly HYSA Cont. ($)", value=1000.0, step=100.0)
hysa_yield = st.sidebar.slider("HYSA Annual Yield (%)", 1.0, 6.0, 4.2, 0.1) / 100

brok_bal = st.sidebar.number_input("Vanguard Brokerage ($)", value=132500.05, step=1000.0)
brok_cont = st.sidebar.number_input("Monthly Brokerage Cont. ($)", value=5000.0, step=100.0)
brok_return = st.sidebar.slider("Expected Market Return (%)", 4.0, 15.0, 9.0, 0.5) / 100

# --- MAIN PAGE: TICKER SELECTOR ---
st.subheader("Select Your Vanguard Holdings")
default_tickers = ["VOO", "VFIAX", "VTI", "VTV", "VT", "VXUS", "IJH", "AMD", "GOOGL", "CVS"]
selected_tickers = st.multiselect("Tap to add or remove funds currently in your portfolio:", default_tickers, default=default_tickers)

# --- LIVE FINANCIAL DATA ANALYSIS ---
if selected_tickers:
    portfolio_data = []
    with st.spinner("Fetching live data from Yahoo Finance..."):
        for ticker in selected_tickers:
            try:
                asset = yf.Ticker(ticker)
                info = asset.info
                price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
                er = info.get('annualReportExpenseRatio') or info.get('expenseRatio', 0)
                er_pct = er * 100 if er else 0.0
                
                portfolio_data.append({
                    "Ticker": ticker,
                    "Type": info.get('quoteType', 'Fund'),
                    "Live Price": f"${price:.2f}",
                    "Expense Ratio": f"{er_pct:.2f}%",
                    "Raw ER": er_pct
                })
            except:
                pass

    if portfolio_data:
        df = pd.DataFrame(portfolio_data)
        st.dataframe(df.drop(columns=["Raw ER"]), use_container_width=True)
        
        # Smart Advisor Alerts
        st.subheader("Automated Portfolio Advice")
        warnings = 0
        tickers_str = " ".join(selected_tickers)
        
        if "VOO" in tickers_str and "VFIAX" in tickers_str:
            st.error("⚠️ **Redundancy Alert:** You are holding both VOO and VFIAX. They track the exact same S&P 500 index. Consider consolidating into one.")
            warnings += 1
        if "VOO" in tickers_str and "VTI" in tickers_str:
            st.warning("⚠️ **Overlap Alert:** VTI is 85% identical to VOO. Holding both creates heavy large-cap duplication.")
            warnings += 1
        for item in portfolio_data:
            if item["Raw ER"] > 0.15:
                st.warning(f"⚠️ **Fee Notice:** {item['Ticker']} charges {item['Expense Ratio']}. Keep an eye on non-index fund fees.")
                warnings += 1
        if warnings == 0:
            st.success("✅ Your selected asset structure looks clean and streamlined!")

# --- MATHEMATICAL PROJECTION ---
st.subheader("The Path to $500,000")

months = 0
hysa_current = hysa_bal
brok_current = brok_bal
total_current = hysa_current + brok_current

timeline_data = [{"Month": 0, "HYSA": hysa_current, "Brokerage": brok_current, "Total": total_current}]

while total_current < 500000 and months < 120:
    months += 1
    hysa_current = (hysa_current * (1 + hysa_yield/12)) + hysa_cont
    brok_current = (brok_current * (1 + brok_return/12)) + brok_cont
    total_current = hysa_current + brok_current
    timeline_data.append({"Month": months, "HYSA": hysa_current, "Brokerage": brok_current, "Total": total_current})

df_timeline = pd.DataFrame(timeline_data)

# Metrics Display
col1, col2 = st.columns(2)
col1.metric("Current Combined Capital", f"${(hysa_bal + brok_bal):,.2f}")
col2.metric("Months to Reach $500k Target", f"{months} Months" if total_current >= 500000 else "> 10 Years")

# Responsive Mobile Interactive Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_timeline["Month"], y=df_timeline["HYSA"], name="HYSA (Cash)", stackgroup='one', line=dict(color='#3b82f6')))
fig.add_trace(go.Scatter(x=df_timeline["Month"], y=df_timeline["Brokerage"], name="Brokerage (Stocks)", stackgroup='one', line=dict(color='#10b981')))
fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)
