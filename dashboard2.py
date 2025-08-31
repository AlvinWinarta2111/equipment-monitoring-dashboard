import streamlit as st
import pandas as pd

# =========================
# Flexible score mappings
# =========================
SCORE_MAPPINGS = {
    "VIBRATION": {
        "acceptable": 3, "excellent": 3, "ok": 3,
        "requires evaluation": 2,
        "unacceptable": 1,
        "not applicable": None
    },
    "OIL ANALYSIS": {
        "no action required": 3, "ok": 3,
        "monitor compartment": 2, "need action": 2,
        "urgent action required": 1,
        "not applicable": None
    },
    "TEMPERATURE": {
        "good": 3,
        "warning": 2,
        "unacceptable": 1,
        "not applicable": None
    },
    "OTHER INSPECTION": {
        "good": 3,
        "alert": 2,
        "need action": 1,
        "not applicable": None
    }
}


def map_score(value, category):
    """Convert category text into numeric score (case-insensitive)."""
    if pd.isna(value):
        return None
    return SCORE_MAPPINGS[category].get(str(value).strip().lower(), None)


def aggregate_score(row):
    """Lowest score among Vibration, Oil, Temp, Inspection becomes the score."""
    subs = [
        row["VIBRATION_SCORE"],
        row["OIL_SCORE"],
        row["TEMP_SCORE"],
        row["OTHER_SCORE"],
    ]
    subs = [s for s in subs if s is not None]
    return min(subs) if subs else None


def color_score(val):
    """Return color style for score values."""
    if val == 1:
        return "background-color: red; color: white;"
    elif val == 2:
        return "background-color: yellow; color: black;"
    elif val == 3:
        return "background-color: green; color: white;"
    return ""


def main():
    st.title("📊 Condition Monitoring Dashboard")

    uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
    if not uploaded_file:
        st.info("Please upload a file to continue.")
        return

    # Load data
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Scorecard", header=1)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return

    # Rename based on your given cell positions
    column_mapping = {
        "AREA": "AREA",
        "SYSTEM": "SYSTEM",
        "EQUIPMENT DESCRIPTION": "EQUIPMENT DESCRIPTION",
        "DATE": "DATE",
        "CONDITION MONITORING SCORE": "CONDITION MONITORING SCORE",
        "VIBRATION": "VIBRATION",
        "OIL ANALYSIS": "OIL ANALYSIS",
        "TEMPERATURE": "TEMPERATURE",
        "OTHER INSPECTION": "OTHER INSPECTION"
    }
    df = df.rename(columns=column_mapping)

    # Parse date
    df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")

    # Map scores
    df["VIBRATION_SCORE"] = df["VIBRATION"].apply(lambda x: map_score(x, "VIBRATION"))
    df["OIL_SCORE"] = df["OIL ANALYSIS"].apply(lambda x: map_score(x, "OIL ANALYSIS"))
    df["TEMP_SCORE"] = df["TEMPERATURE"].apply(lambda x: map_score(x, "TEMPERATURE"))
    df["OTHER_SCORE"] = df["OTHER INSPECTION"].apply(lambda x: map_score(x, "OTHER INSPECTION"))

    # Aggregate equipment score
    df["CALCULATED_SCORE"] = df.apply(aggregate_score, axis=1)

    # Date filter
    min_date, max_date = df["DATE"].min(), df["DATE"].max()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        df = df[(df["DATE"] >= pd.to_datetime(date_range[0])) &
                (df["DATE"] <= pd.to_datetime(date_range[1]))]

    # Hierarchical aggregation
    system_scores = df.groupby(["AREA", "SYSTEM"])["CALCULATED_SCORE"].min().reset_index()
    area_scores = system_scores.groupby("AREA")["CALCULATED_SCORE"].min().reset_index()

    st.subheader("📍 Area Status")
    st.dataframe(area_scores.style.applymap(color_score, subset=["CALCULATED_SCORE"]))

    st.subheader("🛠 System Status")
    st.dataframe(system_scores.style.applymap(color_score, subset=["CALCULATED_SCORE"]))

    st.subheader("🔎 Equipment Details")
    st.dataframe(df[[
        "AREA", "SYSTEM", "EQUIPMENT DESCRIPTION", "DATE",
        "VIBRATION", "OIL ANALYSIS", "TEMPERATURE", "OTHER INSPECTION",
        "CALCULATED_SCORE"
    ]].style.applymap(color_score, subset=["CALCULATED_SCORE"]))


if __name__ == "__main__":
    main()
