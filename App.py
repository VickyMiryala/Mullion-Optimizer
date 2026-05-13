import streamlit as st
import pandas as pd
import math

# Page Configuration
st.set_page_config(page_title="Mullion Optimization & Procurement System", layout="wide")

st.title("🏗️ Pro Mullion Die Optimization App")
st.write("Full visual optimization with detailed wastage metrics and bar layouts.")

# --- Sidebar: Configuration ---
st.sidebar.header("⚙️ Configuration Parameters")
min_stock_input = st.sidebar.number_input("Min Bar Stock Length (in)", value=140, step=10)
max_stock_input = st.sidebar.number_input("Max Bar Stock Length (in)", value=260, step=10)
end_trim_input = st.sidebar.number_input("End Trim per Side (in)", value=2.0, step=0.125, help="Deducted from BOTH ends.")
cut_thickness_input = st.sidebar.number_input("Cut Thickness/Kerf (in)", value=0.1875, step=0.0625)

run_mode = st.sidebar.radio("Processing Mode", ("Process All Dies", "Process Die Individually"))
input_method = st.radio("Input Method", ("Upload CSV", "Paste Data Manually"))

# --- Core Logic Functions ---
def calculate_optimization(req_lengths, stock_length, trim, kerf):
    sorted_lengths = sorted(req_lengths, reverse=True)
    bins = []
    usable_stock = stock_length - (2 * trim)
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
    uploaded_file = st.file_uploader("Upload TEST.csv", type=["csv"])
    if uploaded_file: df = pd.read_csv(uploaded_file)
else:
    st.info("Format: Value, L2, Count (e.g., UA-1486, 150.5, 5)")
    pasted_data = st.text_area("Paste Data", height=150)
    if pasted_data:
        rows = []
        for line in pasted_data.strip().split("\n"):
            parts = [x.strip() for x in line.split(",")]
            if len(parts) == 3:
                try: rows.append({"Value": parts[0], "L2": float(parts[1]), "Count": int(parts[2])})
                except: pass
        if rows: df = pd.DataFrame(rows)

if df is not None:
    st.subheader("📊 Data Preview")
    st.dataframe(df, use_container_width=True)
    
    total_trim = 2 * end_trim_input
    usable_max_std = max_stock_input - total_trim

    # Separation logic
    standard_data = {}
    oversized_dict = {}

    for _, row in df.iterrows():
        die, length, count = str(row['Value']), row['L2'], int(row['Count'])
        if length > usable_max_std:
            key = (die, length)
            oversized_dict[key] = oversized_dict.get(key, 0) + count
        else:
            if die not in standard_data: standard_data[die] = []
            standard_data[die].extend([length] * count)

    # Execution State
    if 'results' not in st.session_state: st.session_state['results'] = {}

    # Trigger Buttons
    if run_mode == "Process All Dies":
        if st.button("🚀 Run Full Optimization"):
            with st.spinner("Processing all profiles..."):
                for die, lengths in standard_data.items():
                    max_req = max(lengths)
                    low = max(min_stock_input, math.ceil(max_req) + total_trim)
                    best_sl, best_bins = None, []
                    for sl in range(int(low), int(max_stock_input) + 1):
                        res = calculate_optimization(lengths, sl, end_trim_input, cut_thickness_input)
                        if best_sl is None or len(res) < len(best_bins):
                            best_sl, best_bins = sl, res
                    st.session_state['results'][die] = {"sl": best_sl, "bins": best_bins, "total_len": sum(lengths)}
    else:
        selected_die = st.selectbox("Select Profile", list(standard_data.keys()))
        if st.button(f"🚀 Optimize {selected_die} Only"):
            lengths = standard_data[selected_die]
            max_req = max(lengths)
            low = max(min_stock_input, math.ceil(max_req) + total_trim)
            best_sl, best_bins = None, []
            for sl in range(int(low), int(max_stock_input) + 1):
                res = calculate_optimization(lengths, sl, end_trim_input, cut_thickness_input)
                if best_sl is None or len(res) < len(best_bins):
                    best_sl, best_bins = sl, res
            st.session_state['results'][selected_die] = {"sl": best_sl, "bins": best_bins, "total_len": sum(lengths)}

    # --- Display Results ---
    if st.session_state['results']:
        st.markdown("---")
        st.subheader("📋 Optimization Summary")
        summary_rows = []
        for die, data in st.session_state['results'].items():
            tot_allocated = len(data['bins']) * data['sl']
            scrap = tot_allocated - data['total_len']
            waste_pct = (scrap / tot_allocated) * 100
            summary_rows.append({
                "Die": die, "Stock Length": data['sl'], "Bars": len(data['bins']), 
                "Total Length": data['total_len'], "Scrap (in)": round(scrap, 2), "Waste %": f"{waste_pct:.2f}%"
            })
        st.table(pd.DataFrame(summary_rows))

        # Visual Bar Layouts
        if st.checkbox("🔍 See Proportional Bar Layouts", value=True):
            tabs = st.tabs(list(st.session_state['results'].keys()))
            for i, die in enumerate(st.session_state['results'].keys()):
                with tabs[i]:
                    info = st.session_state['results'][die]
                    sl = info['sl']
                    for idx, bar in enumerate(info['bins'], 1):
                        sum_bar = sum(bar)
                        total_kerf = (len(bar) - 1) * cut_thickness_input
                        rem = sl - total_trim - sum_bar - total_kerf
                        
                        # Colorful Proportional Bar Visualizer
                        html = f'<div style="display:flex; border:1px solid #333; height:35px; width:100%; background:#eee; margin-bottom:10px; border-radius:5px; overflow:hidden;">'
                        html += f'<div style="background:#6c757d; width:{(end_trim_input/sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div>'
                        for l in bar:
                            html += f'<div style="background:#2b7a78; border-right:1px solid #fff; width:{(l/sl)*100}%; color:white; font-size:11px; display:flex; align-items:center; justify-content:center; font-weight:bold;">{l}</div>'
                        if total_kerf > 0:
                            html += f'<div style="background:#3aafa9; width:{(total_kerf/sl)*100}%;"></div>'
                        html += f'<div style="background:#fe4a49; width:{(rem/sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">{rem:.1f} Scrap</div>'
                        html += f'<div style="background:#6c757d; width:{(end_trim_input/sl)*100}%; color:white; font-size:10px; display:flex; align-items:center; justify-content:center;">Trim</div></div>'
                        st.markdown(html, unsafe_allow_html=True)
                        st.write(f"**Bar {idx}**: Cuts {bar} | Total Used: {sum_bar + total_kerf:.2f}\" | Scrap: {rem:.2f}\"")

    # --- Oversized (Grouped) ---
    if oversized_dict:
        st.markdown("---")
        st.warning("⚠️ Oversized Pieces (Custom Order Requirements)")
        over_data = []
        for (die, length), count in oversized_dict.items():
            over_data.append({"Die": f"{die}-N", "Piece Length": length, "Count": count, "Min. Order (incl. Trims)": length + total_trim})
        st.table(pd.DataFrame(over_data))
