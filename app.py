import sqlite3
import pandas as pd
import streamlit as st

DB = "estadoshp.db"

st.set_page_config(page_title="Dashboard Proporcional", layout="wide")

# ---------- DB ----------
def conn_db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with conn_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS estados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            estado REAL NOT NULL DEFAULT 0
        )
        """)
        conn.commit()

def cargar_df():
    with conn_db() as conn:
        df = pd.read_sql_query(
            "SELECT nombre AS Nombre, estado AS Estado FROM estados",
            conn
        )
    if df.empty:
        df = pd.DataFrame(columns=["Nombre", "Estado"])
    df["Estado"] = pd.to_numeric(df["Estado"], errors="coerce").fillna(0.0)
    return df.sort_values(by="Estado", ascending=False).reset_index(drop=True)

def upsert_estado(nombre, estado):
    with conn_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO estados (nombre, estado)
        VALUES (?, ?)
        ON CONFLICT(nombre) DO UPDATE SET estado=excluded.estado
        """, (nombre, float(estado)))
        conn.commit()

def delete_nombre(nombre):
    with conn_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM estados WHERE nombre=?", (nombre,))
        conn.commit()

def reset_all():
    with conn_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE estados SET estado=0")
        conn.commit()

# ---------- UI helpers ----------
def barra_html(estado, maximo):
    pct = 0 if maximo == 0 else max(0, min(estado / maximo, 1))
    width = int(pct * 100)

    if estado > 0:
        color = "#22c55e"
    elif estado < 0:
        color = "#ef4444"
    else:
        color = "#9ca3af"

    return f"""
    <div style="width:180px;height:14px;border:1px solid #d1d5db;border-radius:4px;">
        <div style="width:{width}%;height:100%;background:{color};border-radius:4px;"></div>
    </div>
    """

# ---------- START ----------
init_db()

st.title("Dashboard Proporcional (SQLite)")

c1, c2, c3 = st.columns([1.2, 1.6, 4])
if c1.button("🔄 Recargar"):
    st.rerun()
if c2.button("🧽 Reset (todo en 0)"):
    reset_all()
    st.rerun()
c3.caption(f"Base de datos: {DB}")

st.divider()

df = cargar_df()
maximo = df["Estado"].max() if len(df) else 0

h = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])
h[0].markdown("**Nombre**")
h[1].markdown("**Estado**")
h[2].markdown("**Barra**")
h[3].markdown("**Sumar / restar**")
h[4].markdown("**Aplicar**")
h[5].markdown("**Borrar**")

for _, row in df.iterrows():
    nombre = row["Nombre"]
    estado = float(row["Estado"])

    a, b, c, d, e, f = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])

    a.write(nombre)

    color = "#16a34a" if estado > 0 else "#dc2626" if estado < 0 else "#6b7280"
    b.markdown(f"<b style='color:{color}'>{estado:.2f}</b>", unsafe_allow_html=True)

    c.markdown(barra_html(estado, maximo), unsafe_allow_html=True)

    delta = d.text_input(
        "",
        placeholder="+0",
        key=f"delta_{nombre}",
        label_visibility="collapsed"
    )

    if e.button("Aplicar", key=f"ap_{nombre}"):
        txt = (delta or "").strip().replace(",", ".")
        if txt:
            try:
                upsert_estado(nombre, estado + float(txt))
                st.rerun()
            except ValueError:
                st.error("Entrada inválida. Usa 10, -5, 3.5")

    if f.button("Borrar", key=f"del_{nombre}"):
        delete_nombre(nombre)
        st.rerun()

st.divider()

st.subheader("Agregar persona")
n1, n2, n3 = st.columns([3, 2, 2])
nuevo = n1.text_input("Nombre nuevo")
estado_ini = n2.number_input("Estado inicial", value=0.0)

if n3.button("➕ Agregar"):
    if nuevo.strip():
        upsert_estado(nuevo.strip(), estado_ini)
        st.rerun()
