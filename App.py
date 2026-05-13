import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Advanced Mullion Die Optimization & Procurement App")
st.write("Unified system for Standard (140-260\") and Custom Oversized Mullion Optimization.")

# --- Sidebar: Configuration Parameters ---
st.sidebar.header("⚙️ Configuration Parameters")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Bar (in)", value=2.0, step=0.125, 
                                          help="Deducted from BOTH ends of the bar (Total 4\" if set to 2\").")
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

# Sidebar: Processing Mode
run_mode = st.sidebar.radio("Select Processing Mode", ("Process All Dies", "Process Die Individually"))

# --- Main Section: Input Methods ---
input_method = st.radio("Select Input Method", ("Upload CSV", "Paste Data Manually"))

df = None
if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload your TEST.csv file", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
else:
    st.info("### Instructions\nEnter: Value, L2, Count. One row per line.")
    pasted_data = st.text_area("Pasted Data", "UA-1486, 140.5, 5\nUA-2000, 280.0, 2", height=150)
    if pasted_data:
        lines = [x.strip() for x in pasted_data.strip().split("\n") if x.strip()]
        rows = []
        for line in lines:
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try:
                    rows.append({"Value": parts[0], "L2": float(parts[1]), "Count": int(parts[2])})
                except ValueError: pass
        if rows: df = pd.DataFrame(rows)

if df is not None:
    with st.expander("📊 Data Preview", expanded=True):
        st.dataframe(df, use_container_width=True)
    
    # --- Logic: Data Sorting ---
    die_lengths = {}
    oversized_dict = {} 
    total_trim = 2 * end_trim_input
    usable_max = max_stock_input - total_trim

    for _, row in df.iterrows():
        die, length, count = str(row['Value']), row['L2'], int(row['Count'])
        if length > usable_max:
            key = (die, length)
            oversized_dict[key] = oversized_dict.get(key, 0) + count
        else:
            if die not in die_lengths: die_lengths[die] = []
            die_lengths[die].extend([length] * count)

    # --- Execution Logic ---
    if 'opt_done' not in st.session_state: st.session_state['opt_done'] = False

    if run_mode == "Process All Dies":
        if st.button("🚀 Run Full Optimization"):
            st.session_state['opt_done'] = True
    else:
        selected_die = st.selectbox("Select Die Profile:", list(die_lengths.keys()) if die_lengths else ["No Standard Sizes"])
        if st.button(f"🚀 Optimize {selected_die} Only"):
            st.session_state['opt_done'] = True

    if st.session_state['opt_done']:
        results_summary = []
        detailed_bins = {}
        target_dies = die_lengths.keys() if run_mode == "Process All Dies" else [selected_die]
        
        with st.status("Calculating best fit background...", expanded=True) as status:
            for die in target_dies:
                if die not in die_lengths: continue
                lengths = die_lengths[die]
                
                # Dynamic Search Range
                low_bound = max(min_stock_input, math.ceil(max(lengths) + total_trim))
                valid_range = range(int(low_bound), int(max_stock_input) + 1)
                
                best_sl, best_bins = None, []
                for sl in valid_range:
                    temp_bins = []
                    for l in sorted(lengths, reverse=True):
                        fit = False
                        for b in temp_bins:
                            if sum(b) + l + (len(b) * cut_thickness_input) <= (sl - total_trim):
                                b.append(l)
                                fit = True
                                break
                        if not fit: temp_bins.append([l])
                    
                    if best_sl is None or len(temp_bins) < len(best_bins):
                        best_sl, best_bins = sl, temp_bins

                if best_sl:
                    tot_req = sum(lengths)
                    tot_alloc = len(best_bins) * best_sl
                    waste = ((tot_alloc - tot_req) / tot_alloc) * 100
                    results_summary.append({"Die": die, "Stock Length": best_sl, "Bars": len(best_bins), "Waste %": round(waste, 2)})
                    detailed_bins[die] = {"sl": best_sl, "bins": best_bins}
            status.update(label="Process Complete!", state="complete")

        # --- Display Section: Standard Results ---
        if results_summary:
            st.subheader("📋 Optimization Summary (140-260\")")
            st.dataframe(pd.DataFrame(results_summary), use_container_width=True)
            
            show_layouts = st.checkbox("🔍 See Detailed Bar Layouts", value=False)
            if show_layouts:
                tabs = st.tabs(list(detailed_bins.keys()))
                for i, die in enumerate(detailed_bins.keys()):
                    with tabs[i]:
                        info = detailed_bins[die]
                        for idx, bar in enumerate(info['bins'], 1):
                            used_with_trim = sum(bar) + total_trim + ((len(bar)-1)*cut_thickness_input)
                            st.write(f"**Bar {idx}**: {bar} | Used Space: {sum(bar):.2f}\"")
                            st.progress(min(used_with_trim / info['sl'], 1.0))

        # --- Display Section: Oversized Optimization ---
        if oversized_dict:
            st.markdown("---")
            st.subheader("📏 Oversized Optimization (Custom Cut List)")
            st.warning("These pieces exceed standard stock limits. Ordered lengths include required trims.")
            
            over_data = []
            for (die, length), count in oversized_dict.items():
                rec_stock = length + total_trim
                over_data.append({
                    "Die Name": f"{die} - N",
                    "Required Cut (in)": length,
                    "Quantity": count,
                    "Order Length (in)": rec_stock,
                    "Total Footage (ft)": round((rec_stock * count) / 12, 2)
                })
            
            df_over = pd.DataFrame(over_data)
            st.table(df_over)
            
            csv_over = df_over.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Oversized Order List", csv_over, "oversized_list.csv", "text/csv")
