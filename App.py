import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Advanced optimization for standard (140-260\") and custom oversized profiles.")

# Sidebar Configuration Parameters
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
    st.info("### Instructions\nEnter your data below: (Value, L2, Count). One row per line.")
    pasted_data = st.text_area("Data Inputs", "UA-1486, 140.5, 5\nUA-525, 140.5, 5", height=200)
    
    if pasted_data:
        lines = [x.strip() for x in pasted_data.strip().split("\n") if x.strip()]
        rows = []
        for line in lines:
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try:
                    rows.append({"Value": parts[0], "L2": float(parts[1]), "Count": int(parts[2])})
                except ValueError: pass
        if rows:
            df = pd.DataFrame(rows)

if df is not None:
    with st.expander("See/Hide Data Preview", expanded=True):
        st.dataframe(df, use_container_width=True)
        
    die_lengths = {}
    oversized_dict = {} 
    
    for index, row in df.iterrows():
        die, length, count = row['Value'], row['L2'], row['Count']
        if pd.isna(die): continue
            
        usable_max_length = max_stock_input - (2 * end_trim_input)
        
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

    # Optimization Calculation Function
    def calculate_mullion_optimization(req_lengths, stock_length):
        sorted_lengths = sorted(req_lengths, reverse=True)
        bins = []
        usable_stock = stock_length - (2 * end_trim_input)
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

    # --- Mode 1: All Dies ---
    if run_mode == "Process All Dies":
        if st.button("Run Process for All Dies"):
            st.session_state['run_all'] = True
            st.session_state['run_single'] = False
            
        if st.session_state['run_all'] and die_lengths:
            with st.status("Optimizing all dies...", expanded=True) as status:
                for die, lengths in die_lengths.items():
                    max_req = max(lengths)
                    low = max(min_stock_input, math.ceil(max_req) + (2 * end_trim_input))
                    valid_stocks = [s for s in range(int(low), int(max_stock_input) + 1)]
                    
                    best_sl, best_bins = None, []
                    for sl in valid_stocks:
                        bins = calculate_mullion_optimization(lengths, sl)
                        if best_sl is None or len(bins) < len(best_bins):
                            best_sl, best_bins = sl, bins
                            
                    results_summary.append({
                        "Die": die, "Total Pieces": len(lengths),
                        "Optimal Stock (in)": best_sl, "Bars Required": len(best_bins),
                        "Waste %": round(((len(best_bins)*best_sl - sum(lengths))/(len(best_bins)*best_sl))*100, 2)
                    })
                    detailed_bins[die] = {"stock_length": best_sl, "bins": best_bins}
                status.update(label="Complete!", state="complete", expanded=False)

    # --- Mode 2: Individual Die ---
    else:
        selected_die = st.selectbox("Select Profile:", list(die_lengths.keys()) if die_lengths else [])
        if st.button(f"Run Process for: {selected_die}"):
            st.session_state['run_single'] = True
            st.session_state['run_all'] = False
            
        if st.session_state['run_single'] and selected_die:
            with st.status(f"Processing {selected_die}...", expanded=True) as status:
                lengths = die_lengths[selected_die]
                max_req = max(lengths)
                low = max(min_stock_input, math.ceil(max_req) + (2 * end_trim_input))
                valid_stocks = [s for s in range(int(low), int(max_stock_input) + 1)]
                
                best_sl, best_bins = None, []
                for sl in valid_stocks:
                    bins = calculate_mullion_optimization(lengths, sl)
                    if best_sl is None or len(bins) < len(best_bins):
                        best_sl, best_bins = sl, bins
                
                results_summary.append({
                    "Die": selected_die, "Total Pieces": len(lengths),
                    "Optimal Stock (in)": best_sl, "Bars Required": len(best_bins),
                    "Waste %": round(((len(best_bins)*best_sl - sum(lengths))/(len(best_bins)*best_sl))*100, 2)
                })
                detailed_bins[selected_die] = {"stock_length": best_sl, "bins": best_bins}
                status.update(label="Complete!", state="complete", expanded=False)

    # --- Output Render ---
    if results_summary:
        st.markdown("---")
        st.subheader("📋 Optimization Summary")
        st.dataframe(pd.DataFrame(results_summary), use_container_width=True)
        
        show_details = st.checkbox("See / Hide Colorful Bar Layouts", value=False)
        if show_details:
            tabs = st.tabs(list(detailed_bins.keys()))
            for i, die in enumerate(detailed_bins.keys()):
                with tabs[i]:
                    info = detailed_bins[die]
                    sl = info['stock_length']
                    for idx, bar in enumerate(info['bins'], 1):
                        sum_bar = sum(bar)
                        total_kerf = (len(bar) - 1) * cut_thickness_input
                        rem = sl - (2 * end_trim_input) - sum_bar - total_kerf
                        
                        # Colorful Bar Visualizer
                        html = f'<div style="display:flex; border:1px solid #333; height:35px; width:100%; background:#eee; margin-bottom:10px; border-radius:5px; overflow:hidden;">'
                        html += f'<div style="background:#6c757d; width:{(end_trim_input/sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div>'
                        for l in bar:
                            html += f'<div style="background:#2b7a78; border-right:1px solid #fff; width:{(l/sl)*100}%; color:white; font-size:11px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{l}</div>'
                        if total_kerf > 0:
                            html += f'<div style="background:#3aafa9; width:{(total_kerf/sl)*100}%;"></div>'
                        html += f'<div style="background:#fe4a49; width:{(rem/sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">{rem:.1f} Scrap</div>'
                        html += f'<div style="background:#6c757d; width:{(end_trim_input/sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div></div>'
                        st.markdown(html, unsafe_allow_html=True)
                        st.write(f"**Bar {idx}**: Cuts {bar} | Remaining Scrap: {rem:.2f} in")

        if oversized_dict:
            st.markdown("---")
            st.warning("⚠️ Oversized Pieces (Grouped)")
            over_recs = [{"Die": f"{d}-N", "Length (in)": l, "Count": c} for (d, l), c in oversized_dict.items()]
            st.table(pd.DataFrame(over_recs))
