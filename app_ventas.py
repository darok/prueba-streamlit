import streamlit as st
import sqlite3
import pandas as pd

def get_conn():
    return sqlite3.connect("ventas.db")

# ---- PESTAÑAS ----
tab1, tab2 = st.tabs(["📋 Cargar venta", "📊 Ver registros"])

# ---- PESTAÑA 1: CARGAR VENTA ----
with tab1:
    st.header("Cargar nueva venta")
    
    conn = get_conn()
    vendedores = pd.read_sql("SELECT * FROM vendedores", conn)
    productos = pd.read_sql("SELECT * FROM productos", conn)
    conn.close()

    vendedor = st.selectbox("Vendedor", vendedores["nombre"])
    producto = st.selectbox("Producto", productos["nombre"])
    cantidad = st.number_input("Cantidad", min_value=1, value=1)
    fecha = st.date_input("Fecha")

    if st.button("Guardar venta"):
        conn = get_conn()
        vid = vendedores[vendedores["nombre"] == vendedor]["id"].values[0]
        pid = productos[productos["nombre"] == producto]["id"].values[0]
        conn.execute("INSERT INTO ventas (vendedor_id, producto_id, cantidad, fecha) VALUES (?, ?, ?, ?)",
                     (int(vid), int(pid), cantidad, str(fecha)))
        conn.commit()
        conn.close()
        st.success("Venta guardada!")

# ---- PESTAÑA 2: VER REGISTROS ----
with tab2:
    st.header("Registros de ventas")

    conn = get_conn()
    df = pd.read_sql("""
        SELECT v.fecha, ve.nombre as vendedor, p.nombre as producto, 
               v.cantidad, p.precio, (v.cantidad * p.precio) as total
        FROM ventas v
        JOIN vendedores ve ON v.vendedor_id = ve.id
        JOIN productos p ON v.producto_id = p.id
        ORDER BY v.fecha DESC
    """, conn)
    conn.close()

    if df.empty:
        st.info("No hay ventas cargadas todavía.")
    else:
        st.subheader("Todas las ventas")
        st.dataframe(df)

        df["fecha"] = pd.to_datetime(df["fecha"])
        df["mes"] = df["fecha"].dt.to_period("M").astype(str)
        df["año"] = df["fecha"].dt.year

        st.subheader("Agregado mensual")
        st.dataframe(df.groupby("mes")["total"].sum().reset_index())

        st.subheader("Agregado anual")
        st.dataframe(df.groupby("año")["total"].sum().reset_index())