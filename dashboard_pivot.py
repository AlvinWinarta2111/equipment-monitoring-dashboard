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
    
    # Create two columns for side-by-side charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("AREA Score Distribution")
        fig_area = px.bar(
            area_scores, x="AREA", y="SCORE", color=area_scores["SCORE"].astype(str), text="SCORE",
            color_discrete_map={"3": "green", "2": "yellow", "1": "red"}, title="Lowest Score per AREA",
            category_orders={"SCORE": ["3", "2", "1"]}
        )
        fig_area.update_layout(yaxis=dict(title="Score", range=[0, 3.5], dtick=1))
        st.plotly_chart(fig_area, use_container_width=True)

    with col_right:
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
    
    st.subheader("Equipment last checked date")
    # Find the latest check date for each piece of equipment and its system
    latest_check = df.groupby(["EQUIPMENT DESCRIPTION", "SYSTEM"])["DATE"].max().reset_index()
    
    # Sort by date from oldest to latest to find the longest time since checked
    longest_time_not_checked = latest_check.sort_values(by="DATE", ascending=True)

    # Reorder columns and format the date for display
    longest_time_not_checked["DATE"] = longest_time_not_checked["DATE"].dt.strftime("%Y-%m-%d")
    longest_time_not_checked = longest_time_not_checked[["DATE", "EQUIPMENT DESCRIPTION", "SYSTEM"]]
    longest_time_not_checked = longest_time_not_checked.rename(columns={"DATE": "Date (oldest to latest)", "EQUIPMENT DESCRIPTION": "Equipment Name", "SYSTEM": "System"})
    
    st.dataframe(longest_time_not_checked, use_container_width=True, hide_index=True)

    st.subheader("System Status Explorer")
    # Calculate percentages for each system's equipment status
    latest_equipment_status = df_filtered_by_date.sort_values("DATE").groupby(["EQUIPMENT DESCRIPTION", "SYSTEM"])["EQUIP_STATUS"].last().reset_index()
    system_status_counts = latest_equipment_status.groupby("SYSTEM")["EQUIP_STATUS"].value_counts().unstack(fill_value=0)
    system_status_counts["Total"] = system_status_counts.sum(axis=1)

    if "Okay" in system_status_counts.columns:
        system_status_counts["Okay (%)"] = (system_status_counts["Okay"] / system_status_counts["Total"] * 100).round(1)
    else:
        system_status_counts["Okay (%)"] = 0.0

    # Add lowest score to the DataFrame
    system_summary = system_status_counts.reset_index()
    system_summary["Lowest Score"] = df_filtered_by_date.groupby("SYSTEM")["SCORE"].min().reset_index()["SCORE"]

    # Configure AgGrid to display the new columns
    display_cols = ["SYSTEM", "Lowest Score", "Okay (%)"]
    gb = GridOptionsBuilder.from_dataframe(system_summary[display_cols])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(resizable=False, filter=True, sortable=True)

    # Apply color coding to the "Lowest Score" column
    cell_style_jscode = JsCode("""
        function(params) {
            if (params.value === 1) return {'backgroundColor': 'red', 'color': 'white'};
            if (params.value === 2) return {'backgroundColor': 'yellow', 'color': 'black'};
            if (params.value === 3) return {'backgroundColor': 'green', 'color': 'white'};
            return null;
        }""")
    gb.configure_column("Lowest Score", cellStyle=cell_style_jscode)
    
    gridOptions = gb.build()
    gridOptions['suppressMovableColumns'] = True
    grid_response = AgGrid(
        system_summary[display_cols], gridOptions=gridOptions, enable_enterprise_modules=True,
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
        
        detail_display_cols = ["EQUIPMENT DESCRIPTION", "DATE", "SCORE", "STATUS", "VIBRATION", "OIL ANALYSIS", "TEMPERATURE", "OTHER INSPECTION"]
        gb_details = GridOptionsBuilder.from_dataframe(detail_df[detail_display_cols])
        gb_details.configure_selection(selection_mode="single", use_checkbox=False)
        gb_details.configure_default_column(resizable=False)
        gb_details.configure_column("STATUS", cellStyle=cell_style_jscode)
        gridOptions_details = gb_details.build()
        gridOptions_details['suppressMovableColumns'] = True
        detail_grid_response = AgGrid(
            detail_df[detail_display_cols], gridOptions=gridOptions_details, enable_enterprise_modules=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED, fit_columns_on_grid_load=True,
            height=300, theme="streamlit", allow_unsafe_jscode=True
        )

        selected_equipment_rows = detail_grid_response.get("selected_rows", [])
        if isinstance(selected_equipment_rows, pd.DataFrame):
            selected_equipment_rows = selected_equipment_rows.to_dict("records")
        
        if selected_equipment_rows:
            selected_equip_name = selected_equipment_rows[0].get('EQUIPMENT DESCRIPTION')
            
            st.markdown(f"#### Details for: **{selected_equip_name}**")
            selected_equip_full_details = detail_df[detail_df['EQUIPMENT DESCRIPTION'] == selected_equip_name].iloc[0]
            action_data = [{"EQUIPMENT DESCRIPTION": selected_equip_full_details.get("EQUIPMENT DESCRIPTION"), "REPORTED BY": selected_equip_full_details.get("REPORTED BY"), "FINDING": selected_equip_full_details.get("FINDING"), "ACTION PLAN": selected_equip_full_details.get("ACTION PLAN"), "PART NEEDED": selected_equip_full_details.get("PART NEEDED")}]
            action_detail_df = pd.DataFrame(action_data)
            gb_action = GridOptionsBuilder.from_dataframe(action_detail_df)
            gb_action.configure_default_column(wrapText=True, autoHeight=True)
            gridOptions_action = gb_action.build()
            gridOptions_action['domLayout'] = 'autoHeight'
            AgGrid(action_detail_df, gridOptions=gridOptions_action, theme="streamlit", fit_columns_on_grid_load=True, allow_unsafe_jscode=True)
            
            # --- Performance Trend ---
            st.subheader(f"Performance Trend for {selected_equip_name}")
            
            df_equip = df_filtered_by_date[df_filtered_by_date["SYSTEM"] == selected_system].copy()
            if not df_equip.empty:
                idx = df_equip.groupby('DATE')['SCORE'].idxmin()
                aggregated_df = df_equip.loc[idx].reset_index(drop=True)

                fig_trend = px.line(aggregated_df, x="DATE", y="SCORE", markers=True)
                fig_trend.update_xaxes(tickformat="%d/%m/%y", fixedrange=True)
                fig_trend.update_layout(yaxis=dict(title="Score", range=[0.5, 3.5], dtick=1, fixedrange=True))
                
                st.plotly_chart(fig_trend, use_container_width=True)
            
            else:
                st.warning(f"No trend data available for {selected_equip_name} in the selected date range.")

            # --- Historical Records ---
            st.subheader("Historical Records")
            df_hist = df[df["EQUIPMENT DESCRIPTION"] == selected_equip_name].copy()
            df_hist["YEAR"] = df_hist["DATE"].dt.year
            df_hist["MONTH"] = df_hist["DATE"].dt.month
            df_hist["DAY"] = df_hist["DATE"].dt.day

            years = sorted(df_hist["YEAR"].unique())
            year_choice = st.selectbox("Select Year", ["All"] + years)
            if year_choice != "All":
                df_hist = df_hist[df_hist["YEAR"] == year_choice]

                months = sorted(df_hist["MONTH"].unique())
                month_choice = st.selectbox("Select Month", ["All"] + months)
                if month_choice != "All":
                    df_hist = df_hist[df_hist["MONTH"] == month_choice]

                    days = sorted(df_hist["DAY"].unique())
                    day_choice = st.selectbox("Select Day", ["All"] + days)
                    if day_choice != "All":
                        df_hist = df_hist[df_hist["DAY"] == day_choice]

            df_hist = df_hist.sort_values("DATE", ascending=False)
            df_hist["STATUS"] = df_hist["SCORE"].apply(map_status)
            df_hist["DATE"] = df_hist["DATE"].dt.strftime("%d/%m/%Y")

            hist_cols = ["DATE", "SCORE", "STATUS", "FINDING", "ACTION PLAN"]
            gb_hist = GridOptionsBuilder.from_dataframe(df_hist[hist_cols])
            gb_hist.configure_default_column(resizable=True, filter=True, sortable=True, wrapText=True, autoHeight=True)
            gb_hist.configure_column("STATUS", cellStyle=cell_style_jscode)
            gridOptions_hist = gb_hist.build()
            gridOptions_hist['suppressMovableColumns'] = True
            AgGrid(
                df_hist[hist_cols], gridOptions=gridOptions_hist, enable_enterprise_modules=True,
                update_mode=GridUpdateMode.NO_UPDATE, fit_columns_on_grid_load=True,
                height=300, theme="streamlit", allow_unsafe_jscode=True
            )

        else:
            st.info("Select a piece of equipment from the table above to see its latest details.")

    else:
        st.info("Click a system above to see its latest equipment details.")


if __name__ == "__main__":
    main()
