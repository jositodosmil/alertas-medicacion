import os
import requests
import pandas as pd
from datetime import datetime
import pytz

# Configuración desde secretos de GitHub
TOKEN = os.getenv("TOKEN_TELEGRAM")
# Para simplificar, puedes leer el CSV directamente si lo publicas en la web
URL_SHEET = os.getenv("GSHEETS_URL") 

def enviar_telegram(chat_id, mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})

# Hora de España
tz = pytz.timezone("Europe/Madrid")
hora_actual = datetime.now(tz).strftime("%H:%M")

# Leer Excel (usa la URL de 'Publicar en la web' como CSV)
df = pd.read_csv(URL_SHEET)
df = df.ffill()

for _, row in df.iterrows():
    if str(row["Activo"]).upper() == "SI" and str(row["Hora"]).strip() == hora_actual:
        msg = f"🌸 *HOLA {row['Paciente']}*\nEs hora de: **{row['Medicamento']}**"
        enviar_telegram(row["Chat_ID"], msg)