import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
import requests
import io

# =========================
# Helper functions
# =========================

def map_status(score):
    if score == 1:
        return "Need Action"
    elif score == 2:
        return "Caution"
    elif score == 3:
        return "Okay"
    return "UNKNOWN"

def color_score(val):
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
    st.title("📊 Condition Monitoring Dashboard")

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

    for col in ['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION']:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.strip().str.upper()

    df.dropna(subset=['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION', 'DATE', 'SCORE'], inplace=True)
    df["SCORE"] = df["SCORE"].astype(int)
    df = df[df["SCORE"].isin([1, 2, 3])]
    df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

    min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df_filtered_by_date = df[(df["DATE"].dt.date >= date_range[0]) & (df["DATE"].dt.date <= date_range[1])]
    else:
        df_filtered_by_date = df

    if df_filtered_by_date.empty:
        st.warning("No data available for the selected date range.")
        return

    # =========================
    # Aggregation + Graphs
    # =========================
    system_scores = df_filtered_by_date.groupby(["AREA", "SYSTEM"])["SCORE"].min().reset_index()
    area_scores = system_scores.groupby("AREA")["SCORE"].min().reset_index()

    st.subheader("AREA Score Distribution")
    fig_area = px.bar(
        area_scores, x="AREA", y="SCORE", color=area_scores["SCORE"].astype(str), text="SCORE",
        color_discrete_map={"3": "green", "2": "yellow", "1": "red"}, title="Lowest Score per AREA",
        category_orders={"SCORE": ["3", "2", "1"]}
    )
    fig_area.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1))
    st.plotly_chart(fig_area, use_container_width=True)

    st.subheader("SYSTEM Score Distribution")
    fig_system = px.bar(
        system_scores, x="SYSTEM", y="SCORE", color=system_scores["SCORE"].astype(str), text="SCORE",
        color_discrete_map={"3": "green", "2": "yellow", "1": "red"}, title="Lowest Score per SYSTEM",
        category_orders={"SCORE": ["3", "2", "1"]}
    )
    fig_system.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1), xaxis=dict(tickangle=-45))
    st.plotly_chart(fig_system, use_container_width=True)

    # =========================
    # System Status Explorer
    # =========================
    st.subheader("System Status Explorer")
    system_summary = df_filtered_by_date.groupby("SYSTEM").agg({"SCORE": "min"}).reset_index()
    system_summary["STATUS"] = system_summary["SCORE"].apply(map_status)

    gb = GridOptionsBuilder.from_dataframe(system_summary[["SYSTEM", "STATUS", "SCORE"]])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(resizable=False, filter=True, sortable=True)
    cell_style_jscode = JsCode("""
        function(params) {
            if (params.value == 'Okay') return {'backgroundColor': 'green', 'color': 'white'};
            if (params.value == 'Caution') return {'backgroundColor': 'yellow', 'color': 'black'};
            if (params.value == 'Need Action') return {'backgroundColor': 'red', 'color': 'white'};
            return null;
        }""")
    gb.configure_column("STATUS", cellStyle=cell_style_jscode)
    gridOptions = gb.build()
    gridOptions['suppressMovableColumns'] = True
    grid_response = AgGrid(
        system_summary, gridOptions=gridOptions, enable_enterprise_modules=True,
        update_mode=GridUpdateMode.SELECTION_CHANGED, fit_columns_on_grid_load=True,
        height=300, theme="streamlit", allow_unsafe_jscode=True
    )

    selected_system_rows = grid_response.get("selected_rows", [])
    if isinstance(selected_system_rows, pd.DataFrame):
        selected_system_rows = selected_system_rows.to_dict("records")

    if selected_system_rows:
        selected_system = selected_system_rows[0].get("SYSTEM")
        detail_df = df_filtered_by_date[df_filtered_by_date["SYSTEM"] == selected_system].copy()
        detail_df = detail_df.sort_values(by="DATE", ascending=False)

        # Equipment table
        detail_df["STATUS"] = detail_df["SCORE"].apply(map_status)
        st.subheader(f"Equipment in {selected_system}")
        st.dataframe(detail_df[["EQUIPMENT DESCRIPTION", "DATE", "SCORE", "STATUS"]])

        # ========== Dropdown Date Selection ==========
        st.subheader("📅 Select Date for Equipment Details")

        available_years = sorted(detail_df["DATE"].dt.year.unique())
        year = st.selectbox("Year", available_years)

        available_months = sorted(detail_df[detail_df["DATE"].dt.year == year]["DATE"].dt.month.unique())
        month = st.selectbox("Month", available_months)

        available_days = sorted(detail_df[(detail_df["DATE"].dt.year == year) & (detail_df["DATE"].dt.month == month)]["DATE"].dt.day.unique())
        day = st.selectbox("Day", available_days)

        selected_date = pd.to_datetime(f"{year}-{month}-{day}")

        st.write(f"Showing data for **{selected_date.strftime('%d/%m/%Y')}**")

        date_df = detail_df[detail_df["DATE"].dt.date == selected_date.date()]

        if not date_df.empty:
            st.dataframe(date_df[["EQUIPMENT DESCRIPTION", "DATE", "SCORE", "STATUS", "FINDING", "ACTION PLAN"]])
        else:
            st.warning("No data for this date.")

if __name__ == "__main__":
    main()
