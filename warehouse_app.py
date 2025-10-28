import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
# -------------------------------------------------------------
# Page Config
# -------------------------------------------------------------
st.set_page_config(
    page_title="Warehouse Optimization Tool",
    page_icon="🏭",
    layout="wide"
)
# -------------------------------------------------------------
# Title and Description
# -------------------------------------------------------------
st.title("🏭 Warehouse Optimization Dashboard")
st.markdown("""
This dashboard helps **NexGen Logistics** optimize warehouse inventory by  
identifying **understocked**, **optimal**, and **overstocked** product categories.  
Use the sidebar filters to explore insights by warehouse or category.
""")
# -------------------------------------------------------------
# Load Data (Auto-fixes column names)
# -------------------------------------------------------------
@st.cache_data
def load_data():
    # Read CSV
    df = pd.read_csv("warehouse_inventory.csv")

    # Clean and standardize column names
    df.columns = (
        df.columns.str.strip()           # Remove extra spaces
                 .str.replace(" ", "_")  # Replace spaces with underscores
                 .str.replace("-", "_")  # Replace hyphens with underscores
                 .str.title()            # Capitalize words (optional)
    )

    # Convert date column safely
    if 'Last_Restocked_Date' in df.columns:
        df['Last_Restocked_Date'] = pd.to_datetime(df['Last_Restocked_Date'], errors='coerce')

    # Drop rows missing key values (only if columns exist)
    required_cols = [c for c in ['Stock_Level', 'Reorder_Level'] if c in df.columns]
    if required_cols:
        df.dropna(subset=required_cols, inplace=True)

    return df

df = load_data()
def classify_stock(row):
    if row['Stock_Level'] < row['Reorder_Level']:
        return "Understocked"
    elif row['Stock_Level'] < 1.5 * row['Reorder_Level']:
        return "Optimal"
    else:
        return "Overstocked"

# Ensure essential columns exist
expected_cols = ['Warehouse_Id', 'Location', 'Product_Category', 'Reorder_Level', 'Storage_Cost_per_Unit']
for col in expected_cols:
    if col not in df.columns:
        st.error(f"❌ Missing column: {col}. Please check your CSV file.")
        st.stop()
# # -------------------------------------------------------------
# Derived Calculations
# -------------------------------------------------------------

# Use correct stock column name
df['Status'] = df.apply(
    lambda x: (
        "Understocked" if x['Current_Stock_Units'] < x['Reorder_Level']
        else "Optimal" if x['Current_Stock_Units'] < 1.5 * x['Reorder_Level']
        else "Overstocked"
    ), axis=1
)

# Days since last restock
if 'Last_Restocked_Date' in df.columns:
    df['Days_Since_Restock'] = (pd.Timestamp.today() - df['Last_Restocked_Date']).dt.days
else:
    df['Days_Since_Restock'] = None

# Calculate excess stock and potential savings
df['Excess_Stock'] = (df['Current_Stock_Units'] - df['Reorder_Level']).clip(lower=0)

# Assume ₹10 cost per excess unit as example (you can change this)
df['Potential_Savings'] = df['Excess_Stock'] * 10
# -------------------------------------------------------------
# Sidebar Filters
# -------------------------------------------------------------
st.sidebar.header("🔍 Filters")

warehouses = st.sidebar.multiselect("Select Warehouse(s)", sorted(df['Warehouse_Id'].unique()))
categories = st.sidebar.multiselect("Select Product Category", sorted(df['Product_Category'].unique()))

filtered_df = df.copy()
if warehouses:
    filtered_df = filtered_df[filtered_df['Warehouse_Id'].isin(warehouses)]
if categories:
    filtered_df = filtered_df[filtered_df['Product_Category'].isin(categories)]
# Normalize column names: remove spaces, unify case, etc.
df.columns = (
    df.columns.str.strip()
              .str.replace(" ", "_")
              .str.replace("-", "_")
              .str.replace("/", "_")
              .str.title()
)

# -------------------------------------------------------------
# KPI Summary (Safe version for your dataset)
# -------------------------------------------------------------
st.markdown("### 📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

# Total warehouses
warehouse_col = [c for c in df.columns if 'Warehouse' in c][0]
col1.metric("🏢 Warehouses", filtered_df[warehouse_col].nunique())

# Total categories
category_col = [c for c in df.columns if 'Product' in c and 'Category' in c][0]
col2.metric("📦 Categories", filtered_df[category_col].nunique())

# Storage cost (auto-detect cost column)
stock_col = [c for c in df.columns if 'Stock' in c][0]
cost_col = [c for c in df.columns if 'Cost' in c][0]

filtered_df['Total_Storage_Cost'] = filtered_df[stock_col] * filtered_df[cost_col]
col3.metric("💰 Total Storage Cost", f"₹{filtered_df['Total_Storage_Cost'].sum():,.0f}")

# Understocked items
col4.metric("⚠️ Understocked Items", (filtered_df['Status'] == 'Understocked').sum())

# -------------------------------------------------------------
# Visualization 1: Stock Status Distribution
# -------------------------------------------------------------
st.subheader("📦 Stock Status by Warehouse")
fig1 = px.histogram(filtered_df, x='Warehouse_Id', color='Status', barmode='group',
                    title='Stock Distribution per Warehouse')
st.plotly_chart(fig1, use_container_width=True)

# -------------------------------------------------------------
# Visualization 2: Storage Cost Breakdown (Fixed)
# -------------------------------------------------------------
st.subheader("💰 Storage Cost by Product Category")

# First, check and detect the correct cost and warehouse columns dynamically
cost_col = [c for c in filtered_df.columns if 'Cost' in c][0]
warehouse_col = [c for c in filtered_df.columns if 'Warehouse' in c][0]

# Create bar chart using detected columns
fig2 = px.bar(
    filtered_df,
    x='Product_Category',
    y=cost_col,  # dynamically detected
    color=warehouse_col,
    title='Storage Cost per Category',
    text_auto='.2s'
)
st.plotly_chart(fig2, use_container_width=True)

# -------------------------------------------------------------
# Visualization 3: Stock vs Reorder Level (Fixed)
# -------------------------------------------------------------
st.subheader("📉 Stock Level vs Reorder Level")

# Dynamically detect column names
stock_col = [c for c in filtered_df.columns if 'Stock' in c][0]
reorder_col = [c for c in filtered_df.columns if 'Reorder' in c][0]
cost_col = [c for c in filtered_df.columns if 'Cost' in c][0]
warehouse_col = [c for c in filtered_df.columns if 'Warehouse' in c][0]

# Create scatter plot
fig3 = px.scatter(
    filtered_df,
    x='Product_Category',
    y=stock_col,
    size=cost_col,
    color='Status',
    hover_data=[warehouse_col, reorder_col],
    title='Stock vs Reorder Levels'
)
st.plotly_chart(fig3, use_container_width=True)

# -------------------------------------------------------------
# Visualization 4: Days Since Last Restock (Fixed)
# -------------------------------------------------------------
if 'Days_Since_Restock' in filtered_df.columns:
    st.subheader("⏰ Days Since Last Restock")

    fig4 = px.bar(
        filtered_df,
        x='Product_Category',
        y='Days_Since_Restock',
        color=warehouse_col,
        title='Days Since Last Restock per Category'
    )
    st.plotly_chart(fig4, use_container_width=True)
# -------------------------------------------------------------
# Insights and Recommendations
# -------------------------------------------------------------
st.subheader("🧠 Insights & Recommendations")

understocked = filtered_df[filtered_df['Status'] == 'Understocked']
overstocked = filtered_df[filtered_df['Status'] == 'Overstocked']

st.markdown(f"""
- **Understocked Products:** {len(understocked)} → Restock immediately to avoid shortages.  
- **Overstocked Products:** {len(overstocked)} → Possible savings of ₹{overstocked['Potential_Savings'].sum():,.0f}.  
- **Average Days Since Restock:** {filtered_df['Days_Since_Restock'].mean():.1f} days.  
- Regularly reviewing stock levels will improve warehouse efficiency and reduce storage costs.
""")

# -------------------------------------------------------------
# Data Download
# -------------------------------------------------------------
st.download_button(
    label="📥 Download Filtered Data as CSV",
    data=filtered_df.to_csv(index=False).encode('utf-8'),
    file_name='optimized_warehouse_data.csv',
    mime='text/csv'
)

# -------------------------------------------------------------
# Footer
# -------------------------------------------------------------
st.markdown("---")
st.caption("© 2025 NexGen Logistics | Developed for OFI Logistics Innovation Challenge")