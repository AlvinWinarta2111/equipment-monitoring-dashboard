import streamlit as st
import pandas as pd

st.title("Data Editor (Streamlit 1.49.0)")

df = pd.DataFrame({
    "System": ["Pump", "Compressor", "Conveyor", "Boiler"],
    "Score": [85, 67, 72, 90],
    "Status": ["Good", "Alert", "Alert", "Good"]
})

# ✅ Minimal arguments only (works in 1.49.0)
edited = st.data_editor(df, key="editor")

st.write("Edited dataframe:", edited)
