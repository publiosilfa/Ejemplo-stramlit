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

def cargar_df() -> pd.DataFrame:
    with conn_db() as conn:
        df = pd.read_sql_query(
            "SELECT nombre AS Nombre, estado AS Estado FROM estados",
            conn
        )
    if df.empty:
        df = pd.DataFrame(columns=["Nombre", "Estado"])
    df["Nombre"] = df["Nombre"].astype(str)
    df["Estado"] = pd.to_numeric(df["Estado"], errors="coerce").fillna(0.0).astype(float)
    df = df.sort_values(by="Estado", ascending=False).reset_index(drop=True)
    return df

def upsert_estado(nombre: str, estado: float):
    with conn_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO estados (nombre, estado)
        VALUES (?, ?)
        ON CONFLICT(nombre) DO UPDATE SET estado=excluded.estado
        """, (nombre, float(estado)))
        conn.commit()

def delete_nombre(nombre: str):
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
def barra_html(estado: float, maximo: float) -> str:
    # Proporcional al máximo (como tu app)
    pct = 0.0 if maximo == 0 else max(0.0, min(estado / maximo, 1.0))
    width = int(pct * 100)

    if estado > 0:
        color = "#22c55e"  # verde
    elif estado < 0:
        color = "#ef4444"  # rojo
    else:
        color = "#9ca3af"  # gris

    return f"""
    <div style="width: 180px; height: 14px; border: 1px solid #d1d5db;
                border-radius: 4px; background: #ffffff;">
      <div style="width: {width}%; height: 100%; background: {color};
                  border-radius: 4px;"></div>
    </div>
    """


# ---------- Start ----------
init_db()

st.title("Dashboard Proporcional (SQLite)")

top1, top2, top3 = st.columns([1.2, 1.2, 4])
with top1:
    if st.button("🔄 Recargar", use_container_width=True):
        st.rerun()
with top2:
    if st.button("🧽 Reset (poner todo en 0)", use_container_width=True):
        reset_all()
        st.success("Listo: todos los estados se pusieron en 0.")
        st.rerun()
with top3:
    st.caption(f"Base de datos: {DB}")

st.divider()

df = cargar_df()
maximo = float(df["Estado"].max()) if len(df) else 0.0

# Encabezados
h = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])
h[0].markdown("**Nombre**")
h[1].markdown("**Estado**")
h[2].markdown("**Barra**")
h[3].markdown("**Sumar / restar**")
h[4].markdown("**Aplicar**")
h[5].markdown("**Borrar**")

st.write("")

for i in range(len(df)):
    nombre = df.at[i, "Nombre"]
    estado = float(df.at[i, "Estado"])

    c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])

    c1.write(nombre)

    if estado > 0:
        c2.markdown(
            f"<span style='color:#16a34a; font-weight:700;'>{estado:.2f}</span>",
            unsafe_allow_html=True
        )
    elif estado < 0:
        c2.markdown(
            f"<span style='color:#dc2626; font-weight:700;'>{estado:.2f}</span>",
            unsafe_allow_html=True
        )
    else:
        c2.markdown(
            f"<span style='color:#6b7280; font-weight:700;'>{estado:.2f}</span>",
            unsafe_allow_html=True
        )

    c3.markdown(barra_html(estado, maximo), unsafe_allow_html=True)

    key_in = f"delta_{nombre}"
    delta_txt = c4.text_input(
        "",
        value="",
        placeholder="+0",
        key=key_in,
        label_visibility="collapsed",
    )

    if c5.button("Aplicar", key=f"ap_{nombre}", use_container_width=True):
        # ✅ FIX iOS/Safari: limpia espacios raros y acepta coma decimal
        txt = (delta_txt or "").strip().replace(",", ".")
        if not txt:
            st.warning("Pon un número antes de aplicar.")
        else:
            try:
                valor = float(txt)
                nuevo_estado = estado + valor
                upsert_estado(nombre, nuevo_estado)
                st.session_state[key_in] = ""
                st.rerun()
            except ValueError:
                st.error("Entrada inválida. Usa: 10, -5, 3.5, etc.")

    if c6.button("Borrar", key=f"del_{nombre}", use_container_width=True):
        delete_nombre(nombre)
        st.rerun()

st.divider()

st.subheader("Agregar persona")
a1, a2, a3 = st.columns([3, 2, 2])
nuevo = a1.text_input("Nombre nuevo", placeholder="Ej: Juan")
estado_ini = a2.number_input("Estado inicial", value=0.0, step=1.0)

if a3.button("➕ Agregar", use_container_width=True):
    n = (nuevo or "").strip()
    if not n:
        st.warning("Escribe un nombre.")
    else:
        # Si ya existe, lo actualiza
        upsert_estado(n, float(estado_ini))
        st.rerun()
