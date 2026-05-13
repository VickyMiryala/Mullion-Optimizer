import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Optimized layout with consolidated custom stock lengths and reliable processing.")

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
        if not placed:
            bins.append([length])
    return bins

# --- Data Input Handling ---
df = None
if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your TEST.csv file", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
else:
    st.info("Format: Value, L2, Count")
    pasted_data = st.text_area("Data Inputs", height=150)
    if pasted_data:
        rows = []
        for line in pasted_data.strip().split("\n"):
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try:
                    rows.append({"Value": parts[0].strip(), "L2": float(parts[1]), "Count": int(parts[2])})
                except:
                    pass
        if rows:
            df = pd.DataFrame(rows)

if df is not None:
    die_standard = {}
    die_oversized = {} 
    total_trim_per_bar = 2 * end_trim_input
    usable_max_std = max_stock_input - total_trim_per_bar
    
    # Pre-sorting data into Standard and Oversized buckets
    for _, row in df.iterrows():
        die, length, count = str(row['Value']), row['L2'], int(row['Count'])
        if length > usable_max_std:
            if die not in die_oversized: die_oversized[die] = []
            die_oversized[die].extend([length] * count)
        else:
            if die not in die_standard: die_standard[die] = []
            die_standard[die].extend([length] * count)
        
    results_summary = []
    detailed_bins = {}
    
    # Handle Session State for buttons
    if 'run_active' not in st.session_state:
        st.session_state['run_active'] = False

    if run_mode == "Process All Dies":
        if st.button("Run Process for All Dies"):
            st.session_state['run_active'] = True
    else:
        selected_die = st.selectbox("Select a Die Profile:", list(die_standard.keys()) if die_standard else ["No Standard Data"])
        if st.button(f"Run Process for: {selected_die}"):
            st.session_state['run_active'] = True

    # --- Calculation Execution ---
    if st.session_state['run_active']:
        targets = die_standard.keys() if run_mode == "Process All Dies" else [selected_die]
        
        for die in targets:
            if die not in die_standard: continue
            lengths = die_standard[die]
            
            # Find the best integer stock length between Min and Max
            max_p = max(lengths)
            low_bound = max(min_stock_input, math.ceil(max_p + total_trim_per_bar))
            
            best_sl, best_bins = None, []
            for sl in range(int(low_bound), int(max_stock_input) + 1):
                res = calculate_mullion_optimization(lengths, sl, total_trim_per_bar, cut_thickness_input)
                if best_sl is None or len(res) < len(best_bins):
                    best_sl, best_bins = sl, res
            
            total_req = sum(lengths)
            tot_allocated = len(best_bins) * best_sl
            scrap_val = tot_allocated - total_req
            waste_pct = (scrap_val / tot_allocated) * 100 if tot_allocated > 0 else 0
            
            results_summary.append({
                "Die": die, "Stock": best_sl, "Bars": len(best_bins), 
                "Required (in)": round(total_req, 2), "Scrap (in)": round(scrap_val, 2),
                "Waste %": f"{waste_pct:.2f}%"
            })
            detailed_bins[die] = {"sl": best_sl, "bins": best_bins}

        # --- Display Results ---
        if results_summary:
            st.subheader("📋 Optimization Summary")
            st.table(pd.DataFrame(results_summary))
            
            if st.checkbox("🔍 Show Visual Bar Layouts", value=True):
                for d, data in detailed_bins.items():
                    with st.expander(f"Layout for {d} (Stock: {data['sl']}\")"):
                        for i, b in enumerate(data['bins'], 1):
                            used_cuts = sum(b)
                            total_kerf = (len(b) - 1) * cut_thickness_input
                            current_total = used_cuts + total_kerf + total_trim_per_bar
                            rem = data['sl'] - current_total
                            
                            st.write(f"**Bar {i}** | Used: {used_cuts + total_kerf:.2f}\" | Scrap: {rem:.2f}\"")
                            st.progress(min(current_total / data['sl'], 1.0))
                            
                            m_cols = st.columns(min(len(b), 6))
                            for c_idx, cut in enumerate(b):
                                with m_cols[c_idx % 6]:
                                    st.metric(f"Cut {c_idx+1}", f"{cut}\"")

        # --- Oversized Optimization ---
        if die_oversized:
            st.markdown("---")
            st.subheader("📏 Oversized Optimization (Consolidated Custom Stock)")
            over_rows = []
            for die, lengths in die_oversized.items():
                # Base order length on the largest requirement + trims
                consolidated_sl = math.ceil(max(lengths) + total_trim_per_bar)
                res_bins = calculate_mullion_optimization(lengths, consolidated_sl, total_trim_per_bar, cut_thickness_input)
                
                over_rows.append({
                    "Die Name": f"{die}-N",
                    "Required Pieces": len(lengths),
                    "Single Order Length (in)": consolidated_sl,
                    "Total Bars": len(res_bins)
                })
                
                with st.expander(f"Layout for {die}-N (Order all at {consolidated_sl}\")"):
                    for idx, b in enumerate(res_bins, 1):
                        st.write(f"Custom Bar {idx}: {b}")
                        st.progress(min((sum(b) + total_trim_per_bar + (len(b)-1)*cut_thickness_input) / consolidated_sl, 1.0))
            
            st.table(pd.DataFrame(over_rows))
