import sqlite3

conn = sqlite3.connect("ventas.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS vendedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendedor_id INTEGER,
    producto_id INTEGER,
    cantidad INTEGER,
    fecha TEXT,
    FOREIGN KEY (vendedor_id) REFERENCES vendedores(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
)
""")

# Datos de ejemplo
c.executemany("INSERT OR IGNORE INTO vendedores (nombre) VALUES (?)", 
    [("Ana",), ("Luis",), ("María",)])

c.executemany("INSERT OR IGNORE INTO productos (nombre, precio) VALUES (?, ?)", 
    [("Producto A", 1500), ("Producto B", 2300), ("Producto C", 800)])

conn.commit()
conn.close()
print("Base de datos creada!")