import streamlit as st
import sqlite3
import pandas as pd

def get_conn():
    return sqlite3.connect("ventas.db")

# ---- PESTAÑAS ----
tab1, tab2, tab3 = st.tabs(["📋 Cargar venta", "📊 Ver registros", "⚙️ Administrar"])

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

# ---- PESTAÑA 3: ADMINISTRAR ----
with tab3:
    st.header("Administrar vendedores y productos")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Agregar vendedor")
        nuevo_vendedor = st.text_input("Nombre del vendedor", key="nuevo_vendedor")
        if st.button("Agregar vendedor"):
            if nuevo_vendedor.strip():
                conn = get_conn()
                conn.execute("INSERT INTO vendedores (nombre) VALUES (?)", (nuevo_vendedor.strip(),))
                conn.commit()
                conn.close()
                st.success(f"Vendedor '{nuevo_vendedor.strip()}' agregado.")
                st.rerun()
            else:
                st.warning("Ingresá un nombre válido.")

        conn = get_conn()
        df_v = pd.read_sql("SELECT * FROM vendedores ORDER BY nombre", conn)
        conn.close()
        st.dataframe(df_v, hide_index=True)

    with col2:
        st.subheader("Agregar producto")
        nuevo_producto = st.text_input("Nombre del producto", key="nuevo_producto")
        nuevo_precio = st.number_input("Precio", min_value=0.0, value=0.0, step=0.01, key="nuevo_precio")
        if st.button("Agregar producto"):
            if nuevo_producto.strip() and nuevo_precio > 0:
                conn = get_conn()
                conn.execute("INSERT INTO productos (nombre, precio) VALUES (?, ?)", (nuevo_producto.strip(), nuevo_precio))
                conn.commit()
                conn.close()
                st.success(f"Producto '{nuevo_producto.strip()}' agregado.")
                st.rerun()
            else:
                st.warning("Ingresá un nombre y un precio mayor a 0.")

        conn = get_conn()
        df_p = pd.read_sql("SELECT * FROM productos ORDER BY nombre", conn)
        conn.close()
        st.dataframe(df_p, hide_index=True)