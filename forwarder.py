import json
import pytz
import os
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler

CONFIG_FILE = "config.json"
MENSAJES_FILE = "mensajes.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def load_mensajes():
    if not os.path.exists(MENSAJES_FILE):
        with open(MENSAJES_FILE, "w") as f:
            json.dump([], f)
    with open(MENSAJES_FILE, "r") as f:
        return json.load(f)

class Forwarder:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.jobs = {}
        print("🟢 Módulo de reenvío inicializado correctamente.")

    def start_forwarding(self):
        config = load_config()
        intervalo = config["intervalo_segundos"]
        tz = pytz.timezone(config.get("timezone", "UTC"))

        if "reenviar" in self.jobs:
            self.scheduler.remove_job("reenviar")

        self.jobs["reenviar"] = self.scheduler.add_job(
            self.reenviar_mensajes,
            "interval",
            seconds=intervalo,
            id="reenviar",
            timezone=tz
        )
        print(f"🚀 Reenvío activado cada {intervalo} segundos en zona horaria {tz}.")

    def stop_forwarding(self):
        if "reenviar" in self.jobs:
            self.scheduler.remove_job("reenviar")
            print("⏹️ Reenvío detenido correctamente.")

    async def reenviar_mensajes(self):
        mensajes = load_mensajes()
        config = load_config()
        destinos = config["destinos"]

        if not destinos:
            print("⚠️ No hay destinos configurados. Omitiendo reenvío.")
            return

        for destino in destinos:
            for mensaje in mensajes:
                try:
                    await self.bot.forward_message(
                        chat_id=destino,
                        from_chat_id=mensaje["from_chat_id"],
                        message_id=mensaje["message_id"]
                    )
                    print(f"✔️ Mensaje reenviado a {destino}.")
                except Exception as e:
                    print(f"❌ Error reenviando a {destino}: {e}")
