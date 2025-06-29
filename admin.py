from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()

    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permiso.")
        return

    text = update.message.text.strip()

    # 1️⃣ Modo eliminar (prioritario)
    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text) - 1
            mensajes = cfg.load_mensajes()
            eliminado = mensajes.pop(idx)
            cfg.save_mensajes(mensajes)
            await update.message.reply_text(f"✅ Mensaje `{eliminado['message_id']}` eliminado.")
        except Exception:
            await update.message.reply_text("❌ Número inválido.")
        context.user_data.pop("modo_eliminar", None)
        return

    # 2️⃣ Modo editar: listar mensajes y elegir uno
    if text == "✏️ Editar mensaje":
        mensajes = cfg.load_mensajes()
        if not mensajes:
            await update.message.reply_text("⚠️ No hay mensajes para editar.")
            return
        lista = "\n".join(
            f"{i+1}. ID `{m['message_id']}` – intervalo {m.get('intervalo_segundos', '-') }s"
            for i, m in enumerate(mensajes)
        )
        await update.message.reply_text(
            f"✏️ Mensajes programados:\n{lista}\n\n"
            "Envía el número del mensaje que deseas editar:",
            parse_mode="Markdown"
        )
        context.user_data["modo_listar_editar"] = True
        return

    if context.user_data.get("modo_listar_editar"):
        try:
            sel = int(text) - 1
            mensajes = cfg.load_mensajes()
            m = mensajes[sel]
            context.user_data["editar_index"] = sel
            # teclado de opciones de edición
            teclado = ReplyKeyboardMarkup([
                ["🕒 Cambiar intervalo"], ["❌ Cancelar edición"]
            ], resize_keyboard=True)
            await update.message.reply_text(
                f"✏️ Configurando mensaje `{m['message_id']}`:\n"
                f"- Intervalo actual: {m.get('intervalo_segundos')}s\n\n"
                "Elige qué quieres editar:",
                reply_markup=teclado
            )
        except Exception:
            await update.message.reply_text("❌ Selección inválida.")
        context.user_data.pop("modo_listar_editar", None)
        return

    # 3️⃣ Cambiar intervalo de mensaje seleccionado
    if text == "🕒 Cambiar intervalo" and context.user_data.get("editar_index") is not None:
        await update.message.reply_text("🕒 Escribe el nuevo intervalo (segundos):")
        context.user_data["modo_intervalo_edit"] = True
        return

    if context.user_data.get("modo_intervalo_edit"):
        try:
            val = int(text)
            idx = context.user_data["editar_index"]
            mensajes = cfg.load_mensajes()
            mensajes[idx]["intervalo_segundos"] = val
            cfg.save_mensajes(mensajes)
            await update.message.reply_text(f"✅ Intervalo actualizado a {val}s.")
        except ValueError:
            await update.message.reply_text("❌ Debes enviar un número.")
        context.user_data.pop("modo_intervalo_edit", None)
        context.user_data.pop("editar_index", None)
        return

    if text == "❌ Cancelar edición":
        context.user_data.pop("modo_listar_editar", None)
        context.user_data.pop("modo_intervalo_edit", None)
        context.user_data.pop("editar_index", None)
        await update.message.reply_text("❌ Edición cancelada.")
        return

    # 4️⃣ Eliminar mensaje programado
    if text == "🗑️ Eliminar mensaje":
        mensajes = cfg.load_mensajes()
        if not mensajes:
            await update.message.reply_text("⚠️ No hay mensajes programados.")
            return
        lista = "\n".join(f"{i+1}. ID `{m['message_id']}`" for i, m in enumerate(mensajes))
        await update.message.reply_text(
            f"🗑️ Mensajes:\n{lista}\n\nEnvía el número a borrar:",
            parse_mode="Markdown"
        )
        context.user_data["modo_eliminar"] = True
        return

    # 5️⃣ Confirmar/cancelar configuración inicial de mensaje reenviado
    if text == "✅ Confirmar guardado":
        await update.message.reply_text("✅ Mensaje guardado para reenvío.")
        context.user_data.pop("mensaje_actual", None)
        return

    if text == "❌ Cancelar":
        mensaje_id = context.user_data.get("mensaje_actual")
        mensajes = cfg.load_mensajes()
        mensajes = [m for m in mensajes if m["message_id"] != mensaje_id]
        cfg.save_mensajes(mensajes)
        await update.message.reply_text("❌ Mensaje descartado.")
        context.user_data.pop("mensaje_actual", None)
        return

    # 6️⃣ Finalizar configuración
    if text == "🏁 Finalizar configuración":
        context.application.forwarder.start_forwarding()
        await update.message.reply_text("🏁 Configuración finalizada. Reenvío automático iniciado.")
        return

    # 7️⃣ Cambiar zona horaria
    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text(
            "🌍 Escribe la zona horaria (pytz), ej. America/Havana:\n"
            "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
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
            await update.message.reply_text(f"✅ Zona horaria: `{tz}`.", parse_mode="Markdown")
        except pytz.UnknownTimeZoneError:
            await update.message.reply_text("❌ Zona inválida.")
        context.user_data.pop("modo_timezone", None)
        return

    # 8️⃣ Cambiar intervalo global
    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text("🕒 Nuevo intervalo global (segundos):")
        context.user_data["modo_intervalo"] = True
        return

    if context.user_data.get("modo_intervalo"):
        try:
            val = int(text)
            config["intervalo_segundos"] = val
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Intervalo global: {val}s.")
        except ValueError:
            await update.message.reply_text("❌ Número inválido.")
        context.user_data.pop("modo_intervalo", None)
        return

    # 9️⃣ Añadir destino
    if text == "➕ Añadir destino":
        await update.message.reply_text("📝 Envía el ID del destino (ej. -1001234567890):")
        context.user_data["modo_destino"] = True
        return

    if context.user_data.get("modo_destino"):
        destino = text.strip()
        if destino not in config["destinos"]:
            config["destinos"].append(destino)
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Destino `{destino}` agregado.")
        else:
            await update.message.reply_text("⚠️ Destino ya existe.")
        context.user_data.pop("modo_destino", None)
        return

    # 🔟 Ver configuración
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

    # ❓ Opción desconocida
    await update.message.reply_text("🤖 No reconozco esa opción. Usa /help.")
