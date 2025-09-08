import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from streamlit_plotly_events import plotly_events
import requests
import io

# =========================
# Helper functions
# =========================

def map_status(score):
    """Converts a numeric score (1, 2, 3) to a text status."""
    if score == 1:
        return "Need Action"
    elif score == 2:
        return "Caution"
    elif score == 3:
        return "Okay"
    return "UNKNOWN"

def color_score(val):
    """Returns CSS style for SCORE cells (used in pandas Styler)."""
    if pd.isna(val):
        return ""
    try:
        v = int(val)
    except Exception:
        return ""
    if v == 1:
        return "background-color: red; color: white;"
    elif v == 2:
        return "background-color: yellow; color: black;"
    elif v == 3:
        return "background-color: green; color: white;"
    return ""

def color_status(val):
    """Returns CSS style for STATUS cells (used in pandas Styler)."""
    if val == "Need Action":
        return "background-color: red; color: white;"
    elif val == "Caution":
        return "background-color: yellow; color: black;"
    elif val =="Okay":
        return "background-color: green; color: white;"
    return ""

# =========================
# Main Streamlit App
# =========================
def main():
    st.set_page_config(layout="wide")
        # --- Add Logo and Title ---
    col1, col2 = st.columns([1, 10])
    with col1:
        st.image("https://raw.githubusercontent.com/AlvinWinarta2111/equipment-monitoring-dashboard/main/images/alamtri_logo.jpeg", width=175)
    with col2:
        st.title("Site Condition Monitoring Dashboard")
    # --- End Logo and Title ---

    if 'clicked_trend_point' not in st.session_state:
        st.session_state.clicked_trend_point = None

    RAW_FILE_URL = "https://raw.githubusercontent.com/AlvinWinarta2111/equipment-monitoring-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx"

    @st.cache_data(ttl=300)
    def load_data():
        response = requests.get(RAW_FILE_URL)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), sheet_name="Scorecard", header=1)

    try:
        df = load_data()
    except Exception as e:
        st.error(f"Error reading data from GitHub file: {e}")
        return

    df.columns = [col.strip().upper() for col in df.columns]
    if "CONDITION MONITORING SCORE" not in df.columns:
        st.error("Error: 'CONDITION MONITORING SCORE' column not found.")
        return

    df = df.rename(columns={"CONDITION MONITORING SCORE": "SCORE"})
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # Clean categorical data
    for col in ['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION']:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.strip().str.upper()

    df.dropna(subset=['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION', 'DATE', 'SCORE'], inplace=True)
    df["SCORE"] = df["SCORE"].astype(int)

    # Filter scores
    df = df[df["SCORE"].isin([1, 2, 3])]
    df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

    # =========================
    # Dashboard Components
    # =========================
    min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df_filtered_by_date = df[(df["DATE"].dt.date >= date_range[0]) & (df["DATE"].dt.date <= date_range[1])]
    else:
        df_filtered_by_date = df

    if df_filtered_by_date.empty:
        st.warning("No data available for the selected date range.")
        return

    # Aggregation
    system_scores = df_filtered_by_date.groupby(["AREA", "SYSTEM"])["SCORE"].min().reset_index()
    area_scores = system_scores.groupby("AREA")["SCORE"].min().reset_index()

    # Create a two-column layout for side-by-side charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("AREA Score Distribution")
        fig_area = px.bar(
            area_scores, x="AREA", y="SCORE", color=area_scores["SCORE"].astype(str), text="SCORE",
            color_discrete_map={"3": "green", "2": "yellow", "1": "red"}, title="Lowest Score per AREA",
            category_orders={"SCORE": ["3", "2", "1"]}
        )
        fig_area.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1))
        st.plotly_chart(fig_area, use_container_width=True)

    with col2:
        st.subheader("Equipment Status Distribution per AREA")
        latest_for_pie = df_filtered_by_date.sort_values("DATE").groupby("EQUIPMENT DESCRIPTION", as_index=False).last()
        area_dist = latest_for_pie.groupby(["AREA", "EQUIP_STATUS"])["EQUIPMENT DESCRIPTION"].count().reset_index(name="COUNT")
        areas = sorted(area_dist["AREA"].unique())
        
        # Use a single column to display all pie charts vertically
        for area in areas:
            st.markdown(f"**{area}**")
            area_data = area_dist[area_dist["AREA"] == area]
            fig_pie = px.pie(
                area_data, names="EQUIP_STATUS", values="COUNT", color="EQUIP_STATUS",
                color_discrete_map={"Need Action": "red", "Caution": "yellow", "Okay": "green"}, hole=0.4,
                category_orders={"EQUIP_STATUS": ["Okay", "Caution", "Need Action"]}
            )
            fig_pie.update_traces(textinfo='percent+value', textfont_size=16)
            fig_pie.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("SYSTEM Score Distribution")
    fig_system = px.bar(
        system_scores, x="SYSTEM", y="SCORE", color=system_scores["SCORE"].astype(str), text="SCORE",
        color_discrete_map={"3": "green", "2": "yellow", "1": "red"}, title="Lowest Score per SYSTEM",
        category_orders={"SCORE": ["3", "2", "1"]}
    )
    fig_system.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1), xaxis=dict(tickangle=-45))
    st.plotly_chart(fig_system, use_container_width=True)

    st.subheader("Area Status (Lowest Score)")
    st.dataframe(area_scores.style.map(color_score, subset=["SCORE"]).hide(axis="index"))

    st.subheader("System Status Explorer")
    system_summary = df_filtered_by_date.groupby("SYSTEM").agg({"SCORE": "min"}).reset_index()
    system_summary["STATUS"] = system_summary["SCORE"].apply(map_status)
    gb = GridOptionsBuilder.from_dataframe(system_summary[["SYSTEM", "STATUS", "SCORE"]])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(resizable=False, filter=True, sortable=True)
    cell_style_jscode = JsCode("""
        function(params) {
            if (params.value == 'Okay') return {'backgroundColor': 'green', 'color': 'white'};
            if (params.value == 'Caution') return {'backgroundColor': 'yellow',
