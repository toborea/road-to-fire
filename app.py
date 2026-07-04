# ... (Keep existing imports) ...

# Inside the 'if uploaded_file is not None:' block, replace the logic with this:
    with st.spinner("Processing screenshot..."):
        text = pytesseract.image_to_string(image)
        secure_cleanup(image)
        
        # Regex to find Ticker followed by Share count
        # Looks for: TICKER [spaces] NUMBER
        matches = re.findall(r'\b([A-Z]{1,5})\s+([\d,]+\.?\d*)', text)
        
        if matches:
            for ticker, shares_str in matches:
                # Clean the share count
                shares = float(shares_str.replace(',', ''))
                
                # Check if ticker exists
                if ticker in st.session_state.portfolio["Ticker"].values:
                    # Update shares
                    st.session_state.portfolio.loc[st.session_state.portfolio["Ticker"] == ticker, "Shares"] = shares
                else:
                    # Add new row
                    new_row = pd.DataFrame({"Ticker": [ticker], "Shares": [shares]})
                    st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
            
            st.success("Portfolio updated from screenshot!")
            st.rerun()
        else:
            st.warning("Could not auto-map shares. Please ensure the screenshot clearly shows the Ticker and Share count next to each other.")
