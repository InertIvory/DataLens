import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="DataLens | Auto Data Analysis", page_icon="📊", layout="wide")

st.title("📊 DataLens")
st.caption("Upload a dataset. Get an automatic data profile, visualizations, and an exportable report.")

@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes, filename: str):
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(io.BytesIO(file_bytes))
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(file_bytes))
    if suffix == ".json":
        return pd.read_json(io.BytesIO(file_bytes))
    raise ValueError("Unsupported file type. Upload CSV, XLSX, XLS, or JSON.")

def fmt_num(value):
    if pd.isna(value):
        return "—"
    return f"{value:,.2f}" if isinstance(value, (float,)) else f"{value:,}"

def make_profile(df):
    rows, cols = df.shape
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    dates = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    missing_cells = int(df.isna().sum().sum())
    total_cells = max(rows * cols, 1)
    return {
        "rows": rows, "columns": cols, "numeric": numeric,
        "categorical": categorical, "dates": dates,
        "missing_cells": missing_cells,
        "missing_pct": missing_cells / total_cells * 100,
        "duplicates": int(df.duplicated().sum()),
    }

def create_text_report(df, profile):
    lines = [
        "# Automated data analysis report",
        "",
        f"- Rows: {profile['rows']:,}",
        f"- Columns: {profile['columns']:,}",
        f"- Numeric columns: {len(profile['numeric'])}",
        f"- Categorical/text columns: {len(profile['categorical'])}",
        f"- Date columns: {len(profile['dates'])}",
        f"- Missing cells: {profile['missing_cells']:,} ({profile['missing_pct']:.2f}%)",
        f"- Duplicate rows: {profile['duplicates']:,}",
        "",
        "## Column types",
        "",
        df.dtypes.astype(str).to_frame("Detected type").to_markdown(),
        "",
        "## Numeric summary",
        "",
    ]
    if profile["numeric"]:
        lines.append(df[profile["numeric"]].describe().round(3).to_markdown())
    else:
        lines.append("No numeric columns detected.")
    lines += ["", "## Missing values by column", "", df.isna().sum().to_frame("Missing values").to_markdown()]
    return "\n".join(lines)

uploaded = st.file_uploader(
    "Upload your dataset",
    type=["csv", "xlsx", "xls", "json"],
    help="Supported formats: CSV, Excel, and JSON."
)

if uploaded is None:
    st.info("Start by uploading a CSV, Excel, or JSON file.")
    st.markdown("""
    **What DataLens does automatically**
    - Profiles rows, columns, data types, missing values, and duplicate rows
    - Calculates descriptive statistics for numeric columns
    - Finds common values in categorical columns
    - Builds distributions, category charts, correlations, and relationship plots
    - Lets you filter data and download a cleaned CSV plus a Markdown report
    """)
    st.stop()

try:
    original_df = load_data(uploaded.getvalue(), uploaded.name)
except Exception as exc:
    st.error(f"Could not read this file: {exc}")
    st.stop()

if original_df.empty:
    st.warning("The uploaded file contains no rows.")
    st.stop()

df = original_df.copy()
profile = make_profile(df)

with st.sidebar:
    st.header("⚙️ Analysis settings")
    st.write(f"**File:** {uploaded.name}")
    st.write(f"**Size:** {uploaded.size / 1024:.1f} KB")
    st.divider()
    st.subheader("Optional cleaning")
    drop_duplicates = st.checkbox("Remove duplicate rows", value=False)
    drop_empty = st.checkbox("Remove completely empty columns", value=True)
    if drop_empty:
        df = df.dropna(axis=1, how="all")
    if drop_duplicates:
        df = df.drop_duplicates()
    st.caption("Cleaning changes are applied in memory; your uploaded original file is not modified.")

profile = make_profile(df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Rows", f"{profile['rows']:,}")
c2.metric("Columns", f"{profile['columns']:,}")
c3.metric("Missing cells", f"{profile['missing_cells']:,}", f"{profile['missing_pct']:.1f}% of all cells")
c4.metric("Duplicate rows", f"{profile['duplicates']:,}")
c5.metric("Numeric columns", len(profile["numeric"]))

tab_overview, tab_visuals, tab_relationships, tab_data, tab_export = st.tabs(
    ["Overview", "Visualizations", "Relationships", "Data explorer", "Export"]
)

with tab_overview:
    st.subheader("Dataset overview")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("**Column types and completeness**")
        overview = pd.DataFrame({
            "Column": df.columns,
            "Data type": [str(t) for t in df.dtypes],
            "Missing": df.isna().sum().values,
            "Missing %": (df.isna().mean().values * 100).round(2),
            "Unique values": [df[c].nunique(dropna=True) for c in df.columns],
        })
        st.dataframe(overview, use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Missing values by column**")
        missing = df.isna().sum().sort_values(ascending=False)
        missing = missing[missing > 0]
        if len(missing):
            missing_df = missing.rename_axis("Column").reset_index(name="Missing values")
            fig = px.bar(missing_df, x="Missing values", y="Column", orientation="h")
            fig.update_layout(height=max(300, 35 * len(missing_df)), margin=dict(l=5, r=5, t=20, b=5))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No missing values detected.")
    st.subheader("Descriptive statistics")
    if profile["numeric"]:
        st.dataframe(df[profile["numeric"]].describe().T.round(3), use_container_width=True)
    else:
        st.info("No numeric columns were detected.")

    if profile["categorical"]:
        st.subheader("Categorical column highlights")
        selected_cat = st.selectbox("Choose a categorical column", profile["categorical"])
        counts = df[selected_cat].astype("string").fillna("(missing)").value_counts().head(15)
        st.dataframe(counts.rename_axis("Value").reset_index(name="Count"), use_container_width=True, hide_index=True)

with tab_visuals:
    st.subheader("Explore individual columns")
    all_columns = df.columns.tolist()
    selected_column = st.selectbox("Select a column", all_columns, key="single_column")
    series = df[selected_column]
    if pd.api.types.is_numeric_dtype(series):
        chart_type = st.radio("Chart", ["Histogram", "Box plot"], horizontal=True)
        if chart_type == "Histogram":
            fig = px.histogram(df, x=selected_column, marginal="box", title=f"Distribution of {selected_column}")
        else:
            fig = px.box(df, y=selected_column, points="outliers", title=f"Spread of {selected_column}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        counts = series.astype("string").fillna("(missing)").value_counts().head(25)
        chart_df = counts.rename_axis("Value").reset_index(name="Count")
        fig = px.bar(chart_df, x="Value", y="Count", title=f"Most common values in {selected_column}")
        st.plotly_chart(fig, use_container_width=True)

    if profile["dates"] and profile["numeric"]:
        st.subheader("Trend over time")
        date_col = st.selectbox("Date column", profile["dates"])
        metric_col = st.selectbox("Numeric measure", profile["numeric"])
        trend = df[[date_col, metric_col]].dropna().copy()
        trend[date_col] = pd.to_datetime(trend[date_col], errors="coerce")
        trend = trend.dropna().sort_values(date_col)
        if not trend.empty:
            grouped = trend.set_index(date_col)[metric_col].resample("D").mean().dropna().reset_index()
            fig = px.line(grouped, x=date_col, y=metric_col, title=f"{metric_col} over time")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("There are no valid date/measure pairs to plot.")

with tab_relationships:
    st.subheader("Relationships between variables")
    if len(profile["numeric"]) >= 2:
        corr = df[profile["numeric"]].corr(numeric_only=True)
        fig = px.imshow(corr, text_auto=".2f", aspect="auto", title="Correlation matrix", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        st.plotly_chart(fig, use_container_width=True)
        x_col, y_col = st.columns(2)
        with x_col:
            x_var = st.selectbox("X variable", profile["numeric"], index=0)
        with y_col:
            y_default = 1 if len(profile["numeric"]) > 1 else 0
            y_var = st.selectbox("Y variable", profile["numeric"], index=y_default)
        if x_var != y_var:
            scatter = df[[x_var, y_var]].dropna()
            fig = px.scatter(scatter, x=x_var, y=y_var, trendline="ols", title=f"{y_var} vs {x_var}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Choose two different variables to create a scatter plot.")
    else:
        st.info("At least two numeric columns are needed for correlation and scatter analysis.")

with tab_data:
    st.subheader("Filter and inspect records")
    filtered = df.copy()
    filterable = [c for c in df.columns if df[c].nunique(dropna=True) <= 100]
    chosen_filter = st.selectbox("Optional filter column", ["(no filter)"] + filterable)
    if chosen_filter != "(no filter)":
        values = df[chosen_filter].dropna().unique().tolist()
        selected_values = st.multiselect("Keep selected values", values, default=values[:min(10, len(values))])
        filtered = filtered[filtered[chosen_filter].isin(selected_values)]
    st.caption(f"Showing {len(filtered):,} of {len(df):,} rows.")
    st.dataframe(filtered, use_container_width=True, height=420)
    st.download_button(
        "Download filtered data as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_data.csv",
        mime="text/csv"
    )

with tab_export:
    st.subheader("Export your analysis")
    report = create_text_report(df, profile)
    st.download_button(
        "Download analysis report (Markdown)",
        data=report.encode("utf-8"),
        file_name="data_analysis_report.md",
        mime="text/markdown"
    )
    st.download_button(
        "Download analysed data (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="analysed_data.csv",
        mime="text/csv"
    )
    st.caption("The report is an automated statistical profile. It does not infer domain-specific causation or replace expert review.")
