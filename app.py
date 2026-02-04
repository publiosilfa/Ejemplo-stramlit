import sqlite3
import pandas as pd
import streamlit as st

DB = "estadoshp.db"

st.set_page_config(page_title="Dashboard Proporcional", layout="wide")

# =======================
# BASE DE DATOS (SQLite)
# =======================

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

def reemplazar_todo(df_edit: pd.DataFrame):
    df_edit = df_edit.copy()
    df_edit["Nombre"] = df_edit["Nombre"].astype(str).str.strip()
    df_edit["Estado"] = pd.to_numeric(df_edit["Estado"], errors="coerce").fillna(0.0)
    df_edit = df_edit[df_edit["Nombre"] != ""]
    df_edit = df_edit.drop_duplicates(subset=["Nombre"], keep="last")

    with conn_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM estados")
        cur.executemany(
            "INSERT INTO estados (nombre, estado) VALUES (?, ?)",
            list(df_edit[["Nombre", "Estado"]].itertuples(index=False, name=None))
        )
        conn.commit()

# =======================
# UI helpers
# =======================

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
    <div style="width:180px;height:14px;border:1px solid #d1d5db;border-radius:4px;background:#fff;">
      <div style="width:{width}%;height:100%;background:{color};border-radius:4px;"></div>
    </div>
    """

# =======================
# APP
# =======================

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

# ---- Ver / editar base completa ----
with st.expander("🗄️ Editar base completa (SQLite)"):
    df_edit = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True
    )
    if st.button("💾 Guardar edición en la base", use_container_width=True):
        reemplazar_todo(df_edit)
        st.success("Base actualizada correctamente.")
        st.rerun()

maximo = df["Estado"].max() if len(df) else 0

# ---- Encabezados ----
h = st.columns([2.2, 1.2, 2.2, 2.2, 1.2, 1.2])
h[0].markdown("**Nombre**")
h[1].markdown("**Estado**")
h[2].markdown("**Barra**")
h[3].markdown("**Sumar / restar**")
h[4].markdown("**Aplicar**")
h[5].markdown("**Borrar**")

st.write("")

# ---- Filas ----
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

    # ✅ FORM: el input se limpia automáticamente al aplicar
    with c4.form(key=f"form_{nombre}", clear_on_submit=True):
        delta = st.number_input(
            "",
            value=0.0,
            step=1.0,
            format="%.2f",
            label_visibility="collapsed",
        )
        aplicar = st.form_submit_button("Aplicar")

    if aplicar:
        if float(delta) != 0.0:
            upsert_estado(nombre, estado + float(delta))
        st.rerun()

    if c6.button("Borrar", key=f"del_{nombre}", use_container_width=True):
        delete_nombre(nombre)
        st.rerun()

st.divider()

# ---- Agregar persona ----
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
