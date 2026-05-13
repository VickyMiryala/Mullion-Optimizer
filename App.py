import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Full optimization for both standard and custom oversized profiles.")

# --- Sidebar: Configuration Parameters ---
st.sidebar.header("⚙️ Configuration Parameters")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Side (in)", value=2.0, step=0.125)
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

run_mode = st.sidebar.radio("Select Processing Mode", ("Process All Dies", "Process Die Individually"))
input_method = st.radio("Select Input Method", ("Upload CSV", "Paste Data Manually"))

# --- Core Logic Functions ---
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
    st.info("Format: Value, L2, Count")
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
    with st.expander("📊 Data Preview", expanded=True):
        st.dataframe(df, use_container_width=True)
        
    die_standard = {}
    die_oversized = {} 
    total_trim_per_bar = 2 * end_trim_input
    usable_max_std = max_stock_input - total_trim_per_bar
    
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
    
    if 'run_all' not in st.session_state: st.session_state['run_all'] = False
    if 'run_single' not in st.session_state: st.session_state['run_single'] = False

    if run_mode == "Process All Dies":
        if st.button("Run Process for All Dies"):
            st.session_state['run_all'] = True
            st.session_state['run_single'] = False
    else:
        selected_die = st.selectbox("Select a Die Profile:", list(die_standard.keys()) if die_standard else [])
        if st.button(f"Run Process for: {selected_die}"):
            st.session_state['run_single'] = True
            st.session_state['run_all'] = False

    if (st.session_state['run_all'] and run_mode == "Process All Dies") or \
       (st.session_state['run_single'] and run_mode == "Process Die Individually"):
        
        targets = die_standard.keys() if run_mode == "Process All Dies" else [selected_die]
        
        with st.status("Calculating...", expanded=True) as status:
            for die in targets:
                if die not in die_standard: continue
                lengths = die_standard[die]
                max_req = max(lengths)
                low = max(min_stock_input, math.ceil(max_req) + total_trim_per_bar)
                valid_stocks = [s for s in range(int(low), int(max_stock_input) + 1)]
                
                best_sl, best_bins = None, []
                for sl in valid_stocks:
                    bins = calculate_mullion_optimization(lengths, sl, total_trim_per_bar, cut_thickness_input)
                    if best_sl is None or len(bins) < len(best_bins):
                        best_sl, best_bins = sl, bins
                
                total_req = sum(lengths)
                results_summary.append({
                    "Die": die, "Pieces": len(lengths), "Stock": best_sl, "Bars": len(best_bins),
                    "Req (in)": round(total_req, 2), "Scrap (in)": round((len(best_bins)*best_sl) - total_req, 2),
                    "Waste %": f"{(((len(best_bins)*best_sl) - total_req) / (len(best_bins)*best_sl))*100:.2f}%"
                })
                detailed_bins[die] = {"stock_length": best_sl, "bins": best_bins}
            status.update(label="Complete!", state="complete", expanded=False)

    if results_summary:
        st.markdown("---")
        st.subheader("📋 Optimization Summary")
        st.table(pd.DataFrame(results_summary))
        
        if st.checkbox("🔍 See Detailed Bar Layouts", value=True):
            tabs = st.tabs(list(detailed_bins.keys()))
            for i, die in enumerate(detailed_bins.keys()):
                with tabs[i]:
                    info = detailed_bins[die]
                    for idx, bar in enumerate(info['bins'], 1):
                        sum_bar = sum(bar)
                        total_kerf = (len(bar) - 1) * cut_thickness_input
                        rem = info['stock_length'] - total_trim_per_bar - sum_bar - total_kerf
                        with st.expander(f"Bar {idx} | Used: {sum_bar + total_kerf:.2f}\" | Scrap: {rem:.2f}\""):
                            st.progress(min((sum_bar + total_kerf + total_trim_per_bar)/info['stock_length'], 1.0))
                            st.write(f"Cuts: {bar}")

    # --- NEW: Optimized Oversized Logic ---
    if die_oversized:
        st.markdown("---")
        st.warning("⚠️ Oversized Optimization (Custom Cuts)")
        over_summary = []
        for die, lengths in die_oversized.items():
            # Optimization for oversized: we find the best custom stock length to fit these items
            max_p = max(lengths)
            custom_sl = math.ceil(max_p + total_trim_per_bar)
            res_bins = calculate_mullion_optimization(lengths, custom_sl, total_trim_per_bar, cut_thickness_input)
            
            over_summary.append({
                "Die Name": f"{die}-N",
                "Total Pieces": len(lengths),
                "Recommended Custom Stock (in)": custom_sl,
                "Total Bars": len(res_bins),
                "Total Required (in)": sum(lengths)
            })
            
            with st.expander(f"Layout for {die}-N"):
                for idx, b in enumerate(res_bins, 1):
                    st.write(f"Custom Bar {idx}: {b} (Total Cut length: {sum(b)}\")")
        st.table(pd.DataFrame(over_summary))
