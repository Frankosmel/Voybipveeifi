from telegram import Update
from telegram.ext import ContextTypes
import json
import config_manager as cfg
import pytz

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()
    
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permisos para usar esta función.")
        return

    text = update.message.text.strip()
    
    if text == "➕ Añadir destino":
        await update.message.reply_text(
            "📝 Por favor escribe el *ID* del canal o grupo al que quieres reenviar mensajes.\n"
            "Ejemplo: `-1001234567890`",
            parse_mode="Markdown"
        )
        return
    
    if text.startswith("-100"):
        destinos = config["destinos"]
        if text in destinos:
            await update.message.reply_text("⚠️ Ese destino ya está en la lista.")
        else:
            destinos.append(text)
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Destino agregado correctamente: `{text}`", parse_mode="Markdown")
        return

    if text == "🗑️ Eliminar mensaje":
        mensajes = cfg.load_mensajes()
        if not mensajes:
            await update.message.reply_text("⚠️ No hay mensajes programados para eliminar.")
            return
        
        lista = "\n".join(
            [f"{idx+1}. ID: {m['message_id']}" for idx, m in enumerate(mensajes)]
        )
        await update.message.reply_text(
            f"🗑️ Estos son los mensajes programados:\n{lista}\n\n"
            "Envía el número del mensaje que quieres eliminar.",
            parse_mode="Markdown"
        )
        context.user_data["modo_eliminar"] = True
        return
    
    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text) - 1
            mensajes = cfg.load_mensajes()
            if 0 <= idx < len(mensajes):
                eliminado = mensajes.pop(idx)
                cfg.save_mensajes(mensajes)
                await update.message.reply_text(
                    f"✅ Mensaje con ID `{eliminado['message_id']}` eliminado correctamente.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Número fuera de rango.")
        except ValueError:
            await update.message.reply_text("⚠️ Por favor escribe un número válido.")
        context.user_data["modo_eliminar"] = False
        return

    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text(
            "🕒 Escribe el nuevo intervalo en *segundos* entre cada reenvío.\n"
            "Ejemplo: `120` para 2 minutos.",
            parse_mode="Markdown"
        )
        context.user_data["modo_intervalo"] = True
        return
    
    if context.user_data.get("modo_intervalo"):
        try:
            nuevo = int(text)
            config["intervalo_segundos"] = nuevo
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Intervalo actualizado a {nuevo} segundos.")
        except ValueError:
            await update.message.reply_text("⚠️ Debes escribir un número entero.")
        context.user_data["modo_intervalo"] = False
        return

    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text(
            "🌍 Escribe la nueva zona horaria en formato *pytz*.\n"
            "Ejemplo: `America/Havana`, `Europe/Madrid`, `UTC`.\n\n"
            "Consulta zonas válidas aquí:\n"
            "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            parse_mode="Markdown"
        )
        context.user_data["modo_timezone"] = True
        return
    
    if context.user_data.get("modo_timezone"):
        tz = text.strip()
        try:
            pytz.timezone(tz)
            config["timezone"] = tz
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Zona horaria cambiada a `{tz}`.", parse_mode="Markdown")
        except pytz.UnknownTimeZoneError:
            await update.message.reply_text("❌ Zona horaria no válida. Intenta de nuevo.")
        context.user_data["modo_timezone"] = False
        return

    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) if config["destinos"] else "Ninguno"
        tz = config.get("timezone", "UTC")
        await update.message.reply_text(
            f"📄 *Configuración actual:*\n"
            f"• Intervalo: `{config['intervalo_segundos']}s`\n"
            f"• Zona horaria: `{tz}`\n"
            f"• Destinos:\n{destinos}",
            parse_mode="Markdown"
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
        "🤖 Opción no reconocida. Usa los botones del teclado para gestionar el bot o escribe /help para más información."
        )
