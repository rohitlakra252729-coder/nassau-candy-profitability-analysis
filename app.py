
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Nassau Candy Profitability Analysis",
    page_icon="🍬",
    layout="wide"
)

st.title("Product Line Profitability & Margin Performance Analysis")
st.subheader("Nassau Candy Distributor")

FILE_PATH = "Nassau_Candy_Final.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(FILE_PATH)
    df.columns = df.columns.str.strip()

    for col in ["Sales", "Gross Profit", "Cost", "Units"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required = ["Sales", "Gross Profit", "Cost", "Units", "Division", "Product Name"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    df = df.dropna(subset=["Sales", "Gross Profit", "Cost", "Units"])
    df = df[(df["Sales"] > 0) & (df["Units"] > 0)]
    df["Gross Margin (%)"] = (df["Gross Profit"] / df["Sales"]) * 100
    df["Profit per Unit"] = df["Gross Profit"] / df["Units"]
    return df

df = load_data()

st.sidebar.header("Dashboard Filters")

if "Order Date" in df.columns:
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    valid_dates = df["Order Date"].dropna()

    if not valid_dates.empty:
        date_range = st.sidebar.date_input(
            "Order date range",
            value=(valid_dates.min().date(), valid_dates.max().date())
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            df = df[
                df["Order Date"].dt.date.between(date_range[0], date_range[1])
            ]

divisions = sorted(df["Division"].dropna().astype(str).unique())
selected_divisions = st.sidebar.multiselect(
    "Division",
    divisions,
    default=divisions
)
df = df[df["Division"].astype(str).isin(selected_divisions)]

margin_threshold = st.sidebar.slider(
    "Minimum gross margin (%)",
    min_value=-100,
    max_value=100,
    value=-100
)

search = st.sidebar.text_input("Search product")
df = df[df["Gross Margin (%)"] >= margin_threshold]

if search:
    df = df[df["Product Name"].astype(str).str.contains(search, case=False, na=False)]

if df.empty:
    st.warning("No records match the selected filters.")
    st.stop()

total_sales = df["Sales"].sum()
total_profit = df["Gross Profit"].sum()
total_cost = df["Cost"].sum()
total_units = df["Units"].sum()
overall_margin = total_profit / total_sales * 100 if total_sales else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"${total_sales:,.2f}")
c2.metric("Gross Profit", f"${total_profit:,.2f}")
c3.metric("Gross Margin", f"{overall_margin:.2f}%")
c4.metric("Units Sold", f"{total_units:,.0f}")

st.divider()

overview, division_tab, diagnostics, pareto = st.tabs([
    "Product Profitability",
    "Division Performance",
    "Cost & Margin Diagnostics",
    "Profit Concentration"
])

with overview:
    st.header("Product-Level Profitability")

    products = df.groupby("Product Name", as_index=False).agg(
        Sales=("Sales", "sum"),
        **{"Gross Profit": ("Gross Profit", "sum")},
        Cost=("Cost", "sum"),
        Units=("Units", "sum")
    )
    products["Gross Margin (%)"] = (
        products["Gross Profit"] / products["Sales"].replace(0, pd.NA)
    ) * 100
    products["Profit per Unit"] = (
        products["Gross Profit"] / products["Units"].replace(0, pd.NA)
    )

    left, right = st.columns(2)
    with left:
        top_profit = products.nlargest(10, "Gross Profit")
        st.plotly_chart(
            px.bar(top_profit, x="Gross Profit", y="Product Name",
                   orientation="h", title="Top 10 Products by Gross Profit"),
            width="stretch"
        )
    with right:
        top_margin = products.nlargest(10, "Gross Margin (%)")
        st.plotly_chart(
            px.bar(top_margin, x="Gross Margin (%)", y="Product Name",
                   orientation="h", title="Top 10 Products by Gross Margin"),
            width="stretch"
        )

    st.subheader("Product Profitability Table")
    st.dataframe(
        products.sort_values("Gross Profit", ascending=False),
        width="stretch"
    )

with division_tab:
    st.header("Division Performance")

    division = df.groupby("Division", as_index=False).agg(
        Sales=("Sales", "sum"),
        **{"Gross Profit": ("Gross Profit", "sum")},
        Cost=("Cost", "sum")
    )
    division["Gross Margin (%)"] = (
        division["Gross Profit"] / division["Sales"].replace(0, pd.NA)
    ) * 100

    st.plotly_chart(
        px.bar(division, x="Division", y=["Sales", "Gross Profit"],
               barmode="group", title="Revenue vs Gross Profit by Division"),
        width="stretch"
    )
    st.plotly_chart(
        px.bar(division, x="Division", y="Gross Margin (%)",
               title="Gross Margin by Division"),
        width="stretch"
    )
    st.dataframe(division, width="stretch")

with diagnostics:
    st.header("Cost vs Margin Diagnostics")

    st.plotly_chart(
        px.scatter(
            df, x="Sales", y="Cost", color="Division",
            size="Units", hover_name="Product Name",
            title="Cost vs Sales"
        ),
        width="stretch"
    )

    st.plotly_chart(
        px.scatter(
            df, x="Sales", y="Gross Margin (%)", color="Division",
            hover_name="Product Name",
            title="Sales vs Gross Margin"
        ),
        width="stretch"
    )

    st.subheader("Potential Margin Risks")
    risks = df[df["Gross Margin (%)"] < 10].copy()
    st.dataframe(risks, width="stretch")

with pareto:
    st.header("Profit Concentration Analysis")

    products = df.groupby("Product Name", as_index=False).agg(
        Sales=("Sales", "sum"),
        **{"Gross Profit": ("Gross Profit", "sum")}
    )

    for metric in ["Sales", "Gross Profit"]:
        ranked = products.sort_values(metric, ascending=False).copy()
        total = ranked[metric].sum()
        ranked["Cumulative Contribution (%)"] = (
            ranked[metric].cumsum() / total * 100 if total > 0 else 0
        )
        st.subheader(f"Pareto Analysis: {metric}")
        st.plotly_chart(
            px.line(
                ranked, x="Product Name",
                y="Cumulative Contribution (%)",
                title=f"Cumulative {metric} Contribution"
            ),
            width="stretch"
        )
        count_80 = (
            (ranked["Cumulative Contribution (%)"] < 80).sum() + 1
            if total > 0 else 0
        )
        st.write(f"Products needed to reach approximately 80% of {metric}: {count_80}")
        st.dataframe(ranked, width="stretch")

st.caption("Analysis is based on the uploaded Nassau Candy dataset and selected filters.")
