import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Advanced Mullion Optimizer", layout="wide")

st.title("🏗️ Advanced Mullion Die Stock Length Optimizer")
st.write("Upload your production file to generate the cut layout per bar for each unique die profile.")

uploaded_file = st.file_uploader("Upload TEST.csv", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    st.success("File successfully loaded!")
    
    die_lengths = {}
    for index, row in df.iterrows():
        die = row['Value']
        length = row['L2']
        count = row['Count']
        
        if pd.isna(die):
            continue
            
        if die not in die_lengths:
            die_lengths[die] = []
        die_lengths[die].extend([length] * count)
        
    results = []
    
    # Iterate through unique dies
    for die, lengths in die_lengths.items():
        max_req = max(lengths)
        min_stock = max(140, math.ceil(max_req))
        
        # Test available stock bars between the minimum required length and the upper bound of 260 inches.
        valid_stocks = [s for s in range(140, 261) if s >= min_stock]
        
        if not valid_stocks:
            continue
            
        # Optimization logic
        def get_bins(req_lengths, stock_length):
            sorted_len = sorted(req_lengths, reverse=True)
            bins = []
            for length in sorted_len:
                placed = False
                for b in bins:
                    if sum(b) + length <= stock_length:
                        b.append(length)
                        placed = True
                        break
                if not placed:
                    bins.append([length])
            return bins
            
        best_sl = None
        best_bins = []
        for sl in valid_stocks:
            bins = get_bins(lengths, sl)
            if best_sl is None or len(bins) < len(best_bins):
                best_sl = sl
                best_bins = bins
                
        total_required = sum(lengths)
        total_allocated = len(best_bins) * best_sl
        scrap = total_allocated - total_required
        waste_pct = (scrap / total_allocated) * 100
        
        results.append({
            "Die": die,
            "Required Length (in)": total_required,
            "Optimal Stock Length (in)": best_sl,
            "Bars Required": len(best_bins),
            "Scrap (in)": round(scrap, 2),
            "Waste %": round(waste_pct, 2)
        })
        
    out_df = pd.DataFrame(results)
    st.dataframe(out_df, use_container_width=True)
    
    csv = out_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Optimized Output", 
        data=csv, 
        file_name="mullion_die_optimized.csv", 
        mime="text/csv"
    )
