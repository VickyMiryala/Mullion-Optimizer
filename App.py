import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Fast, cached optimization for standard and oversized profiles.")

# --- Sidebar: Settings ---
st.sidebar.header("⚙️ Settings")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Side (in)", value=2.0, step=0.125)
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

run_mode = st.sidebar.radio("Processing Mode", ("All Dies", "Individual Die"))
input_method = st.radio("Input Method", ("Upload CSV", "Manual Paste"))

# --- Core Optimization Engine (Cached for Speed) ---
@st.cache_data
def optimize_die(lengths, min_stock, max_stock, trim, kerf):
    total_trim = 2 * trim
    max_p = max(lengths)
    low = max(min_stock, math.ceil(max_p + total_trim))
    
    best_sl, best_bins = None, []
    
    for sl in range(int(low), int(max_stock) + 1):
        # Bin Packing Algorithm
        current_bins = []
        for l in sorted(lengths, reverse=True):
            fit = False
            for b in current_bins:
                if sum(b) + l + (len(b) * kerf) <= (sl - total_trim):
                    b.append(l)
                    fit = True
                    break
            if not fit: current_bins.append([l])
        
        if best_sl is None or len(current_bins) < len(best_bins):
            best_sl, best_bins = sl, current_bins
            
    return {"sl": best_sl, "bins": best_bins}

# --- Data Loading ---
df = None
if input_method == "Upload CSV":
    uploaded_file = st.file_uploader("Upload TEST.csv", type=["csv"])
    if uploaded_file: df = pd.read_csv(uploaded_file)
else:
    pasted_data = st.text_area("Paste Data (Value, L2, Count)", "UA-1486, 140.5, 5", height=150)
    if pasted_data:
        rows = [{"Value": x.split(",")[0].strip(), "L2": float(x.split(",")[1]), "Count": int(x.split(",")[2])} 
                for x in pasted_data.strip().split("\n") if len(x.split(",")) == 3]
        df = pd.DataFrame(rows)

if df is not None:
    standard_data, oversized_data = {}, {}
    total_trim = 2 * end_trim_input
    
    for _, row in df.iterrows():
        die, length, count = str(row['Value']), row['L2'], int(row['Count'])
        if length > (max_stock_input - total_trim):
            if die not in oversized_data: oversized_data[die] = []
            oversized_data[die].extend([length] * count)
        else:
            if die not in standard_data: standard_data[die] = []
            standard_data[die].extend([length] * count)

    # --- Processing ---
    results_map = {}
    
    if run_mode == "All Dies":
        if st.button("🚀 Run Full Optimization"):
            with st.status("Calculating...", expanded=False):
                for die, lengths in standard_data.items():
                    results_map[die] = optimize_die(lengths, min_stock_input, max_stock_input, end_trim_input, cut_thickness_input)
            st.session_state['results'] = results_map
    else:
        selected = st.selectbox("Select Die", list(standard_data.keys()))
        if st.button(f"🚀 Optimize {selected}"):
            res = optimize_die(standard_data[selected], min_stock_input, max_stock_input, end_trim_input, cut_thickness_input)
            if 'results' not in st.session_state: st.session_state['results'] = {}
            st.session_state['results'][selected] = res

    # --- Display Results ---
    if 'results' in st.session_state:
        res_df = []
        for die, data in st.session_state['results'].items():
            res_df.append({"Die": die, "Stock": data['sl'], "Bars": len(data['bins'])})
        
        st.subheader("📋 Summary")
        st.table(pd.DataFrame(res_df))

        if st.checkbox("🔍 Show Visual Bar Layouts"):
            tabs = st.tabs(list(st.session_state['results'].keys()))
            for i, die in enumerate(st.session_state['results'].keys()):
                with tabs[i]:
                    data = st.session_state['results'][die]
                    for idx, bar in enumerate(data['bins'], 1):
                        sum_b = sum(bar)
                        kerf_t = (len(bar)-1)*cut_thickness_input
                        rem = data['sl'] - total_trim - sum_b - kerf_t
                        
                        html = f'<div style="display:flex; border:1px solid #333; height:35px; width:100%; background:#eee; margin-bottom:10px; border-radius:5px; overflow:hidden;">'
                        html += f'<div style="background:#6c757d; width:{(end_trim_input/data["sl"])*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div>'
                        for l in bar:
                            html += f'<div style="background:#2b7a78; border-right:1px solid #fff; width:{(l/data["sl"])*100}%; color:white; font-size:11px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{l}</div>'
                        html += f'<div style="background:#fe4a49; width:{(rem/data["sl"])*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">{rem:.1f} Scrap</div>'
                        html += f'<div style="background:#6c757d; width:{(end_trim_input/data["sl"])*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div></div>'
                        st.markdown(html, unsafe_allow_html=True)

    if oversized_data:
        st.markdown("---")
        st.subheader("📏 Oversized Grouped Results")
        for die, lengths in oversized_data.items():
            # Oversized optimization: try to pack pieces together on custom bars
            custom_sl = max(lengths) + total_trim
            res = optimize_die(lengths, custom_sl, custom_sl, end_trim_input, cut_thickness_input)
            with st.expander(f"Oversized Die: {die} - N (Custom Stock: {custom_sl}\")"):
                st.write(f"Total Custom Bars: {len(res['bins'])}")
                for i, b in enumerate(res['bins'], 1):
                    st.write(f"Bar {i}: {b}")
