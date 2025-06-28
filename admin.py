from telegram import Update
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()
    
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permisos para usar esta función.")
        return

    text = update.message.text.strip()

    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text(
            "🌍 Escribe la nueva zona horaria en formato pytz.\nEjemplo: America/Havana, Europe/Madrid, UTC.\n\n"
            "Lista completa:\nhttps://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            disable_web_page_preview=True
        )
        context.user_data["modo_timezone"] = True
        return

    if context.user_data.get("modo_timezone"):
        tz = text.strip()
        try:
            pytz.timezone(tz)
            config["timezone"] = tz
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Zona horaria cambiada a {tz}.")
        except pytz.UnknownTimeZoneError:
            await update.message.reply_text("❌ Zona horaria no válida. Intenta de nuevo.")
        context.user_data["modo_timezone"] = False
        return

    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) if config["destinos"] else "Ninguno"
        tz = config.get("timezone", "UTC")
        await update.message.reply_text(
            f"📄 Configuración actual:\n"
            f"- Intervalo: {config['intervalo_segundos']} segundos\n"
            f"- Zona horaria: {tz}\n"
            f"- Destinos:\n{destinos}"
        )
        return

    if text == "🚀 Activar reenvío":
        context.application.forwarder.start_forwarding()
        await update.message.reply_text("🚀 Reenvío activado con éxito.")
        return

    if text == "⏹️ Detener reenvío":
        context.application.forwarder.stop_forwarding()
        await update.message.reply_text("⏹️ Reenvío detenido correctamente.")
        return

    await update.message.reply_text(
        "🤖 Opción no reconocida. Usa los botones o escribe /help."
    )
