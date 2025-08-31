import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
import requests
import io

# =========================
# Helper functions (for styling and status mapping)
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

# =========================
# Main Streamlit App
# =========================
def main():
    st.set_page_config(layout="wide")
    st.title("📊 Condition Monitoring Dashboard")

    RAW_FILE_URL = "https://raw.githubusercontent.com/AlvinWinarta2111/equipment-monitoring-dashboard/main/data/CONDITION%20MONITORING%20SCORECARD.xlsx"

    @st.cache_data(ttl=300)  # cache for 5 minutes
    def load_data():
        response = requests.get(RAW_FILE_URL)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), sheet_name="Scorecard", header=1)

    # Load data
    try:
        df = load_data()
    except Exception as e:
        st.error(f"Error reading data from GitHub file: {e}")
        return

    # Normalize column names to UPPER
    df.columns = [col.strip().upper() for col in df.columns]

    # Ensure required column exists
    required_score_col = "CONDITION MONITORING SCORE"
    if required_score_col not in df.columns:
        st.error(f"Error: A column named '{required_score_col}' was not found in your file.")
        return

    # Rename and coerce types
    df = df.rename(columns={required_score_col: "SCORE"})
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # Drop rows missing essential fields
    required_subset = ['AREA', 'SYSTEM', 'EQUIPMENT DESCRIPTION', 'DATE', 'SCORE']
    df.dropna(subset=required_subset, inplace=True)

    # Convert SCORE to integer
    df["SCORE"] = df["SCORE"].astype(int)

    # Create text status
    df["EQUIP_STATUS"] = df["SCORE"].apply(map_status)

    # --- FILTERS ---
    min_date, max_date = df["DATE"].min().date(), df["DATE"].max().date()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df_filtered_by_date = df[(df["DATE"].dt.date >= date_range[0]) & (df["DATE"].dt.date <= date_range[1])]
    else:
        df_filtered_by_date = df

    if df_filtered_by_date.empty:
        st.warning("No data available for the selected date range.")
        return

    # --- Aggregation ---
    system_scores = df_filtered_by_date.groupby(["AREA", "SYSTEM"])["SCORE"].min().reset_index()
    area_scores = system_scores.groupby("AREA")["SCORE"].min().reset_index()

    # --- VISUALIZATIONS ---
    st.subheader("AREA Score Distribution")
    fig_area = px.bar(
        area_scores, x="AREA", y="SCORE", color=area_scores["SCORE"].astype(str),
        text="SCORE", color_discrete_map={"3": "green", "2": "yellow", "1": "red"},
        title="Lowest Score per AREA", category_orders={"SCORE": ["3", "2", "1"]}
    )
    fig_area.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1))
    st.plotly_chart(fig_area, use_container_width=True)

    st.subheader("Equipment Status Distribution per AREA")
    latest_for_pie = df_filtered_by_date.sort_values("DATE").groupby("EQUIPMENT DESCRIPTION", as_index=False).last()
    area_dist = latest_for_pie.groupby(["AREA", "EQUIP_STATUS"])["EQUIPMENT DESCRIPTION"].count().reset_index(name="COUNT")
    areas = sorted(area_dist["AREA"].unique())
    cols_per_row = 3
    for i in range(0, len(areas), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, area in enumerate(areas[i:i + cols_per_row]):
            if j < len(cols):
                with cols[j]:
                    st.markdown(f"**{area}**")
                    area_data = area_dist[area_dist["AREA"] == area]
                    fig = px.pie(
                        area_data, names="EQUIP_STATUS", values="COUNT", color="EQUIP_STATUS",
                        color_discrete_map={"Need Action": "red", "Caution": "yellow", "Okay": "green"},
                        hole=0.4, category_orders={"EQUIP_STATUS": ["Okay", "Caution", "Need Action"]}
                    )
                    fig.update_traces(textinfo='percent+value', textfont_size=16)
                    fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)

    st.subheader("SYSTEM Score Distribution")
    fig_system = px.bar(
        system_scores, x="SYSTEM", y="SCORE", color=system_scores["SCORE"].astype(str),
        text="SCORE", color_discrete_map={"3": "green", "2": "yellow", "1": "red"},
        title="Lowest Score per SYSTEM", category_orders={"SCORE": ["3", "2", "1"]}
    )
    fig_system.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1), xaxis=dict(tickangle=-45))
    st.plotly_chart(fig_system, use_container_width=True)

    st.subheader("Area Status (Lowest Score)")
    st.dataframe(area_scores.style.map(color_score, subset=["SCORE"]).hide(axis="index"))

    # --- SYSTEM STATUS EXPLORER ---
    st.subheader("System Status Explorer")
    system_summary = df_filtered_by_date.groupby("SYSTEM").agg({"SCORE": "min"}).reset_index()
    system_summary["STATUS"] = system_summary["SCORE"].apply(map_status)
    gb = GridOptionsBuilder.from_dataframe(system_summary[["SYSTEM", "STATUS", "SCORE"]])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(resizable=False, filter=True, sortable=True)
    cell_style_jscode = JsCode("""
    function(params) {
        if (params.value == 'Okay') { return {'backgroundColor': 'green', 'color': 'white'}; }
        if (params.value == 'Caution') { return {'backgroundColor': 'yellow', 'color': 'black'}; }
        if (params.value == 'Need Action') { return {'backgroundColor': 'red', 'color': 'white'}; }
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
        st.markdown(f"### Equipment Details for **{selected_system}** (Latest Status in Range)")
        detail_df = df_filtered_by_date[df_filtered_by_date["SYSTEM"] == selected_system].copy()
        detail_df = detail_df.sort_values(by="DATE", ascending=False).drop_duplicates(subset=["EQUIPMENT DESCRIPTION"], keep="first")
        detail_df["STATUS"] = detail_df["SCORE"].apply(map_status)
        
        gb_details = GridOptionsBuilder.from_dataframe(detail_df)
        gb_details.configure_selection(selection_mode="single", use_checkbox=False)
        gb_details.configure_default_column(resizable=False)
        gb_details.configure_column("STATUS", cellStyle=cell_style_jscode)
        gridOptions_details = gb_details.build()
        gridOptions_details['suppressMovableColumns'] = True

        detail_grid_response = AgGrid(
            detail_df, gridOptions=gridOptions_details, enable_enterprise_modules=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED, fit_columns_on_grid_load=True,
            height=300, theme="streamlit", allow_unsafe_jscode=True
        )

        # --- NEW: Third-level drilldown for component details ---
        selected_equipment_rows = detail_grid_response.get("selected_rows", [])
        if isinstance(selected_equipment_rows, pd.DataFrame):
            selected_equipment_rows = selected_equipment_rows.to_dict("records")
        
        if selected_equipment_rows:
            selected_equip = selected_equipment_rows[0]
            st.markdown(f"#### Details for: **{selected_equip.get('EQUIPMENT DESCRIPTION')}**")

            # Create component status table
            component_data = {
                "Component": ["Vibration", "Oil Analysis", "Temperature", "Other Inspection"],
                "Status": [
                    selected_equip.get("VIBRATION"), selected_equip.get("OIL ANALYSIS"),
                    selected_equip.get("TEMPERATURE"), selected_equip.get("OTHER INSPECTION")
                ]
            }
            component_df = pd.DataFrame(component_data)
            st.table(component_df.set_index("Component"))

            # Display details in separate expandable sections
            with st.expander("Show Finding, Action Plan, and Parts Needed"):
                st.markdown("**Finding:**")
                st.info(selected_equip.get("FINDING", "N/A"))
                st.markdown("**Action Plan:**")
                st.info(selected_equip.get("ACTION PLAN", "N/A"))
                st.markdown("**Part Needed:**")
                st.info(selected_equip.get("PART NEEDED", "N/A"))

        # --- Performance Trend ---
        st.subheader(f"Performance Trend for {selected_system}")
        trend_df = df_filtered_by_date.groupby(['DATE', 'SYSTEM'])['SCORE'].min().reset_index()
        trend_df_filtered = trend_df[trend_df["SYSTEM"] == selected_system]
        if not trend_df_filtered.empty:
            fig_trend = px.line(
                trend_df_filtered, x="DATE", y="SCORE", markers=True,
                title=f"Performance Trend for {selected_system}"
            )
            fig_trend.update_xaxes(tickformat="%d/%m/%y", fixedrange=True)
            fig_trend.update_layout(yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1, fixedrange=True))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning(f"No trend data available for {selected_system} in the selected date range.")
    else:
        st.info("Click a system above to see its latest equipment details and performance trend.")

if __name__ == "__main__":
    main()

