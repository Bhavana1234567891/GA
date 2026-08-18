import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Sales Dashboard",
    layout="wide"
)

st.title("📊 Sales Analytics Dashboard")

# Load Data
df = pd.read_csv("sales_data.csv")

df["Date"] = pd.to_datetime(df["Date"])

# Sidebar Filters
st.sidebar.header("Filters")

category = st.sidebar.multiselect(
    "Category",
    options=df["Category"].unique(),
    default=df["Category"].unique()
)

region = st.sidebar.multiselect(
    "Region",
    options=df["Region"].unique(),
    default=df["Region"].unique()
)

filtered_df = df[
    (df["Category"].isin(category)) &
    (df["Region"].isin(region))
]

# KPIs
st.header("Key Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Revenue",
        f"${filtered_df['Revenue'].sum():,.0f}"
    )

with col2:
    st.metric(
        "Total Units Sold",
        filtered_df["Units Sold"].sum()
    )

with col3:
    st.metric(
        "Products Sold",
        filtered_df["Product"].nunique()
    )

st.divider()

# Dataset
st.subheader("Sales Data")

st.dataframe(filtered_df)

st.divider()

# Revenue by Product
st.subheader("Revenue by Product")

product_revenue = filtered_df.groupby("Product")["Revenue"].sum().reset_index()

fig = px.bar(
    product_revenue,
    x="Product",
    y="Revenue",
    color="Product"
)

st.plotly_chart(fig, use_container_width=True)

# Sales Trend
st.subheader("Daily Revenue Trend")

daily = filtered_df.groupby("Date")["Revenue"].sum().reset_index()

fig2 = px.line(
    daily,
    x="Date",
    y="Revenue",
    markers=True
)

st.plotly_chart(fig2, use_container_width=True)

# Revenue by Region
st.subheader("Revenue by Region")

region_data = filtered_df.groupby("Region")["Revenue"].sum().reset_index()

fig3 = px.pie(
    region_data,
    values="Revenue",
    names="Region"
)

st.plotly_chart(fig3, use_container_width=True)

# Top Products
st.subheader("Top Selling Products")

top = (
    filtered_df.groupby("Product")["Units Sold"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(top)

# Summary
st.subheader("Summary")

best = top.idxmax()
worst = top.idxmin()

st.success(f"🏆 Best Selling Product: {best}")

st.error(f"📉 Least Selling Product: {worst}")