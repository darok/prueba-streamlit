import streamlit as st
import pandas as pd

st.title("Analizador de datos")

archivo = st.file_uploader("Subí un archivo CSV o Excel", type=["csv", "xlsx"])

if archivo:
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        df = pd.read_excel(archivo)
    
    st.write("Vista previa:")
    st.dataframe(df)
    
    st.write("Estadísticas básicas:")
    st.write(df.describe())