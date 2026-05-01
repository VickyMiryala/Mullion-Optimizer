import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Advanced Mullion Die Optimization & Procurement App")
st.write("Process custom stock lengths, end trims, and cut lengths with precise background execution and manual die-by-die selection.")

# Sidebar Inputs for Conditions
st.sidebar.header("⚙️ Configuration Parameters")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Bar (in)", value=2.0, step=0.125)
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

# Selection Mode
run_mode = st.sidebar.radio("Select Processing Mode", ("Process All Dies", "Process Dies Individually"))

# Input Choice
input_method = st.radio("Select Input Method", ("Upload CSV", "Paste Data Manually"))

df = None

if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your TEST.csv file", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
else:
    st.info("### Instructions\nEnter your data below, separated by commas (Value, L2, Count). One row per line.")
    pasted_data = st.text_area("Data Inputs", "UA-1486, 140.5, 5\nUA-525, 140.5, 5\nUA-524, 140.5, 5", height=200)
    
    if pasted_data:
        lines = [x.strip() for x in pasted_data.strip().split("\n") if x.strip()]
        rows = []
        for line in lines:
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try:
                    rows.append({
                        "Value": parts[0],
                        "L2": float(parts[1]),
                        "Count": int(parts[2])
                    })
                except ValueError:
                    pass
        if rows:
            df = pd.DataFrame(rows)

if df is not None:
    # 1. Data Preview Section
    st.subheader("📊 Data Preview")
    st.dataframe(df, use_container_width=True)
    
    # Process the data
    die_lengths = {}
    oversized_lengths = []
    
    for index, row in df.iterrows():
        die = row['Value']
        length = row['L2']
        count = row['Count']
        
        if pd.isna(die):
            continue
            
        usable_max_length = max_stock_input - end_trim_input
        if length > usable_max_length:
            for _ in range(count):
                oversized_lengths.append({"Die": f"{die} - N", "Length": length})
            continue
            
        if die not in die_lengths:
            die_lengths[die] = []
        die_lengths[die].extend([length] * count)
        
    results_summary = []
    detailed_bins = {}
    
    # Check execution states
    if 'run_optimization' not in st.session_state:
        st.session_state['run_optimization'] = False
        
    # Run Modes
    if run_mode == "Process All Dies":
        if st.button("Run Process for All Dies"):
            st.session_state['run_optimization'] = True
        
        if st.session_state['run_optimization']:
            with st.status("Optimizing all dies at once...", expanded=True) as status:
                st.write("Validating parameters and lengths...")
                
                for die, lengths in die_lengths.items():
                    max_req = max(lengths)
                    min_allowed_stock = math.ceil(max_req) + end_trim_input
                    calc_min_stock = max(min_stock_input, min_allowed_stock)
                    valid_stocks = [s for s in range(int(calc_min_stock), int(max_stock_input) + 1)]
                    
                    if not valid_stocks:
                        for l in lengths:
                            oversized_lengths.append({"Die": f"{die} - N", "Length": l})
                        continue
                        
                    def calculate_mullion_optimization(req_lengths, stock_length):
                        sorted_lengths = sorted(req_lengths, reverse=True)
                        bins = []
                        usable_stock = stock_length - end_trim_input
                        
                        for length in sorted_lengths:
                            placed = False
                            for b in bins:
                                potential_items = b + [length]
                                space_used = sum(potential_items) + (len(potential_items) - 1) * cut_thickness_input
                                if space_used <= usable_stock:
                                    b.append(length)
                                    placed = True
                                    break
                            if not placed:
                                bins.append([length])
                        return bins
                        
                    best_sl = None
                    best_bins = []
                    for sl in valid_stocks:
                        bins = calculate_mullion_optimization(lengths, sl)
                        if best_sl is None or len(bins) < len(best_bins):
                            best_sl = sl
                            best_bins = bins
                            
                    total_required = sum(lengths)
                    total_allocated = len(best_bins) * best_sl
                    scrap = total_allocated - total_required
                    waste_pct = (scrap / total_allocated) * 100 if total_allocated > 0 else 0
                    
                    results_summary.append({
                        "Die": die,
                        "Total Pieces": len(lengths),
                        "Required Length (in)": total_required,
                        "Optimal Stock Length (in)": best_sl,
                        "Bars Required": len(best_bins),
                        "Scrap (in)": round(scrap, 2),
                        "Waste %": round(waste_pct, 2)
                    })
                    
                    detailed_bins[die] = {
                        "stock_length": best_sl,
                        "bins": best_bins,
                        "waste_pct": waste_pct
                    }
                status.update(label="Optimization Processing Complete!", state="complete", expanded=False)
                
    else:
        # Process Dies Individually Mode
        selected_die = st.selectbox("Select a Die Profile to Run:", list(die_lengths.keys()))
        if st.button(f"Run Process for: {selected_die}"):
            st.session_state['run_optimization'] = True
            
        if st.session_state['run_optimization'] and selected_die:
            with st.status(f"Processing die {selected_die}...", expanded=True) as status:
                lengths = die_lengths[selected_die]
                max_req = max(lengths)
                min_allowed_stock = math.ceil(max_req) + end_trim_input
                calc_min_stock = max(min_stock_input, min_allowed_stock)
                valid_stocks = [s for s in range(int(calc_min_stock), int(max_stock_input) + 1)]
                
                def calculate_mullion_optimization(req_lengths, stock_length):
                    sorted_lengths = sorted(req_lengths, reverse=True)
                    bins = []
                    usable_stock = stock_length - end_trim_input
                    
                    for length in sorted_lengths:
                        placed = False
                        for b in bins:
                            potential_items = b + [length]
                            space_used = sum(potential_items) + (len(potential_items) - 1) * cut_thickness_input
                            if space_used <= usable_stock:
                                b.append(length)
                                placed = True
                                break
                        if not placed:
                            bins.append([length])
                    return bins
                    
                best_sl = None
                best_bins = []
                for sl in valid_stocks:
                    bins = calculate_mullion_optimization(lengths, sl)
                    if best_sl is None or len(bins) < len(best_bins):
                        best_sl = sl
                        best_bins = bins
                        
                total_required = sum(lengths)
                total_allocated = len(best_bins) * best_sl
                scrap = total_allocated - total_required
                waste_pct = (scrap / total_allocated) * 100 if total_allocated > 0 else 0
                
                results_summary.append({
                    "Die": selected_die,
                    "Total Pieces": len(lengths),
                    "Required Length (in)": total_required,
                    "Optimal Stock Length (in)": best_sl,
                    "Bars Required": len(best_bins),
                    "Scrap (in)": round(scrap, 2),
                    "Waste %": round(waste_pct, 2)
                })
                
                detailed_bins[selected_die] = {
                    "stock_length": best_sl,
                    "bins": best_bins,
                    "waste_pct": waste_pct
                }
                status.update(label=f"Done processing {selected_die}!", state="complete", expanded=False)

    # 3. Render Output Table and Charts
    if results_summary:
        results_df = pd.DataFrame(results_summary)
        st.markdown("---")
        st.subheader("📋 Optimization Summary")
        st.dataframe(results_df, use_container_width=True)
        
        csv_summary = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Summary CSV",
            data=csv_summary,
            file_name="mullion_die_summary.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        show_details = st.checkbox("See / Hide Detailed Bar Layouts", value=True)
        
        if show_details:
            st.subheader("🔍 Detailed Layouts by Profile")
            tabs = st.tabs(list(detailed_bins.keys()))
            
            for i, die in enumerate(detailed_bins.keys()):
                with tabs[i]:
                    die_info = detailed_bins[die]
                    st.write(f"### Die: {die}")
                    st.write(f"**Optimal Stock Length:** {die_info['stock_length']} in | "
                             f"**Total Bars Required:** {len(die_info['bins'])}")
                    
                    for idx, bar in enumerate(die_info['bins'], 1):
                        sum_bar = sum(bar)
                        total_cuts_kerf = (len(bar) - 1) * cut_thickness_input
                        total_used_with_kerf = sum_bar + total_cuts_kerf
                        remainder = die_info['stock_length'] - end_trim_input - total_used_with_kerf
                        
                        with st.expander(f"Bar {idx} | Usable Length Used: {total_used_with_kerf:.2f} in | Remainder Scrap: {remainder:.2f} in", expanded=(idx <= 3)):
                            st.markdown("#### Visual Bar Allocation")
                            usage_ratio = total_used_with_kerf / die_info['stock_length']
                            st.progress(min(usage_ratio, 1.0), text=f"Bar Used: {total_used_with_kerf:.2f} in")
                            
                            st.markdown("**Cut Details:**")
                            cols = st.columns(min(len(bar), 6))
                            for c_idx, cut in enumerate(bar):
                                with cols[c_idx % 6]:
                                    st.metric(label=f"Cut {c_idx+1}", value=f"{cut} in")
                                    
                            st.write(f"**Original Cuts on Bar:** {bar}")
                            st.write(f"**End Trim Allowance:** {end_trim_input} in")
                            st.write(f"**Kerf Loss:** {total_cuts_kerf:.4f} in")
                            st.write(f"**Remaining Scrap After Cuts:** {remainder:.2f} in")
                            
        # Oversized Partitions
        if oversized_lengths:
            st.markdown("---")
            st.warning("⚠️ Oversized / Unmatched Pieces")
            st.dataframe(pd.DataFrame(oversized_lengths), use_container_width=True)
