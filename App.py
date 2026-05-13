import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Optimized layout with consolidated custom stock lengths for oversized profiles.")

# --- Sidebar: Configuration Parameters ---
st.sidebar.header("⚙️ Configuration Parameters")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Side (in)", value=2.0, step=0.125)
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

run_mode = st.sidebar.radio("Select Processing Mode", ("Process All Dies", "Process Die Individually"))
input_method = st.radio("Select Input Method", ("Upload CSV", "Paste Data Manually"))

# --- Core Logic Function ---
def calculate_mullion_optimization(req_lengths, stock_length, trim_total, kerf):
    sorted_lengths = sorted(req_lengths, reverse=True)
    bins = []
    usable_stock = stock_length - trim_total
    for length in sorted_lengths:
        placed = False
        for b in bins:
            potential_space = sum(b) + length + (len(b) * kerf)
            if potential_space <= usable_stock:
                b.append(length)
                placed = True
                break
        if not placed: bins.append([length])
    return bins

# --- Data Input Handling ---
df = None
if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your TEST.csv file", type=["csv"])
    if uploaded_file: df = pd.read_csv(uploaded_file)
else:
    pasted_data = st.text_area("Data Inputs", height=150)
    if pasted_data:
        rows = []
        for line in pasted_data.strip().split("\n"):
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try: rows.append({"Value": parts[0], "L2": float(parts[1]), "Count": int(parts[2])})
                except: pass
        if rows: df = pd.DataFrame(rows)

if df is not None:
    die_standard, die_oversized = {}, {} 
    total_trim_per_bar = 2 * end_trim_input
    usable_max_std = max_stock_input - total_trim_per_bar
    
    for _, row in df.iterrows():
        die, length, count = str(row['Value']), row['L2'], int(row['Count'])
        if length > usable_max_length if 'usable_max_length' in locals() else usable_max_std:
            if die not in die_oversized: die_oversized[die] = []
            die_oversized[die].extend([length] * count)
        else:
            if die not in die_standard: die_standard[die] = []
            die_standard[die].extend([length] * count)
        
    results_summary = []
    detailed_bins = {}
    
    if 'run_active' not in st.session_state: st.session_state['run_active'] = False

    if run_mode == "Process All Dies":
        if st.button("Run Process for All Dies"): st.session_state['run_active'] = True
    else:
        selected_die = st.selectbox("Select a Die Profile:", list(die_standard.keys()))
        if st.button(f"Run Process for: {selected_die}"): st.session_state['run_active'] = True

    if st.session_state['run_active']:
        targets = die_standard.keys() if run_mode == "Process All Dies" else [selected_die]
        
        # 1. Standard Results
        for die in targets:
            if die not in die_standard: continue
            lengths = die_standard[die]
            low = max(min_stock_input, math.ceil(max(lengths) + total_trim_per_bar))
            best_sl, best_bins = None, []
            for sl in range(int(low), int(max_stock_input) + 1):
                res = calculate_mullion_optimization(lengths, sl, total_trim_per_bar, cut_thickness_input)
                if best_sl is None or len(res) < len(best_bins):
                    best_sl, best_bins = sl, res
            
            total_req = sum(lengths)
            results_summary.append({
                "Die": die, "Stock": best_sl, "Bars": len(best_bins), 
                "Scrap (in)": round((len(best_bins)*best_sl) - total_req, 2),
                "Waste %": f"{(((len(best_bins)*best_sl) - total_req) / (len(best_bins)*best_sl))*100:.2f}%"
            })
            detailed_bins[die] = {"sl": best_sl, "bins": best_bins}

        if results_summary:
            st.subheader("📋 Optimization Summary")
            st.table(pd.DataFrame(results_summary))
            if st.checkbox("🔍 Show Visual Bar Layouts", value=True):
                for d, data in detailed_bins.items():
                    with st.expander(f"Layout for {d}"):
                        for i, b in enumerate(data['bins'], 1):
                            st.write(f"Bar {i}: {b} | Used: {sum(b):.2f}\"")
                            st.progress(min((sum(b)+total_trim_per_bar)/data['sl'], 1.0))

        # 2. FIXED: Oversized Optimization (Consolidated Order Lengths)
        if die_oversized:
            st.markdown("---")
            st.warning("⚠️ Oversized Optimization (Consolidated Orders)")
            over_rows = []
            for die, lengths in die_oversized.items():
                # Step 1: Find ONE best custom stock length for the entire die profile
                # We base it on the largest piece plus trims
                consolidated_sl = math.ceil(max(lengths) + total_trim_per_bar)
                
                # Step 2: Fit all pieces into that single stock length
                res_bins = calculate_mullion_optimization(lengths, consolidated_sl, total_trim_per_bar, cut_thickness_input)
                
                over_rows.append({
                    "Die Name": f"{die}-N",
                    "Required Cuts": len(lengths),
                    "Single Order Length (in)": consolidated_sl,
                    "Total Bars to Order": len(res_bins)
                })
                
                with st.expander(f"Layout for {die}-N (Ordering all at {consolidated_sl}\")"):
                    for idx, b in enumerate(res_bins, 1):
                        st.write(f"Custom Bar {idx}: {b}")
                        st.progress(min((sum(b)+total_trim_per_bar)/consolidated_sl, 1.0))
            
            st.table(pd.DataFrame(over_rows))
