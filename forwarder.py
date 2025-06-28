import json
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler

CONFIG_FILE = "config.json"
MENSAJES_FILE = "mensajes.json"

# Cargar configuración
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

# Cargar mensajes programados
def load_mensajes():
    if not os.path.exists(MENSAJES_FILE):
        with open(MENSAJES_FILE, "w") as f:
            json.dump([], f)
    with open(MENSAJES_FILE, "r") as f:
        return json.load(f)

# Guardar mensajes programados
def save_mensajes(mensajes):
    with open(MENSAJES_FILE, "w") as f:
        json.dump(mensajes, f, indent=4)

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

        # Evitar múltiples jobs duplicados
        if "reenviar" in self.jobs:
            self.scheduler.remove_job("reenviar")

        self.jobs["reenviar"] = self.scheduler.add_job(
            self.reenviar_mensajes,
            "interval",
            seconds=intervalo,
            id="reenviar"
        )
        print(f"🚀 Reenvío activado cada {intervalo} segundos.")

    def stop_forwarding(self):
        if "reenviar" in self.jobs:
            self.scheduler.remove_job("reenviar")
            print("⏹️ Reenvío detenido.")

    def reenviar_mensajes(self):
        mensajes = load_mensajes()
        config = load_config()
        destinos = config["destinos"]

        if not destinos:
            print("⚠️ No hay destinos configurados. Omitiendo reenvío.")
            return

        for destino in destinos:
            for mensaje in mensajes:
                try:
                    self.bot.forward_message(
                        chat_id=destino,
                        from_chat_id=mensaje["from_chat_id"],
                        message_id=mensaje["message_id"]
                    )
                    print(f"✔️ Mensaje reenviado a {destino}.")
                except Exception as e:
                    print(f"❌ Error reenviando a {destino}: {e}")
