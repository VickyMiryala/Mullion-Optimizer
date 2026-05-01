import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Stock Length Optimizer", layout="wide")

st.title("🏗️ Mullion Die Stock Length Optimizer")
st.write("Upload your `TEST.csv` file to determine the optimal stock length between 140 and 260 inches for each unique die.")

# File Uploader
uploaded_file = st.file_uploader("Upload your TEST.csv file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    st.subheader("📊 Uploaded Data Preview")
    st.dataframe(df.head(), use_container_width=True)
    
    # Process the data
    die_lengths = {}
    for index, row in df.iterrows():
        die = row['Value']
        length = row['L2']
        count = row['Count']
        
        if pd.isna(die):
            continue
            
        if die not in die_lengths:
            die_lengths[die] = []
        # Expand lengths based on the count/frequency
        die_lengths[die].extend([length] * count)
        
    results = []
    
    for die, lengths in die_lengths.items():
        max_req_len = max(lengths)
        
        # Constraints: 
        # 1. Stock length must be >= maximum required length for that die
        # 2. Stock length must be between 140 and 260 inches
        min_stock = math.ceil(max_req_len)
        min_stock = max(140, min_stock)
        max_stock = 260
        
        if min_stock > max_stock:
            results.append({
                "Die": die,
                "Max Required Length (in)": max_req_len,
                "Opt. Stock Length (in)": "N/A",
                "Bars Required": "N/A",
                "Total Scrap (in)": "N/A",
                "Waste %": "N/A",
                "Status": "Exceeds max stock limit of 260 in"
            })
            continue
            
        # Define the allowed range of stock lengths to test
        stock_options = list(range(min_stock, max_stock + 1))
        
        def calculate_mullion_optimization(req_lengths, stock_length):
            sorted_lengths = sorted(req_lengths, reverse=True)
            bins = []
            
            for length in sorted_lengths:
                placed = False
                for b in bins:
                    if sum(b) + length <= stock_length:
                        b.append(length)
                        placed = True
                        break
                if not placed:
                    bins.append([length])
                    
            total_stock_bars = len(bins)
            total_required = sum(req_lengths)
            total_allocated = total_stock_bars * stock_length
            scrap = total_allocated - total_required
            scrap_pct = (scrap / total_allocated) * 100 if total_allocated > 0 else 0
            
            return {
                "stock_length": stock_length,
                "bars_needed": total_stock_bars,
                "scrap_percentage": scrap_pct,
                "scrap_inches": scrap,
            }
            
        die_results = []
        for sl in stock_options:
            die_results.append(calculate_mullion_optimization(lengths, sl))
            
        # Find the layout with the minimum scrap waste
        best_choice = min(die_results, key=lambda x: x['scrap_inches'])
        
        results.append({
            "Die": die,
            "Max Required Length (in)": max_req_len,
            "Opt. Stock Length (in)": best_choice["stock_length"],
            "Bars Required": best_choice["bars_needed"],
            "Total Scrap (in)": round(best_choice["scrap_inches"], 2),
            "Waste %": round(best_choice["scrap_percentage"], 2),
            "Status": "Optimal"
        })
        
    results_df = pd.DataFrame(results)
    
    st.subheader("📋 Optimization Results per Die")
    st.dataframe(results_df, use_container_width=True)
    
    # Download Button
    csv = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Optimized Results",
        data=csv,
        file_name="mullion_die_optimized_output.csv",
        mime="text/csv"
    )
else:
    st.info("⬆️ Await uploading a CSV file in order to run the optimization process.")
