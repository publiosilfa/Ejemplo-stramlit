import os
import pandas as pd
import streamlit as st

ARCHIVO = "estadoshp.csv"

st.set_page_config(page_title="Dashboard Proporcional", layout="wide")

# ---------- Utilidades ----------
def cargar_df() -> pd.DataFrame:
    if os.path.exists(ARCHIVO):
        df = pd.read_csv(ARCHIVO)
        if "Nombre" not in df.columns:
            df["Nombre"] = df.index.astype(str)
        if "Estado" not in df.columns:
            df["Estado"] = 0.0
    else:
        df = pd.DataFrame(columns=["Nombre", "Estado"])
    df["Nombre"] = df["Nombre"].astype(str)
    df["Estado"] = pd.to_numeric(df["Estado"], errors="coerce").fillna(0.0).astype(float)
    return df

def ordenar(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(by="Estado", ascending=False).reset_index(drop=True)

def guardar_df(df: pd.DataFrame) -> None:
    ordenar(df).to_csv(ARCHIVO, index=False)

def barra_html(estado: float, maximo: float) -> str:
    # Evita división por cero
    pct = 0.0 if maximo == 0 else max(0.0, min(estado / maximo, 1.0))
    width = int(pct * 100)

    if estado > 0:
        color = "#22c55e"  # verde
    elif estado < 0:
        color = "#ef4444"  # rojo
    else:
        color = "#9ca3af"  # gris

    return f"""
    <div style="width: 160px; height: 14px; border: 1px solid #d1d5db; border-radius: 4px; background: #ffffff;">
      <div style="width: {width}%; height: 100%; background: {color}; border-radius: 4px;"></div>
    </div>
    """

# ---------- Estado (session) ----------
if "df" not in st.session_state:
    st.session_state.df = ordenar(cargar_df())

st.title("Dashboard Proporcional")

colA, colB, colC = st.columns([1, 1, 4])
with colA:
    if st.button("💾 Guardar cambios", use_container_width=True):
        guardar_df(st.session_state.df)
        st.success("Guardado. Cambios guardados correctamente.")

with colB:
    if st.button("🔄 Recargar desde CSV", use_container_width=True):
        st.session_state.df = ordenar(cargar_df())
        st.info("Recargado desde el archivo.")

with colC:
    st.caption(f"Archivo: {ARCHIVO}")

st.divider()

df = st.session_state.df
maximo = df["Estado"].max() if len(df) else 0.0

# ---------- Tabla “a mano” para tener inputs por fila ----------
header = st.columns([2.2, 1.2, 2.2, 2.2, 1.8])
header[0].markdown("**Nombre**")
header[1].markdown("**Estado**")
header[2].markdown("**Barra**")
header[3].markdown("**Sumar / restar**")
header[4].markdown("**Acción**")

st.write("")

for i in range(len(df)):
    nombre = df.at[i, "Nombre"]
    estado = float(df.at[i, "Estado"])

    c1, c2, c3, c4, c5 = st.columns([2.2, 1.2, 2.2, 2.2, 1.8])

    c1.write(nombre)

    # Color del número
    if estado > 0:
        c2.markdown(f"<span style='color:#16a34a; font-weight:700;'>{estado:.2f}</span>", unsafe_allow_html=True)
    elif estado < 0:
        c2.markdown(f"<span style='color:#dc2626; font-weight:700;'>{estado:.2f}</span>", unsafe_allow_html=True)
    else:
        c2.markdown(f"<span style='color:#6b7280; font-weight:700;'>{estado:.2f}</span>", unsafe_allow_html=True)

    c3.markdown(barra_html(estado, maximo), unsafe_allow_html=True)

    # Entrada por fila (key única)
    key_in = f"delta_{i}"
    delta_txt = c4.text_input("",
                             value="",
                             placeholder="+0",
                             key=key_in,
                             label_visibility="collapsed")

    if c5.button("Aplicar", key=f"btn_{i}", use_container_width=True):
        txt = (delta_txt or "").strip()
        if not txt:
            st.warning("Pon un número antes de aplicar.")
        else:
            try:
                valor = float(txt)
                st.session_state.df.at[i, "Estado"] = float(st.session_state.df.at[i, "Estado"]) + valor
                st.session_state.df = ordenar(st.session_state.df)
 #               st.session_state[key_in] = ""  # limpia el input
                st.rerun()
            except ValueError:
                st.error("Entrada inválida. Usa algo como 10, -5, 3.5")

st.divider()

# ---------- (Opcional) Agregar nuevo nombre ----------
st.subheader("Agregar persona")
cN1, cN2, cN3 = st.columns([3, 2, 2])
nuevo = cN1.text_input("Nombre nuevo", placeholder="Ej: Juan")
estado_ini = cN2.number_input("Estado inicial", value=0.0, step=1.0)

if cN3.button("➕ Agregar", use_container_width=True):
    nuevo = (nuevo or "").strip()
    if not nuevo:
        st.warning("Escribe un nombre.")
    else:
        st.session_state.df = pd.concat(
            [st.session_state.df, pd.DataFrame([{"Nombre": nuevo, "Estado": float(estado_ini)}])],
            ignore_index=True
        )
        st.session_state.df = ordenar(st.session_state.df)
        st.rerun()
