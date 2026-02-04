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
    df["Nombre"] = df["Nombre"].astype(str)
    df["Estado"] = pd.to_numeric(df["Estado"], errors="coerce").fillna(0.0).astype(float)
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
    # proporcional al máximo (igual que tu lógica original)
    pct = 0.0 if maximo == 0 else max(0.0, min(estado / maximo, 1.0))
    width = int(pct * 100)

    if estado > 0:
        color = "#22c55e"
    elif estado < 0:
        color = "#ef4444"
    else:
        color = "#9ca3af"

    return f"""
    <div style="width:180px;height:14px;border:1px solid #d1d5db;border-radius:4px;background:#fff;">
      <div style="width:{width}%;height:100%;background:{color};border-radius:4px;"></div>
    </div>
    """


# ---------- START ----------
init_db()

st.title("Dashboard Proporcional (SQLite)")

t1, t2, t3 = st.columns([1.2, 1.6, 4])
with t1:
    if st.button("🔄 Recargar", use_container_width=True):
        st.rerun()
with t2:
    if st.button("🧽 Reset (todo en 0)", use_container_width=True):
        reset_all()
        st.rerun()
with t3:
    st.caption(f"Base de datos: {DB}")

st.divider()

df = cargar_df()
maximo = float(df["Estado"].max()) if len(df) else 0.0

# encabezados
h = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])
h[0].markdown("**Nombre**")
h[1].markdown("**Estado**")
h[2].markdown("**Barra**")
h[3].markdown("**Sumar / restar**")
h[4].markdown("**Aplicar**")
h[5].markdown("**Borrar**")

st.write("")

# filas
for _, row in df.iterrows():
    nombre = row["Nombre"]
    estado = float(row["Estado"])

    c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])

    c1.write(nombre)

    color_num = "#16a34a" if estado > 0 else "#dc2626" if estado < 0 else "#6b7280"
    c2.markdown(
        f"<span style='color:{color_num}; font-weight:700;'>{estado:.2f}</span>",
        unsafe_allow_html=True
    )

    c3.markdown(barra_html(estado, maximo), unsafe_allow_html=True)

    # ✅ number_input: teclado numérico real en iOS
    delta = c4.number_input(
        "",
        value=0.0,
        step=1.0,
        key=f"delta_{nombre}",
        label_visibility="collapsed",
        format="%.2f",
    )

    if c5.button("Aplicar", key=f"ap_{nombre}", use_container_width=True):
        # Si delta=0, no hacemos nada (evita clics accidentales)
        if float(delta) != 0.0:
            upsert_estado(nombre, estado + float(delta))
        st.rerun()

    if c6.button("Borrar", key=f"del_{nombre}", use_container_width=True):
        delete_nombre(nombre)
        st.rerun()

st.divider()

# agregar persona
st.subheader("Agregar persona")
a1, a2, a3 = st.columns([3, 2, 2])
nuevo = a1.text_input("Nombre nuevo", placeholder="Ej: Juan")
estado_ini = a2.number_input("Estado inicial", value=0.0, step=1.0, format="%.2f")

if a3.button("➕ Agregar", use_container_width=True):
    n = (nuevo or "").strip()
    if not n:
        st.warning("Escribe un nombre.")
    else:
        upsert_estado(n, float(estado_ini))
        st.rerun()
