from telegram import Update
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()

    # Solo el admin puede usar estos handlers
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permisos para usar este bot.")
        return

    text = update.message.text.strip()

    # 1️⃣ Proceso de eliminación de mensaje en modo_eliminar (prioritario)
    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text) - 1
            mensajes = cfg.load_mensajes()
            if 0 <= idx < len(mensajes):
                eliminado = mensajes.pop(idx)
                cfg.save_mensajes(mensajes)
                await update.message.reply_text(f"✅ Mensaje `{eliminado['message_id']}` eliminado correctamente.")
            else:
                await update.message.reply_text("❌ Número fuera de rango.")
        except ValueError:
            await update.message.reply_text("❌ Eso no es un número válido.")
        context.user_data["modo_eliminar"] = False
        return

    # 2️⃣ Confirmar o cancelar guardado de mensaje reenviado
    if text == "✅ Confirmar guardado":
        await update.message.reply_text("✅ Mensaje guardado para reenvío automático.")
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

    # 3️⃣ Finalizar configuración y arrancar reenvío
    if text == "🏁 Finalizar configuración":
        context.application.forwarder.start_forwarding()
        await update.message.reply_text(
            "🏁 Configuración finalizada.\n"
            "▶️ El reenvío automático ha comenzado. ¡Emojis premium preservados!"
        )
        return

    # 4️⃣ Intervalo específico para un mensaje
    if text == "🕒 Intervalo del mensaje":
        await update.message.reply_text("🕒 Escribe el nuevo intervalo en segundos para ESTE mensaje:")
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
            await update.message.reply_text(
                f"✅ Intervalo del mensaje `{mensaje_id}` ajustado a {intervalo}s."
            )
        except ValueError:
            await update.message.reply_text("❌ Debes enviar un número válido.")
        context.user_data["modo_intervalo_mensaje"] = False
        return

    # 5️⃣ Cambiar zona horaria
    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text(
            "🌍 Escribe la zona horaria en formato pytz.\n"
            "Ejemplo: America/Havana, Europe/Madrid, UTC.\n"
            "Lista completa: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            disable_web_page_preview=True
        )
        context.user_data["modo_timezone"] = True
        return

    if context.user_data.get("modo_timezone"):
        tz = text
        try:
            pytz.timezone(tz)
            config["timezone"] = tz
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Zona horaria cambiada a `{tz}`.")
        except pytz.UnknownTimeZoneError:
            await update.message.reply_text("❌ Zona inválida. Revisa la lista pytz.")
        context.user_data["modo_timezone"] = False
        return

    # 6️⃣ Cambiar intervalo global
    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text("🕒 Escribe el intervalo global en segundos:")
        context.user_data["modo_intervalo"] = True
        return

    if context.user_data.get("modo_intervalo"):
        try:
            nuevo = int(text)
            config["intervalo_segundos"] = nuevo
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Intervalo global ajustado a {nuevo}s.")
        except ValueError:
            await update.message.reply_text("❌ Debes enviar un número entero.")
        context.user_data["modo_intervalo"] = False
        return

    # 7️⃣ Añadir destino
    if text == "➕ Añadir destino":
        await update.message.reply_text(
            "📝 Envía el ID del canal o grupo destino (p.ej. -1001234567890):"
        )
        context.user_data["modo_destino"] = True
        return

    if context.user_data.get("modo_destino"):
        destino = text
        if destino not in config["destinos"]:
            config["destinos"].append(destino)
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Destino `{destino}` agregado.")
        else:
            await update.message.reply_text("⚠️ Ese destino ya existe.")
        context.user_data["modo_destino"] = False
        return

    # 8️⃣ Eliminar mensaje programado
    if text == "🗑️ Eliminar mensaje":
        mensajes = cfg.load_mensajes()
        if not mensajes:
            await update.message.reply_text("⚠️ No hay mensajes programados.")
            return
        lista = "\n".join(f"{i+1}. ID `{m['message_id']}`" for i, m in enumerate(mensajes))
        await update.message.reply_text(
            f"🗑️ Mensajes programados:\n{lista}\n\nEnvía el número que deseas eliminar:"
        )
        context.user_data["modo_eliminar"] = True
        return

    # 9️⃣ Ver configuración actual
    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) or "Ninguno"
        await update.message.reply_text(
            f"📄 Configuración actual:\n"
            f"- Intervalo global: {config['intervalo_segundos']}s\n"
            f"- Zona horaria: `{config['timezone']}`\n"
            f"- Destinos:\n{destinos}",
            parse_mode="Markdown"
        )
        return

    # 🚫 Opción desconocida
    await update.message.reply_text("🤖 Opción no reconocida. Usa /help.")
