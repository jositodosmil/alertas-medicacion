import sqlite3
import asyncio
import threading
from datetime import datetime
from flask import Flask, request, redirect, render_template_string
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "8615340270:AAHoE31HRAAAZx7EXYzn-tWLKbwQQDp7Cnk"
SUPERVISOR_CHAT_ID = 7874158815

conn = sqlite3.connect("meds.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS patients(
id INTEGER PRIMARY KEY,
name TEXT,
chat_id INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS meds(
id INTEGER PRIMARY KEY,
patient_id INTEGER,
name TEXT,
dose TEXT,
time TEXT,
photo TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS logs(
id INTEGER PRIMARY KEY,
med_id INTEGER,
scheduled TEXT,
taken INTEGER,
taken_time TEXT
)
""")

conn.commit()

app_web = Flask(__name__)

HTML = """
<h2>Pacientes</h2>

<form method="post">
Nombre <input name="pname">
Chat ID <input name="chat">
<button name="addp">Añadir paciente</button>
</form>

<ul>
{% for p in patients %}
<li>{{p[1]}} (chat {{p[2]}})</li>
{% endfor %}
</ul>

<h2>Medicamentos</h2>

<form method="post">
Paciente
<select name="patient">
{% for p in patients %}
<option value="{{p[0]}}">{{p[1]}}</option>
{% endfor %}
</select>

Nombre <input name="name">
Dosis <input name="dose">
Hora <input name="time">
Foto (ruta archivo) <input name="photo">

<button name="addm">Añadir medicamento</button>
</form>

<ul>
{% for m in meds %}
<li>{{m[1]}} - {{m[2]}} {{m[3]}} {{m[4]}}</li>
{% endfor %}
</ul>

<a href="/stats">Ver estadísticas</a>
"""

STATS = """
<h2>Estadísticas de cumplimiento</h2>

<table border=1>
<tr><th>Paciente</th><th>% cumplimiento</th></tr>

{% for s in stats %}
<tr>
<td>{{s[0]}}</td>
<td>{{s[1]}}%</td>
</tr>
{% endfor %}
</table>

<a href="/">volver</a>
"""

@app_web.route("/", methods=["GET","POST"])
def panel():

    if request.method == "POST":

        if "addp" in request.form:

            cur.execute(
            "INSERT INTO patients(name,chat_id) VALUES(?,?)",
            (request.form["pname"], request.form["chat"])
            )

        if "addm" in request.form:

            cur.execute(
            "INSERT INTO meds(patient_id,name,dose,time,photo) VALUES(?,?,?,?,?)",
            (
                request.form["patient"],
                request.form["name"],
                request.form["dose"],
                request.form["time"],
                request.form["photo"]
            )
            )

        conn.commit()

        return redirect("/")

    patients = cur.execute("SELECT * FROM patients").fetchall()

    meds = cur.execute("""
    SELECT patients.name,meds.name,meds.dose,meds.time
    FROM meds
    JOIN patients ON meds.patient_id = patients.id
    """).fetchall()

    return render_template_string(
        HTML,
        patients=patients,
        meds=meds
    )

@app_web.route("/stats")
def stats():

    stats = cur.execute("""
    SELECT patients.name,
    ROUND(SUM(logs.taken)*100.0/COUNT(logs.id),1)
    FROM logs
    JOIN meds ON logs.med_id=meds.id
    JOIN patients ON meds.patient_id=patients.id
    GROUP BY patients.name
    """).fetchall()

    return render_template_string(STATS, stats=stats)

async def taken(update, context):

    query = update.callback_query
    log_id = query.data

    cur.execute(
    "UPDATE logs SET taken=1,taken_time=? WHERE id=?",
    (datetime.now(), log_id)
    )

    conn.commit()

    await query.answer()

    await query.edit_message_text(
    "✅ Medicación registrada"
    )

async def check_missed(bot, log_id, patient, med):

    await asyncio.sleep(1800)

    r = cur.execute(
    "SELECT taken FROM logs WHERE id=?",
    (log_id,)
    ).fetchone()

    if r[0] == 0:

        await bot.send_message(
        SUPERVISOR_CHAT_ID,
        f"⚠️ {patient} no confirmó {med}"
        )

async def send_reminder(bot, med):

    cur.execute(
    "INSERT INTO logs(med_id,scheduled,taken) VALUES(?,?,0)",
    (med[0], datetime.now())
    )

    conn.commit()

    log_id = cur.lastrowid

    keyboard = [
        [InlineKeyboardButton("TOMADO ✅", callback_data=str(log_id))]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    chat = med[1]

    if med[5]:

        await bot.send_photo(
        chat,
        photo=open(med[5],"rb"),
        caption=f"💊 {med[2]}\nDosis: {med[3]}",
        reply_markup=markup
        )

    else:

        await bot.send_message(
        chat,
        f"💊 {med[2]}\nDosis: {med[3]}",
        reply_markup=markup
        )

    asyncio.create_task(
        check_missed(bot, log_id, med[6], med[2])
    )

async def scheduler_job(bot):

    now = datetime.now().strftime("%H:%M")

    meds = cur.execute("""
    SELECT meds.id,
           patients.chat_id,
           meds.name,
           meds.dose,
           meds.time,
           meds.photo,
           patients.name
    FROM meds
    JOIN patients ON meds.patient_id = patients.id
    """).fetchall()

    for m in meds:

        if m[4] == now:

            await send_reminder(bot, m)

def main():

    import threading

def run_flask():
    app_web.run(port=5000, use_reloader=False)

def main():

    telegram = Application.builder().token(TOKEN).build()

    telegram.add_handler(
        CallbackQueryHandler(taken)
    )

    scheduler = BackgroundScheduler()

    async def job():
        await scheduler_job(telegram.bot)

    scheduler.add_job(
        lambda: asyncio.run(job()),
        "interval",
        minutes=1
    )

    scheduler.start()

    # arrancar Flask en segundo plano
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("Panel web en: http://localhost:5000")
    print("Bot de Telegram iniciado")

    telegram.run_polling()

if __name__ == "__main__":
    main()