from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

# Mismo teclado principal para reusarlo
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "✏️ Editar mensaje", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria", "🔗 Vincular canal"],
        ["📄 Ver configuración"]
    ],
    resize_keyboard=True
)

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()

    if user_id != int(config["admin_id"]):
        await update.message.reply_text("🚫 No tienes permisos.", reply_markup=MAIN_KEYBOARD)
        return

    text = update.message.text.strip()

    # ─── 1) Flujo de configuración de un mensaje reenviado ───
    if context.user_data.get("mensaje_actual"):
        mid = context.user_data["mensaje_actual"]

        # 1.a) Ajustar intervalo sólo de este mensaje
        if context.user_data.get("modo_intervalo_mensaje"):
            try:
                val = int(text)
                msgs = cfg.load_mensajes()
                for m in msgs:
                    if m["message_id"] == mid:
                        m["intervalo_segundos"] = val
                cfg.save_mensajes(msgs)
                await update.message.reply_text(
                    f"✅ Intervalo de `{mid}` actualizado a {val}s.",
                    reply_markup=MAIN_KEYBOARD
                )
            except ValueError:
                await update.message.reply_text("❌ Debes enviar un número válido.", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_intervalo_mensaje")
            context.user_data.pop("mensaje_actual")
            return

        if text == "🕒 Intervalo del mensaje":
            await update.message.reply_text(
                "🕒 Escribe el nuevo intervalo (segundos):",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data["modo_intervalo_mensaje"] = True
            return

        # 1.b) Confirmar o cancelar guardado
        if text == "✅ Confirmar guardado":
            await update.message.reply_text("✅ Mensaje confirmado para reenvío.", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("mensaje_actual")
            return

        if text == "❌ Cancelar":
            msgs = cfg.load_mensajes()
            msgs = [m for m in msgs if m["message_id"] != mid]
            cfg.save_mensajes(msgs)
            await update.message.reply_text("❌ Mensaje descartado.", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("mensaje_actual")
            return

        # 1.c) Finalizar configuración e iniciar reenvío
        if text == "🏁 Finalizar configuración":
            context.application.forwarder.start_forwarding()
            await update.message.reply_text(
                "🏁 Configuración finalizada. Reenvío automático iniciado.",
                reply_markup=MAIN_KEYBOARD
            )
            context.user_data.pop("mensaje_actual")
            return

    # Si pulsa cualquiera de las opciones de configuración sin haber reenviado:
    if text in ["🕒 Intervalo del mensaje", "✅ Confirmar guardado", "❌ Cancelar", "🏁 Finalizar configuración"]:
        await update.message.reply_text(
            "⚠️ Primero debes reenviar un mensaje al bot para configurarlo.",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # ─── 2) Vincular canal de origen ───
    if text == "🔗 Vincular canal":
        await update.message.reply_text(
            "🔗 Reenvía un mensaje del canal que quieras vincular como origen:",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["modo_vincular"] = True
        return

    if context.user_data.get("modo_vincular"):
        if update.message.forward_from_chat:
            cid = update.message.forward_from_chat.id
            config["origen_chat_id"] = str(cid)
            cfg.save_config(config)
            await update.message.reply_text(
                f"✅ Canal vinculado: `{cid}`",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await update.message.reply_text("❌ Debes reenviar un mensaje del canal.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_vincular", None)
        return

    # ─── 3) Editar mensaje ya guardado ───
    if text == "✏️ Editar mensaje":
        msgs = cfg.load_mensajes()
        if not msgs:
            await update.message.reply_text("⚠️ No hay mensajes para editar.", reply_markup=MAIN_KEYBOARD)
            return
        lista = "\n".join(f"{i+1}. ID `{m['message_id']}` – {m['intervalo_segundos']}s"
                          for i, m in enumerate(msgs))
        teclado = ReplyKeyboardMarkup(
            keyboard=[
                [str(i+1) for i in range(len(msgs))],
                ["🔙 Volver al menú"]
            ],
            resize_keyboard=True
        )
        await update.message.reply_text(
            f"✏️ Elige número de mensaje a editar:\n\n{lista}",
            parse_mode="Markdown",
            reply_markup=teclado
        )
        context.user_data["modo_listar_editar"] = True
        return

    if context.user_data.get("modo_listar_editar"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_listar_editar", None)
            return
        try:
            idx = int(text) - 1
            msgs = cfg.load_mensajes()
            m = msgs[idx]
            context.user_data["editar_index"] = idx
            teclado = ReplyKeyboardMarkup(
                keyboard=[["🕒 Cambiar intervalo"], ["❌ Cancelar edición"]],
                resize_keyboard=True
            )
            await update.message.reply_text(
                f"✏️ Configurando mensaje `{m['message_id']}` (int {m['intervalo_segundos']}s)\n"
                "Elige acción:",
                reply_markup=teclado
            )
        except Exception:
            await update.message.reply_text("❌ Selección inválida.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_listar_editar", None)
        return

    if text == "🕒 Cambiar intervalo" and context.user_data.get("editar_index") is not None:
        await update.message.reply_text("🕒 Nuevo intervalo (segundos):", reply_markup=ReplyKeyboardRemove())
        context.user_data["modo_intervalo_edit"] = True
        return

    if context.user_data.get("modo_intervalo_edit"):
        try:
            val = int(text)
            idx = context.user_data.pop("editar_index")
            msgs = cfg.load_mensajes()
            msgs[idx]["intervalo_segundos"] = val
            cfg.save_mensajes(msgs)
            await update.message.reply_text(f"✅ Intervalo actualizado a {val}s.", reply_markup=MAIN_KEYBOARD)
        except ValueError:
            await update.message.reply_text("❌ Debes enviar un número.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_intervalo_edit", None)
        return

    if text == "❌ Cancelar edición":
        await update.message.reply_text("❌ Edición cancelada.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("editar_index", None)
        return

    # ─── 4) Eliminar mensaje programado ───
    if text == "🗑️ Eliminar mensaje":
        msgs = cfg.load_mensajes()
        if not msgs:
            await update.message.reply_text("⚠️ No hay mensajes.", reply_markup=MAIN_KEYBOARD)
            return
        lista = "\n".join(f"{i+1}. ID `{m['message_id']}`" for i, m in enumerate(msgs))
        await update.message.reply_text(
            f"🗑️ Mensajes programados:\n{lista}\n\nEnvía el número que deseas eliminar:",
            parse_mode="Markdown"
        )
        context.user_data["modo_eliminar"] = True
        return

    # ─── 5) Cambiar zona horaria ───
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
            await update.message.reply_text(f"✅ Zona: `{text}`", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
        except pytz.UnknownTimeZoneError:
            await update.message.reply_text("❌ Zona no válida.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_timezone", None)
        return

    # ─── 6) Cambiar intervalo global ───
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
            await update.message.reply_text(f"✅ Intervalo global: {val}s.", reply_markup=MAIN_KEYBOARD)
        except ValueError:
            await update.message.reply_text("❌ Debes enviar un número.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_intervalo", None)
        return

    # ─── 7) Añadir destino ───
    if text == "➕ Añadir destino":
        await update.message.reply_text(
            "📝 Envía el ID del canal/grupo destino (–100…):",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_destino"] = True
        return

    if context.user_data.get("modo_destino"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_destino", None)
            return
        dest = text.strip()
        if dest not in config["destinos"]:
            config["destinos"].append(dest)
            cfg.save_config(config)
            await update.message.reply_text(f"✅ Destino `{dest}` agregado.", reply_markup=MAIN_KEYBOARD)
        else:
            await update.message.reply_text("⚠️ El destino ya existe.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_destino", None)
        return

    # ─── 8) Ver configuración ───
    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) or "Ninguno"
        origen = config.get("origen_chat_id", "No asignado")
        await update.message.reply_text(
            f"📄 Configuración actual:\n"
            f"- Intervalo global: {config['intervalo_segundos']}s\n"
            f"- Zona horaria: `{config['timezone']}`\n"
            f"- Canal origen: `{origen}`\n"
            f"- Destinos:\n{destinos}",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # ─── Opción desconocida ───
    await update.message.reply_text("🤖 Opción no reconocida. Usa /help.", reply_markup=MAIN_KEYBOARD)
