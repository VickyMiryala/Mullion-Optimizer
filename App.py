import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Full optimization with original expander layouts and detailed wastage metrics.")

# --- Sidebar: Configuration Parameters ---
st.sidebar.header("⚙️ Configuration Parameters")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Side (in)", value=2.0, step=0.125, 
                                          help="Deducted from BOTH ends of the bar.")
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

# Selection of Operating Mode
run_mode = st.sidebar.radio("Select Processing Mode", ("Process All Dies", "Process Die Individually"))

# Input Method Choice
input_method = st.radio("Select Input Method", ("Upload CSV", "Paste Data Manually"))

df = None
if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your TEST.csv file", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
else:
    st.info("### Instructions\nEnter: Value, L2, Count. One row per line.")
    pasted_data = st.text_area("Data Inputs", "UA-1486, 140.5, 5\nUA-525, 140.5, 5", height=200)
    if pasted_data:
        lines = [x.strip() for x in pasted_data.strip().split("\n") if x.strip()]
        rows = []
        for line in lines:
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try: rows.append({"Value": parts[0], "L2": float(parts[1]), "Count": int(parts[2])})
                except ValueError: pass
        if rows: df = pd.DataFrame(rows)

if df is not None:
    with st.expander("📊 Data Preview", expanded=True):
        st.dataframe(df, use_container_width=True)
        
    die_lengths = {}
    oversized_dict = {} 
    total_trim_per_bar = 2 * end_trim_input
    
    for index, row in df.iterrows():
        die, length, count = row['Value'], row['L2'], row['Count']
        if pd.isna(die): continue
            
        usable_max_length = max_stock_input - total_trim_per_bar
        if length > usable_max_length:
            key = (die, length)
            oversized_dict[key] = oversized_dict.get(key, 0) + count
            continue
            
        if die not in die_lengths: die_lengths[die] = []
        die_lengths[die].extend([length] * count)
        
    results_summary = []
    detailed_bins = {}
    
    if 'run_all' not in st.session_state: st.session_state['run_all'] = False
    if 'run_single' not in st.session_state: st.session_state['run_single'] = False

    def calculate_mullion_optimization(req_lengths, stock_length):
        sorted_lengths = sorted(req_lengths, reverse=True)
        bins = []
        usable_stock = stock_length - total_trim_per_bar
        for length in sorted_lengths:
            placed = False
            for b in bins:
                potential_space = sum(b) + length + (len(b) * cut_thickness_input)
                if potential_space <= usable_stock:
                    b.append(length)
                    placed = True
                    break
            if not placed: bins.append([length])
        return bins

    if run_mode == "Process All Dies":
        if st.button("Run Process for All Dies"):
            st.session_state['run_all'] = True
            st.session_state['run_single'] = False
    else:
        selected_die = st.selectbox("Select a Die Profile:", list(die_lengths.keys()) if die_lengths else [])
        if st.button(f"Run Process for: {selected_die}"):
            st.session_state['run_single'] = True
            st.session_state['run_all'] = False

    if (st.session_state['run_all'] and run_mode == "Process All Dies") or \
       (st.session_state['run_single'] and run_mode == "Process Die Individually"):
        
        targets = die_lengths.keys() if run_mode == "Process All Dies" else [selected_die]
        
        with st.status("Calculating...", expanded=True) as status:
            for die in targets:
                if die not in die_lengths: continue
                lengths = die_lengths[die]
                max_req = max(lengths)
                low = max(min_stock_input, math.ceil(max_req) + total_trim_per_bar)
                valid_stocks = [s for s in range(int(low), int(max_stock_input) + 1)]
                
                best_sl, best_bins = None, []
                for sl in valid_stocks:
                    bins = calculate_mullion_optimization(lengths, sl)
                    if best_sl is None or len(bins) < len(best_bins):
                        best_sl, best_bins = sl, bins
                
                total_req_len = sum(lengths)
                tot_allocated = len(best_bins) * best_sl
                scrap_val = tot_allocated - total_req_len
                waste_pct = (scrap_val / tot_allocated) * 100 if tot_allocated > 0 else 0
                
                results_summary.append({
                    "Die": die, "Pieces": len(lengths),
                    "Stock Length": best_sl, "Bars": len(best_bins),
                    "Required (in)": round(total_req_len, 2), "Scrap (in)": round(scrap_val, 2),
                    "Waste %": f"{waste_pct:.2f}%"
                })
                detailed_bins[die] = {"stock_length": best_sl, "bins": best_bins}
            status.update(label="Complete!", state="complete", expanded=False)

    if results_summary:
        st.markdown("---")
        st.subheader("📋 Optimization Summary")
        st.table(pd.DataFrame(results_summary))
        
        show_details = st.checkbox("🔍 See Detailed Bar Layouts", value=True)
        if show_details:
            tabs = st.tabs(list(detailed_bins.keys()))
            for i, die in enumerate(detailed_bins.keys()):
                with tabs[i]:
                    info = detailed_bins[die]
                    st.write(f"### Die Profile: {die}")
                    st.write(f"**Stock Selection:** {info['stock_length']}\" | **Required Bars:** {len(info['bins'])}")
                    
                    for idx, bar in enumerate(info['bins'], 1):
                        sum_bar = sum(bar)
                        total_kerf = (len(bar) - 1) * cut_thickness_input
                        used_with_kerf = sum_bar + total_kerf
                        rem = info['stock_length'] - total_trim_per_bar - used_with_kerf
                        
                        # The Layout you requested: Expander with Bar info + Progress + Metrics
                        with st.expander(f"Bar {idx} | Used: {used_with_kerf:.2f}\" | Scrap: {rem:.2f}\"", expanded=(idx <= 3)):
                            usage_ratio = (used_with_kerf + total_trim_per_bar) / info['stock_length']
                            st.progress(min(usage_ratio, 1.0))
                            
                            st.markdown("**Cut Breakdown:**")
                            cols = st.columns(min(len(bar), 6))
                            for c_idx, cut in enumerate(bar):
                                with cols[c_idx % 6]:
                                    st.metric(label=f"Cut {c_idx+1}", value=f"{cut}\"")
                                    
                            st.write(f"**Raw Cut List:** {bar}")
                            st.write(f"**Trims & Kerf:** {total_trim_per_bar}\" trim + {total_kerf:.3f}\" kerf loss")

        if oversized_dict:
            st.markdown("---")
            st.warning("⚠️ Oversized Pieces (Grouped)")
            over_recs = [{"Die Name": f"{d}-N", "Length": l, "Qty": c, "Min Order": l + total_trim_per_bar} 
                        for (d, l), c in oversized_dict.items()]
            st.table(pd.DataFrame(over_recs))
