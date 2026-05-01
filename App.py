import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Mullion Optimizer & Procurement Pro", layout="wide")

st.title("🏗️ Mullion Die Optimization & Procurement App")
st.write("Determine the most cost-effective defined stock length to order and generate an optimized cutting layout for undefined required lengths.")

# Sidebar Inputs
st.sidebar.header("Input Parameters")

# Input for Undefined Required Lengths
lengths_input = st.sidebar.text_input(
    "Required Lengths (in inches, separated by commas)", 
    "144.5, 96.0, 72.25, 55.0, 144.5, 120.0, 60.5, 45.0, 32.0"
)

# Input for Available Defined Stock Lengths
stock_input = st.sidebar.text_input(
    "Available Stock Lengths (in inches, separated by commas)", 
    "240, 288, 320"
)

# Parse the inputs safely
try:
    required_lengths = [float(x.strip()) for x in lengths_input.split(",") if x.strip()]
except ValueError:
    required_lengths = []
    st.sidebar.error("Please enter valid numerical lengths separated by commas.")

try:
    available_stocks = [float(x.strip()) for x in stock_input.split(",") if x.strip()]
except ValueError:
    available_stocks = []
    st.sidebar.error("Please enter valid numerical stock lengths separated by commas.")

# Optimization Logic
def calculate_mullion_optimization(req_lengths, stock_length):
    sorted_lengths = sorted(req_lengths, reverse=True)
    bins = []
    
    for length in sorted_lengths:
        placed = False
        for b in bins:
            if sum(b) + length <= stock_length:
                b.append(length)
                placed = True
                break
        if not placed:
            bins.append([length])
            
    total_stock_bars = len(bins)
    total_required = sum(req_lengths)
    total_allocated = total_stock_bars * stock_length
    scrap = total_allocated - total_required
    scrap_pct = (scrap / total_allocated) * 100 if total_allocated > 0 else 0
    
    return {
        "stock_length": stock_length,
        "bars_needed": total_stock_bars,
        "scrap_percentage": scrap_pct,
        "scrap_inches": scrap,
        "layout": bins
    }

# Main Application Layout
if required_lengths and available_stocks:
    results = []
    for sl in available_stocks:
        results.append(calculate_mullion_optimization(required_lengths, sl))
    
    # Find the optimal choice based on minimum scrap inches
    best_choice = min(results, key=lambda x: x["scrap_inches"])
    
    st.subheader("📊 Optimization Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Optimal Stock Length", f"{best_choice['stock_length']:.1f} in")
    col2.metric("Total Bars Needed", f"{best_choice['bars_needed']}")
    col3.metric("Scrap Percentage", f"{best_choice['scrap_percentage']:.2f}%")
    
    st.markdown("---")
    
    # Cutting Layout Layout
    st.subheader("📋 Optimal Cutting Layout")
    st.write("The following layout minimizes waste and fits all undefined pieces into the minimum number of defined profiles.")
    
    for idx, bar in enumerate(best_choice['layout'], 1):
        sum_bar = sum(bar)
        remainder = best_choice['stock_length'] - sum_bar
        
        with st.expander(f"Stock Bar {idx} | Length Used: {sum_bar:.1f} in | Scrap Remaining: {remainder:.1f} in", expanded=True):
            # Display contents of each bar
            df_cuts = pd.DataFrame({"Cut Length (in)": bar}).T
            st.dataframe(df_cuts, use_container_width=True)
            
    # Procurement Comparison Matrix
    st.markdown("---")
    st.subheader("🛒 Procurement Comparison Matrix")
    df_comp = pd.DataFrame(results).rename(columns={
        "stock_length": "Stock Length (in)",
        "bars_needed": "Bars Required",
        "scrap_inches": "Total Scrap (in)",
        "scrap_percentage": "Waste %"
    })
    
    st.dataframe(
        df_comp[["Stock Length (in)", "Bars Required", "Total Scrap (in)", "Waste %"]].style.format({
            "Stock Length (in)": "{:.1f}",
            "Bars Required": "{:.0f}",
            "Total Scrap (in)": "{:.2f}",
            "Waste %": "{:.2f}%"
        }),
        use_container_width=True
    )
else:
    st.info("Enter the required lengths and available stock profiles in the sidebar to generate your layout.")
