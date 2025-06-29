import config_manager as cfg

class Forwarder:
    def __init__(self, bot, job_queue):
        self.bot = bot
        self.jq = job_queue
        self.job = None
        print("🟢 Forwarder listo.")

    def start_forwarding(self):
        conf = cfg.load_config()
        interval = conf["intervalo_segundos"]
        if self.job:
            self.job.schedule_removal()
        self.job = self.jq.run_repeating(
            self._reenviar,
            interval=interval,
            first=interval,
            name="reenviar"
        )
        print(f"🚀 Envío cada {interval}s en zona {conf['zone']}")

    def stop_forwarding(self):
        if self.job:
            self.job.schedule_removal()
            self.job = None
            print("⏹️ Reenvío detenido.")

    async def _reenviar(self, context):
        conf = cfg.load_config()
        ms = cfg.load_mensajes()
        for m in ms:
            if m.get("dest_all", True):
                dests = conf["destinos"]
            else:
                dests = conf["listas_destinos"].get(m.get("dest_list"), [])
            for d in dests:
                try:
                    await self.bot.forward_message(
                        chat_id=d,
                        from_chat_id=m["from_chat_id"],
                        message_id=m["message_id"]
                    )
                    print(f"✔️ {m['message_id']} → {d}")
                except Exception as e:
                    print(f"❌ Error {m['message_id']} → {d}: {e}")
