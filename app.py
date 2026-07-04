# --- FEATURE: SCREENSHOT SCANNER (UPDATED) ---
st.subheader("📷 Auto-Update Tickers & Shares")
# 'accept_multiple_files=True' allows you to upload more than one at a time
uploaded_files = st.file_uploader("Upload Brokerage Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        with st.spinner(f"Processing {uploaded_file.name}..."):
            text = pytesseract.image_to_string(image)
            secure_cleanup(image)
            
            # This Regex looks for a Ticker (e.g., VOO) 
            # followed by any amount of text, then a number (Quantity)
            # It is more forgiving of column spacing
            matches = re.findall(r'\b([A-Z]{1,5})\s+[\w\s]+\s+([\d,]+\.?\d*)', text)
            
            if matches:
                for ticker, shares_str in matches:
                    try:
                        shares = float(shares_str.replace(',', ''))
                        if ticker in st.session_state.portfolio["Ticker"].values:
                            st.session_state.portfolio.loc[st.session_state.portfolio["Ticker"] == ticker, "Shares"] = shares
                        else:
                            new_row = pd.DataFrame({"Ticker": [ticker], "Shares": [shares]})
                            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
                    except:
                        continue
                st.success(f"Processed {uploaded_file.name}")
            else:
                st.warning(f"Could not map data in {uploaded_file.name}. Ensure 'Quantity' is visible.")
    st.rerun()
