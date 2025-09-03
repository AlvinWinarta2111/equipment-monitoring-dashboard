import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------
# Load Excel Data
# ---------------------------
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name="scorecard")

    # Rename and clean columns
    df = df.rename(columns={"CONDITION MONITORING SCORE": "SCORE"})
    df["SCORE"] = pd.to_numeric(df["SCORE"], errors="coerce")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # Drop rows with missing critical values
    df = df.dropna(subset=["DATE", "EQUIPMENT", "SCORE"])

    # Add date components for filtering
    df["YEAR"] = df["DATE"].dt.year
    df["MONTH"] = df["DATE"].dt.month
    df["DAY"] = df["DATE"].dt.day
    df["DATE_ONLY"] = df["DATE"].dt.strftime("%d/%m/%Y")

    return df


# ---------------------------
# Main App
# ---------------------------
def main():
    st.set_page_config(page_title="📊 Condition Monitoring Scorecard Dashboard", layout="wide")

    st.title("📊 Condition Monitoring Scorecard Dashboard")

    uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])
    if uploaded_file is None:
        st.warning("Please upload the scorecard Excel file.")
        return

    df = load_data(uploaded_file)

    # Sidebar - Equipment selection
    st.sidebar.header("Filter Options")
    equipment_list = df["EQUIPMENT"].unique()
    selected_equipment = st.sidebar.selectbox("Select Equipment", equipment_list)

    df_equip = df[df["EQUIPMENT"] == selected_equipment]

    # ---------------------------
    # Trendline
    # ---------------------------
    st.subheader(f"Trendline for {selected_equipment}")
    fig_trend = px.scatter(
        df_equip,
        x="DATE",
        y="SCORE",
        title=f"Condition Monitoring Trend - {selected_equipment}",
        labels={"SCORE": "Condition Monitoring Score", "DATE": "Date"},
        markers=True,
    )
    fig_trend.update_traces(marker=dict(size=10, color="skyblue"))
    fig_trend.update_layout(xaxis_title="Date", yaxis_title="Score")
    st.plotly_chart(fig_trend, use_container_width=True)

    # ---------------------------
    # Historical Records with Hierarchical Date Filter
    # ---------------------------
    st.subheader("Historical Records")

    # Step 1: Year filter
    years = sorted(df_equip["YEAR"].dropna().unique())
    selected_year = st.selectbox("Select Year", years)

    df_year = df_equip[df_equip["YEAR"] == selected_year]

    # Step 2: Month filter (depends on year)
    months = sorted(df_year["MONTH"].dropna().unique())
    month_names = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
                   7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
    month_display = [month_names[m] for m in months]
    selected_month_name = st.selectbox("Select Month", month_display)
    selected_month = [k for k,v in month_names.items() if v == selected_month_name][0]

    df_month = df_year[df_year["MONTH"] == selected_month]

    # Step 3: Day filter (depends on year + month)
    days = sorted(df_month["DAY"].dropna().unique())
    selected_day = st.selectbox("Select Day", days)

    df_filtered = df_month[df_month["DAY"] == selected_day]

    # Show filtered table
    st.dataframe(
        df_filtered[["DATE_ONLY", "SCORE", "STATUS", "FINDING", "ACTION PLAN"]]
        .sort_values(by="DATE_ONLY", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
