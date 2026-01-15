"""
Aplicación Streamlit para procesar ausencias sin soporte.
Frontend limpio y organizado.
"""
import streamlit as st
from io import BytesIO
from processor import AusenciasProcessor


# =========================
# Configuración
# =========================
st.set_page_config(page_title="Ausencias sin soporte", layout="wide")


# =========================
# Session State
# =========================
def init_state():
    """Inicializa el estado de la sesión."""
    defaults = {
        "ready": False,
        "excel_bytes": None,
        "file_name": None,
        "aus_sin_out": None,
        "summary": None,
        "params": None,
        "logs": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# =========================
# UI Principal
# =========================
st.title("📌 Ausencias sin soporte (TS + Ausentismos + SAP + Retiros + MasterData)")

with st.sidebar:
    st.header("⚙️ Controles")
    show_debug = st.checkbox("Mostrar diagnóstico (logs)", value=False)

    if st.button("🧹 Limpiar resultados"):
        st.session_state.ready = False
        st.session_state.excel_bytes = None
        st.session_state.file_name = None
        st.session_state.aus_sin_out = None
        st.session_state.summary = None
        st.session_state.params = None
        st.session_state.logs = []
        st.rerun()

with st.expander("📘 Instructivo", expanded=True):
    st.markdown(
        """
1) Carga los 6 archivos.
2) Selecciona el periodo (inicio y fin).
3) Clic en **Generar consolidado**.
4) Descarga el Excel consolidado (no se pierde al descargar).

**Reglas:**
- Retiro = `Desde - 1 día` (Retiros)
- Ingreso = MasterData donde `Clase de fecha` contiene "alta"
- Activos: solo IDs con `Función` autorizada en `funciones_marcación`
- MasterData ID: **N° pers. / Nº pers.**
"""
    )

# =========================
# Formulario de carga
# =========================
with st.form("main_form", clear_on_submit=False):
    c1, c2 = st.columns(2)

    with c1:
        f_horas = st.file_uploader("📄 Rep_Horas_laboradas.xlsx", type=["xlsx"])
        f_ausrep = st.file_uploader("📄 Rep_aususentismos.xlsx", type=["xlsx"])
        f_retiros = st.file_uploader("📄 Retiros.xlsx", type=["xlsx"])

    with c2:
        f_md = st.file_uploader("📄 Md_activos.xlsx", type=["xlsx"])
        f_func = st.file_uploader("📄 funciones_marcación.xlsx", type=["xlsx"])
        f_aussap = st.file_uploader("📄 Ausentismos_SAP (XLS / XLSX)", type=["xls", "xlsx"])

    d1, d2 = st.columns(2)
    with d1:
        fecha_inicio = st.date_input("Fecha inicio del periodo")
    with d2:
        fecha_fin = st.date_input("Fecha fin del periodo")

    run = st.form_submit_button("🚀 Generar consolidado")


# =========================
# Procesamiento
# =========================
if run:
    st.session_state.logs = []

    # Validaciones
    if not all([f_horas, f_ausrep, f_retiros, f_md, f_func, f_aussap]):
        st.error("Debes cargar los 6 archivos.")
        st.stop()

    if fecha_fin < fecha_inicio:
        st.error("La fecha fin no puede ser menor que la fecha inicio.")
        st.stop()

    with st.spinner("Procesando..."):
        # Preparar archivos
        files = {
            'horas': {'bytes': f_horas.read(), 'name': f_horas.name},
            'ausrep': {'bytes': f_ausrep.read(), 'name': f_ausrep.name},
            'retiros': {'bytes': f_retiros.read(), 'name': f_retiros.name},
            'md': {'bytes': f_md.read(), 'name': f_md.name},
            'func': {'bytes': f_func.read(), 'name': f_func.name},
            'aussap': {'bytes': f_aussap.read(), 'name': (f_aussap.name or "").lower()},
        }

        # Procesar
        processor = AusenciasProcessor(fecha_inicio, fecha_fin)
        result = processor.process(files)

        if result is None:
            st.error("Error en el procesamiento. Revisa los logs.")
            st.session_state.logs = processor.logs
            if show_debug:
                st.info("\n".join(st.session_state.logs))
            st.stop()

        # Guardar resultados
        st.session_state.excel_bytes = result['excel_bytes']
        st.session_state.file_name = result['file_name']
        st.session_state.aus_sin_out = result['dfs']['Ausencias_sin_soporte']
        st.session_state.summary = result['dfs']['Resumen_periodo']
        st.session_state.params = result['dfs']['Parametros']
        st.session_state.logs = result['logs']
        st.session_state.ready = True


# =========================
# Resultados (persistentes)
# =========================
if st.session_state.ready:
    st.success("Listo ✅. Ya puedes revisar y descargar (no se pierde al descargar).")

    tabs = st.tabs(["📄 Detalle", "📊 Resumen", "⚙️ Parámetros", "🧾 Diagnóstico"])

    with tabs[0]:
        st.dataframe(st.session_state.aus_sin_out, use_container_width=True, height=520)

    with tabs[1]:
        st.dataframe(st.session_state.summary, use_container_width=True, height=520)

    with tabs[2]:
        st.dataframe(st.session_state.params, use_container_width=True, height=240)

    with tabs[3]:
        st.write("\n".join(st.session_state.logs) if st.session_state.logs else "Sin logs.")
        st.caption("En Parámetros, 'MD_id_col_usada' debe quedar como N° pers. / Nº pers.")
        if show_debug:
            st.info("\n".join(st.session_state.logs))

    st.download_button(
        label="⬇️ Descargar Excel consolidado",
        data=st.session_state.excel_bytes,
        file_name=st.session_state.file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_excel_fixed",
    )
else:
    st.info("Carga archivos, selecciona el periodo y presiona **Generar consolidado**.")


# =========================
# Footer
# =========================
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px 0;'>
        <p style='margin: 0; font-size: 14px;'>
            Creado por <b>Nómina Data Analytics</b><br>
            Jerónimo Martins © 2026
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
