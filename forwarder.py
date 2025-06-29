import json
import pytz
import os
import asyncio
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler
import config_manager as cfg

class Forwarder:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.jobs = {}
        print("🟢 Módulo de reenvío inicializado correctamente.")

    def start_forwarding(self):
        config = cfg.load_config()
        intervalo = config["intervalo_segundos"]
        tz = pytz.timezone(config.get("timezone", "UTC"))

        if "reenviar" in self.jobs:
            self.scheduler.remove_job("reenviar")

        self.jobs["reenviar"] = self.scheduler.add_job(
            self._trigger_reenvio,
            "interval",
            seconds=intervalo,
            id="reenviar",
            timezone=tz
        )
        print(f"🚀 Reenvío activado cada {intervalo}s en zona {tz}.")

    def stop_forwarding(self):
        if "reenviar" in self.jobs:
            self.scheduler.remove_job("reenviar")
            print("⏹️ Reenvío detenido correctamente.")

    def _trigger_reenvio(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._reenviar())

    async def _reenviar(self):
        mensajes = cfg.load_mensajes()
        config = cfg.load_config()
        destinos = config["destinos"]

        if not destinos:
            print("⚠️ No hay destinos configurados.")
            return

        for destino in destinos:
            for mensaje in mensajes:
                try:
                    await self.bot.forward_message(
                        chat_id=destino,
                        from_chat_id=mensaje["from_chat_id"],
                        message_id=mensaje["message_id"]
                    )
                    print(f"✔️ Mensaje {mensaje['message_id']} reenviado a {destino}.")
                except Exception as e:
                    print(f"❌ Error reenviando a {destino}: {e}")
