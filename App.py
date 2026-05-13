import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Full visual optimization for standard (140-260\") and custom oversized profiles.")

# Sidebar Configuration
st.sidebar.header("⚙️ Settings")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Side (in)", value=2.0, step=0.125, help="Applied to BOTH ends.")
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

run_mode = st.sidebar.radio("Processing Mode", ("All Dies", "Individual Die"))
input_method = st.radio("Input Method", ("Upload CSV", "Manual Paste"))

df = None
if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload TEST.csv", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
else:
    st.info("### Instructions\nEnter: Value, L2, Count. One row per line.")
    pasted_data = st.text_area("Paste Data", "UA-1486, 140.5, 5\nUA-2000, 275.0, 4", height=150)
    if pasted_data:
        rows = []
        for line in pasted_data.strip().split("\n"):
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try:
                    rows.append({"Value": parts[0], "L2": float(parts[1]), "Count": int(parts[2])})
                except ValueError: pass
        if rows: df = pd.DataFrame(rows)

def bin_pack(lengths, stock_length, trim, kerf):
    sorted_len = sorted(lengths, reverse=True)
    bins = []
    usable = stock_length - (2 * trim)
    for l in sorted_len:
        fit = False
        for b in bins:
            # Space check: sum of cuts + total kerfs between cuts
            if sum(b) + l + (len(b) * kerf) <= usable:
                b.append(l)
                fit = True
                break
        if not fit: bins.append([l])
    return bins

if df is not None:
    with st.expander("📊 Data Preview", expanded=True):
        st.dataframe(df, use_container_width=True)
    
    total_trim = 2 * end_trim_input
    usable_max_std = max_stock_input - total_trim

    # Separation logic
    standard_data = {}
    oversized_data = {}

    for _, row in df.iterrows():
        die, length, count = str(row['Value']), row['L2'], int(row['Count'])
        if length > usable_max_std:
            if die not in oversized_data: oversized_data[die] = []
            oversized_data[die].extend([length] * count)
        else:
            if die not in standard_data: standard_data[die] = []
            standard_data[die].extend([length] * count)

    # Execution Buttons
    if run_mode == "All Dies":
        start_button = st.button("🚀 Run Full Optimization")
    else:
        selected_die = st.selectbox("Select Die Profile", list(standard_data.keys()))
        start_button = st.button(f"🚀 Optimize {selected_die} Only")

    if start_button:
        # Standard Optimization Output
        st.subheader("📋 Standard Stock Results (140-260\")")
        targets = standard_data.keys() if run_mode == "All Dies" else [selected_die]
        
        for die in targets:
            if die not in standard_data: continue
            lengths = standard_data[die]
            
            low = max(min_stock_input, math.ceil(max(lengths) + total_trim))
            best_sl, best_bins = None, []
            
            for sl in range(int(low), int(max_stock_input) + 1):
                res = bin_pack(lengths, sl, end_trim_input, cut_thickness_input)
                if best_sl is None or len(res) < len(best_bins):
                    best_sl, best_bins = sl, res
            
            with st.expander(f"Die: {die} | Stock: {best_sl}\" | Bars: {len(best_bins)}", expanded=True):
                for i, bar in enumerate(best_bins, 1):
                    used_cuts = sum(bar)
                    total_kerf = (len(bar)-1) * cut_thickness_input
                    rem_scrap = best_sl - total_trim - used_cuts - total_kerf
                    
                    # Proportional HTML Visualizer
                    html = f'<div style="display:flex; border:1px solid #333; height:35px; width:100%; background:#eee; margin-bottom:10px; border-radius:5px; overflow:hidden;">'
                    html += f'<div style="background:#6c757d; width:{(end_trim_input/best_sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div>'
                    for l in bar:
                        html += f'<div style="background:#2b7a78; border-right:1px solid #fff; width:{(l/best_sl)*100}%; color:white; font-size:11px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{l}</div>'
                    if total_kerf > 0:
                        html += f'<div style="background:#3aafa9; width:{(total_kerf/best_sl)*100}%;"></div>'
                    html += f'<div style="background:#fe4a49; width:{(rem_scrap/best_sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">{rem_scrap:.1f} Scrap</div>'
                    html += f'<div style="background:#6c757d; width:{(end_trim_input/best_sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div></div>'
                    st.markdown(html, unsafe_allow_html=True)

        # Oversized Optimization Output
        if oversized_data:
            st.markdown("---")
            st.subheader("📏 Oversized Optimization (Custom Orders)")
            for die, lengths in oversized_data.items():
                custom_sl = max(lengths) + total_trim
                res = bin_pack(lengths, custom_sl, end_trim_input, cut_thickness_input)
                
                with st.expander(f"Die: {die} - N | Custom Order: {custom_sl}\" | Total Bars: {len(res)}", expanded=True):
                    for idx, bar in enumerate(res, 1):
                        st.write(f"**Custom Bar {idx}:** Contains cuts {bar} | Recommended Order Length: **{custom_sl}\"**")
                        
                        # Same Visualizer for Oversized
                        rem_ov = custom_sl - total_trim - sum(bar) - ((len(bar)-1)*cut_thickness_input)
                        html_ov = f'<div style="display:flex; border:1px solid #333; height:30px; width:100%; background:#eee; margin-bottom:5px; border-radius:5px; overflow:hidden;">'
                        html_ov += f'<div style="background:#6c757d; width:{(end_trim_input/custom_sl)*100}%;"></div>'
                        for l in bar:
                            html_ov += f'<div style="background:#2b7a78; border-right:1px solid #fff; width:{(l/custom_sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">{l}</div>'
                        html_ov += f'<div style="background:#fe4a49; width:{(rem_ov/custom_sl)*100}%;"></div>'
                        html_ov += f'<div style="background:#6c757d; width:{(end_trim_input/custom_sl)*100}%;"></div></div>'
                        st.markdown(html_ov, unsafe_allow_html=True)
