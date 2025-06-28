async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permisos.")
        return

    text = update.message.text.strip()

    if text == "🕒 Intervalo del mensaje":
        await update.message.reply_text(
            "Escribe el intervalo en segundos para reenviar este mensaje:",
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
            await update.message.reply_text(f"✅ Intervalo del mensaje configurado en {intervalo}s.")
        except ValueError:
            await update.message.reply_text("⚠️ Debes escribir un número válido.")
        context.user_data["modo_intervalo_mensaje"] = False
        return

    if text == "✅ Confirmar guardado":
        await update.message.reply_text("✅ Mensaje guardado para reenvío automático.")
        context.user_data["mensaje_actual"] = None
        return

    if text == "❌ Cancelar":
        mensaje_id = context.user_data.get("mensaje_actual")
        mensajes = cfg.load_mensajes()
        mensajes = [m for m in mensajes if m["message_id"] != mensaje_id]
        cfg.save_mensajes(mensajes)
        await update.message.reply_text("❌ Mensaje descartado.")
        context.user_data["mensaje_actual"] = None
        return
