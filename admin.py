from telegram import Update
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()

    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permisos para usar este bot.")
        return

    text = update.message.text.strip()

    # 🌐 Cambiar zona horaria
    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text(
            "🌍 Escribe la nueva zona horaria en formato pytz.\n"
            "Ejemplo: America/Havana, Europe/Madrid, UTC.\n\n"
            "Ver zonas válidas aquí:\n"
            "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
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
            await update.message.reply_text("❌ Zona horaria inválida, revisa la lista pytz.")
        context.user_data["modo_timezone"] = False
        return

    # 🔁 Cambiar intervalo general
    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text(
            "🕒 Escribe el nuevo intervalo en segundos (por ejemplo 120 para 2 minutos):"
        )
        context.user_data["modo_intervalo"] = True
        return

    if context.user_data.get("modo_intervalo"):
        try:
            nuevo = int(text)
            config["intervalo_segundos"] = nuevo
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Intervalo general actualizado a {nuevo} segundos.")
        except ValueError:
            await update.message.reply_text("❌ Eso no es un número válido.")
        context.user_data["modo_intervalo"] = False
        return

    # ➕ Añadir destino
    if text == "➕ Añadir destino":
        await update.message.reply_text(
            "📝 Escribe el ID del grupo/canal destino (por ejemplo -1001234567890):"
        )
        context.user_data["modo_destino"] = True
        return

    if context.user_data.get("modo_destino"):
        destino = text.strip()
        if destino not in config["destinos"]:
            config["destinos"].append(destino)
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Destino {destino} agregado correctamente.")
        else:
            await update.message.reply_text("⚠️ Ese destino ya está agregado.")
        context.user_data["modo_destino"] = False
        return

    # 🗑️ Eliminar mensaje programado
    if text == "🗑️ Eliminar mensaje":
        mensajes = cfg.load_mensajes()
        if not mensajes:
            await update.message.reply_text("⚠️ No hay mensajes programados.")
            return
        lista = "\n".join([f"{i+1}. ID: {m['message_id']}" for i, m in enumerate(mensajes)])
        await update.message.reply_text(
            f"🗑️ Mensajes programados:\n{lista}\n\n"
            "Envía el número que deseas eliminar:"
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
                await update.message.reply_text(f"✅ Mensaje con ID {eliminado['message_id']} eliminado.")
            else:
                await update.message.reply_text("❌ Número fuera de rango.")
        except ValueError:
            await update.message.reply_text("❌ Eso no es un número válido.")
        context.user_data["modo_eliminar"] = False
        return

    # Ajustes de reenvío de mensajes reenviados detectados
    if text == "🕒 Intervalo del mensaje":
        await update.message.reply_text(
            "🕒 Escribe el intervalo en segundos para reenviar este mensaje específico:"
        )
        context.user_data["modo_intervalo_mensaje"] = True
        return

    if context.user_data.get("modo_intervalo_mensaje"):
        try:
            intervalo = int(text)
            mensaje_id = context.user_data.get("mensaje_actual")
            mensajes = cfg.load_mensajes()
            for m in mensajes:
                if m["message_id"] == mensaje_id:
                    m["intervalo_segundos"] = intervalo
            cfg.save_mensajes(mensajes)
            await update.message.reply_text(f"✅ Intervalo del mensaje {mensaje_id} configurado a {intervalo} segundos.")
        except ValueError:
            await update.message.reply_text("❌ Eso no es un número válido.")
        context.user_data["modo_intervalo_mensaje"] = False
        return

    if text == "✅ Confirmar guardado":
        await update.message.reply_text("✅ Mensaje guardado correctamente para reenvío.")
        context.user_data["mensaje_actual"] = None
        return

    if text == "❌ Cancelar":
        mensaje_id = context.user_data.get("mensaje_actual")
        mensajes = cfg.load_mensajes()
        mensajes = [m for m in mensajes if m["message_id"] != mensaje_id]
        cfg.save_mensajes(mensajes)
        await update.message.reply_text("❌ Mensaje descartado y eliminado.")
        context.user_data["mensaje_actual"] = None
        return

    # 📄 Ver configuración
    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) if config["destinos"] else "Ninguno"
        tz = config.get("timezone", "UTC")
        await update.message.reply_text(
            f"📄 Configuración actual:\n"
            f"- Intervalo general: {config['intervalo_segundos']} s\n"
            f"- Zona horaria: {tz}\n"
            f"- Destinos:\n{destinos}"
        )
        return

    # 🚀 Activar reenvío
    if text == "🚀 Activar reenvío":
        context.application.forwarder.start_forwarding()
        await update.message.reply_text("🚀 Reenvío activado.")
        return

    # ⏹️ Detener reenvío
    if text == "⏹️ Detener reenvío":
        context.application.forwarder.stop_forwarding()
        await update.message.reply_text("⏹️ Reenvío detenido.")
        return

    # Opción desconocida
    await update.message.reply_text(
        "🤖 Opción no reconocida. Usa los botones de abajo o /help para más info."
    )
