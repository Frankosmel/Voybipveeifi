from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

# Teclado principal (duplicado aquí para reenviar tras cerrar mensajes)
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "✏️ Editar mensaje", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria"],
        ["📄 Ver configuración"]
    ],
    resize_keyboard=True
)

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()

    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permiso.")
        return

    text = update.message.text.strip()

    # 1️⃣ Si estamos en modo_eliminar, procesamos primero
    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text) - 1
            mensajes = cfg.load_mensajes()
            eliminado = mensajes.pop(idx)
            cfg.save_mensajes(mensajes)
            await update.message.reply_text(
                f"✅ Mensaje `{eliminado['message_id']}` eliminado.",
                reply_markup=MAIN_KEYBOARD
            )
        except Exception:
            await update.message.reply_text(
                "❌ Número inválido.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_eliminar", None)
        return

    # 2️⃣ Confirmar o cancelar guardado de mensaje reenviado
    if text == "✅ Confirmar guardado":
        await update.message.reply_text(
            "✅ Mensaje guardado para reenvío automático.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.pop("mensaje_actual", None)
        # re-mostrar menú principal
        await update.message.reply_text("🔙 De nuevo al menú principal:", reply_markup=MAIN_KEYBOARD)
        return

    if text == "❌ Cancelar":
        mensaje_id = context.user_data.get("mensaje_actual")
        mensajes = cfg.load_mensajes()
        mensajes = [m for m in mensajes if m["message_id"] != mensaje_id]
        cfg.save_mensajes(mensajes)
        await update.message.reply_text(
            "❌ Mensaje descartado.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.pop("mensaje_actual", None)
        await update.message.reply_text("🔙 De nuevo al menú principal:", reply_markup=MAIN_KEYBOARD)
        return

    # 3️⃣ Finalizar configuración y arrancar reenvío
    if text == "🏁 Finalizar configuración":
        context.application.forwarder.start_forwarding()
        await update.message.reply_text(
            "🏁 Configuración finalizada.\n▶️ Reenvío automático iniciado.",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
        return

    # 4️⃣ Editar mensaje: listar y luego cambiar intervalo
    if text == "✏️ Editar mensaje":
        mensajes = cfg.load_mensajes()
        if not mensajes:
            await update.message.reply_text(
                "⚠️ No hay mensajes para editar.",
                reply_markup=MAIN_KEYBOARD
            )
            return
        lista = "\n".join(
            f"{i+1}. ID `{m['message_id']}` – intervalo {m.get('intervalo_segundos','-')}s"
            for i, m in enumerate(mensajes)
        )
        teclado = ReplyKeyboardMarkup([
            [f"{i+1}" for i in range(len(mensajes))],
            ["🔙 Volver al menú"]
        ], resize_keyboard=True)
        await update.message.reply_text(
            f"✏️ Elige el número del mensaje a editar:\n\n{lista}",
            reply_markup=teclado,
            parse_mode="Markdown"
        )
        context.user_data["modo_listar_editar"] = True
        return

    if context.user_data.get("modo_listar_editar"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_listar_editar", None)
            return
        try:
            sel = int(text) - 1
            mensajes = cfg.load_mensajes()
            m = mensajes[sel]
            context.user_data["editar_index"] = sel
            teclado = ReplyKeyboardMarkup([
                ["🕒 Cambiar intervalo"], ["❌ Cancelar edición"]
            ], resize_keyboard=True)
            await update.message.reply_text(
                f"✏️ Configurando mensaje `{m['message_id']}` (int {m['intervalo_segundos']}s)\n"
                "Elige acción:",
                reply_markup=teclado
            )
        except Exception:
            await update.message.reply_text(
                "❌ Selección inválida.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_listar_editar", None)
        return

    # 5️⃣ Cambiar intervalo de mensaje seleccionado
    if text == "🕒 Cambiar intervalo" and context.user_data.get("editar_index") is not None:
        await update.message.reply_text("🕒 Nuevo intervalo (segundos):")
        context.user_data["modo_intervalo_edit"] = True
        return

    if context.user_data.get("modo_intervalo_edit"):
        try:
            val = int(text)
            idx = context.user_data["editar_index"]
            mensajes = cfg.load_mensajes()
            mensajes[idx]["intervalo_segundos"] = val
            cfg.save_mensajes(mensajes)
            await update.message.reply_text(
                f"✅ Intervalo actualizado a {val}s.",
                reply_markup=MAIN_KEYBOARD
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Debes enviar un número.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_intervalo_edit", None)
        context.user_data.pop("editar_index", None)
        return

    if text == "❌ Cancelar edición":
        await update.message.reply_text(
            "❌ Edición cancelada.",
            reply_markup=MAIN_KEYBOARD
        )
        context.user_data.pop("modo_intervalo_edit", None)
        context.user_data.pop("editar_index", None)
        return

    # 6️⃣ Cambiar zona horaria
    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text(
            "🌍 Nueva zona pytz (p.ej. Europe/Madrid):",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_timezone"] = True
        return

    if context.user_data.get("modo_timezone"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_timezone", None)
            return
        try:
            pytz.timezone(text)
            config["timezone"] = text
            cfg.save_config(config)
            await update.message.reply_text(
                f"✅ Zona horaria: `{text}`.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
        except pytz.UnknownTimeZoneError:
            await update.message.reply_text(
                "❌ Zona inválida.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_timezone", None)
        return

    # 7️⃣ Cambiar intervalo global
    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text(
            "🕒 Nuevo intervalo global (s):",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_intervalo"] = True
        return

    if context.user_data.get("modo_intervalo"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_intervalo", None)
            return
        try:
            val = int(text)
            config["intervalo_segundos"] = val
            cfg.save_config(config)
            await update.message.reply_text(
                f"✅ Intervalo global: {val}s.",
                reply_markup=MAIN_KEYBOARD
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Debes enviar un número.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_intervalo", None)
        return

    # 8️⃣ Añadir destino
    if text == "➕ Añadir destino":
        await update.message.reply_text(
            "📝 ID de destino (p.ej. -1001234567890):",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_destino"] = True
        return

    if context.user_data.get("modo_destino"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_destino", None)
            return
        destino = text
        if destino not in config["destinos"]:
            config["destinos"].append(destino)
            cfg.save_config(config)
            await update.message.reply_text(
                f"✅ Destino `{destino}` agregado.",
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await update.message.reply_text(
                "⚠️ Ese destino ya existe.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_destino", None)
        return

    # 9️⃣ Ver configuración
    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) or "Ninguno"
        await update.message.reply_text(
            f"📄 Configuración:\n"
            f"- Intervalo global: {config['intervalo_segundos']}s\n"
            f"- Zona horaria: `{config['timezone']}`\n"
            f"- Destinos:\n{destinos}",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # 🔟 Opción desconocida
    await update.message.reply_text(
        "🤖 Opción no reconocida. Usa /help.",
        reply_markup=MAIN_KEYBOARD
            )
