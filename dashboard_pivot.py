import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_plotly_events import plotly_events

# =========================
# LOAD DATA
# =========================
df = pd.read_csv("your_data.csv")

# Ensure DATE column is datetime
df["DATE"] = pd.to_datetime(df["DATE"])

# =========================
# FILTER DATA BY LATEST DATE
# =========================
latest_date = df["DATE"].max()
df_filtered_by_date = df[df["DATE"] == latest_date]

# =========================
# GRID DISPLAY
# =========================
st.subheader("Equipment Status Table")

gb = GridOptionsBuilder.from_dataframe(df_filtered_by_date)
gb.configure_selection(selection_mode="single", use_checkbox=True)
grid_options = gb.build()

grid_response = AgGrid(
    df_filtered_by_date,
    gridOptions=grid_options,
    height=300,
    fit_columns_on_grid_load=True,
)

selected = grid_response["selected_rows"]

# =========================
# TRENDLINE SECTION
# =========================
if selected:
    selected_equip_name = selected[0]["EQUIPMENT DESCRIPTION"]

    st.subheader(f"Trendline for {selected_equip_name}")

    # 1. Filter data for the selected equipment
    trend_df_filtered = df[
        df["EQUIPMENT DESCRIPTION"] == selected_equip_name
    ].copy()

    # 2. Group by DATE, get the minimum score per date
    trend_df_filtered = (
        trend_df_filtered.groupby("DATE")["SCORE"].min().reset_index()
    )

    # =============================
    # TOP: Non-Clickable Trendline
    # =============================
    st.markdown("### 📊 Overall Trend (Non-Clickable)")
    fig_trend_static = px.line(trend_df_filtered, x="DATE", y="SCORE", markers=True)
    st.plotly_chart(fig_trend_static, use_container_width=True)

    # =============================
    # BOTTOM: Clickable Trendline
    # =============================
    st.markdown("### 🖱️ Drilldown Trend (Clickable)")
    fig_trend_click = px.line(trend_df_filtered, x="DATE", y="SCORE", markers=True)
    selected_points = plotly_events(
        fig_trend_click,
        click_event=True,
        key=f"trend_chart_click_{selected_equip_name}"
    )

    # If user clicks a point, show details
    if selected_points:
        clicked_idx = selected_points[0]["pointIndex"]
        clicked_date = trend_df_filtered.iloc[clicked_idx]["DATE"]

        st.markdown(f"**You clicked on date: {clicked_date.date()}**")

        # Show all equipment data for that date
        clicked_day_data = df[df["DATE"] == clicked_date]
        st.dataframe(clicked_day_data)

else:
    st.info("Please select an equipment from the table above to see its trendline.")
