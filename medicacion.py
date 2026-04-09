import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
from datetime import datetime
import pytz
import pandas as pd

# --- CONFIGURACIÓN ---
TOKEN_TELEGRAM = "8615340270:AAHoE31HRAAAZx7EXYzn-tWLKbwQQDp7Cnk"
URL_APP = "https://tu-app.streamlit.app" # Cambia esto cuando la publiques

# Conexión a la base de datos
conn = st.connection("gsheets", type=GSheetsConnection)

def enviar_telegram(chat_id, mensaje, nombre_med):
    # Añadimos el enlace de confirmación al mensaje
    # Usamos URL segura para que el bot mande el botón de confirmación
    url_confirmar = f"{URL_APP}?check={nombre_med}"
    texto_completo = f"{mensaje}\n\n✅ Confirma aquí: {url_confirmar}"
    
    url_api = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    requests.get(url_api, params={"chat_id": chat_id, "text": texto_completo, "parse_mode": "Markdown"})

# --- LÓGICA DE CONFIRMACIÓN ---
# Si entran a través del enlace de Telegram
query_params = st.query_params
if "check" in query_params:
    med_confirmado = query_params["check"]
    st.balloons()
    st.success(f"¡Gracias! Se ha registrado que has tomado: {med_confirmado}")
    # Aquí podrías añadir una fila a una segunda hoja de "Historial"
    # Por ahora lo mostramos en pantalla para confirmar que funciona
    st.stop() 

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Pastillero Familiar", page_icon="💊")
st.title("💊 Sistema de Control de Medicación")

# Cargar datos de la hoja "Medicamentos"
try:
    df = conn.read(worksheet="Medicamentos", ttl="1m")
except:
    st.error("No se pudo leer la hoja. Revisa el nombre de la pestaña (Medicamentos).")
    st.stop()

# 1. Ajuste de hora local
tz = pytz.timezone("Europe/Madrid")
ahora = datetime.now(tz)
hora_str = ahora.strftime("%H:%M")

st.sidebar.metric("Hora Actual", hora_str)

# 2. PROCESO DE ENVÍO AUTOMÁTICO (Cada vez que el Cron-Job visita la web)
for _, row in df.iterrows():
    if str(row["Activo"]).upper() == "SI" and row["Hora"] == hora_str:
        # Evitamos re-envíos (puedes añadir lógica de 'último_envío' en el Excel)
        mensaje_aviso = f"🌸 *HOLA {row['Paciente']}*\nEs hora de tu medicina: **{row['Medicamento']}**\nDosis: {row['Dosis']}"
        enviar_telegram(row["Chat_ID"], mensaje_aviso, row["Medicamento"])
        st.toast(f"Aviso enviado a {row['Paciente']}")

# 3. VISUALIZACIÓN PARA TI
col1, col2 = st.columns(2)

with col1:
    st.subheader("👨 Papá")
    st.dataframe(df[df["Paciente"] == "Papá"][["Medicamento", "Hora", "Dosis"]])

with col2:
    st.subheader("👩 Mamá")
    st.dataframe(df[df["Paciente"] == "Mamá"][["Medicamento", "Hora", "Dosis"]])

st.divider()
st.info("Configuración: El Cron-Job debe visitar esta URL cada minuto para asegurar la precisión.")