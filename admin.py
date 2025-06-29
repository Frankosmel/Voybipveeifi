from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

ITEMS_PER_PAGE = 3

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "✏️ Editar mensaje", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria", "🔗 Canal de origen"],
        ["📄 Ver configuración"]
    ],
    resize_keyboard=True
)

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()
    if user_id != int(config["admin_id"]):
        await update.message.reply_text("🚫 No tienes permiso.", reply_markup=MAIN_KEYBOARD)
        return

    text = update.message.text.strip()

    # ─── Flujo de mensaje reenviado ───
    if context.user_data.get("mensaje_actual"):
        mid = context.user_data["mensaje_actual"]

        # Intervalo del mensaje
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
                await update.message.reply_text("❌ Debes enviar un número.", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("modo_intervalo_mensaje")
            context.user_data.pop("mensaje_actual")
            return

        if text == "🕒 Intervalo del mensaje":
            await update.message.reply_text("🕒 Nuevo intervalo (s):", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_intervalo_mensaje"] = True
            return

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

        if text == "🏁 Finalizar configuración":
            context.application.forwarder.start_forwarding()
            await update.message.reply_text("🏁 Configuración finalizada. Reenvío iniciado.", reply_markup=MAIN_KEYBOARD)
            context.user_data.pop("mensaje_actual")
            return

        # Si pulsa estas sin mensaje_actual
    if text in ["🕒 Intervalo del mensaje","✅ Confirmar guardado","❌ Cancelar","🏁 Finalizar configuración"]:
        await update.message.reply_text("⚠️ Primero reenvía un mensaje al bot.", reply_markup=MAIN_KEYBOARD)
        return

    # ─── Vincular canal de origen ───
    if text == "🔗 Canal de origen":
        await update.message.reply_text("🔗 Reenvía un mensaje del canal a vincular.", reply_markup=ReplyKeyboardRemove())
        context.user_data["modo_vincular"] = True
        return

    # ─── Edición paginada de mensajes ───
    if text == "✏️ Editar mensaje":
        msgs = cfg.load_mensajes()
        if not msgs:
            await update.message.reply_text("⚠️ No hay mensajes para editar.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data["page"] = 0
        return await mostrar_pagina_editar(update, context)

    if context.user_data.get("modo_listar_editar"):
        return await manejar_paginacion_o_seleccion(update, context)

    # ─── Eliminar mensaje programado ───
    if text == "🗑️ Eliminar mensaje":
        msgs = cfg.load_mensajes()
        if not msgs:
            await update.message.reply_text("⚠️ No hay mensajes.", reply_markup=MAIN_KEYBOARD)
            return
        lista = "\n".join(f"{i+1}. ID `{m['message_id']}`" for i, m in enumerate(msgs))
        await update.message.reply_text(f"🗑️ Mensajes:\n{lista}\n\nEnvía número a borrar:", parse_mode="Markdown")
        context.user_data["modo_eliminar"] = True
        return
    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text)-1
            msgs = cfg.load_mensajes()
            eliminado = msgs.pop(idx)
            cfg.save_mensajes(msgs)
            await update.message.reply_text(f"✅ Eliminado `{eliminado['message_id']}`.", reply_markup=MAIN_KEYBOARD)
        except:
            await update.message.reply_text("❌ Número inválido.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_eliminar", None)
        return

    # ─── Cambiar zona horaria ───
    if text == "🌐 Cambiar zona horaria":
        await update.message.reply_text("🌍 Nueva zona pytz:", reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True))
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
            await update.message.reply_text(f"✅ Zona `{text}`.", parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
        except:
            await update.message.reply_text("❌ Zona no válida.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_timezone", None)
        return

    # ─── Cambiar intervalo global ───
    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text("🕒 Nuevo intervalo global (s):", reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True))
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
            await update.message.reply_text(f"✅ Intervalo global {val}s.", reply_markup=MAIN_KEYBOARD)
        except:
            await update.message.reply_text("❌ Número inválido.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_intervalo", None)
        return

    # ─── Añadir destino ───
    if text == "➕ Añadir destino":
        await update.message.reply_text("📝 ID destino (–100…):", reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True))
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
            await update.message.reply_text("⚠️ Ya existe.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_destino", None)
        return

    # ─── Ver configuración ───
    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) or "Ninguno"
        origen = config.get("origen_chat_id", "No asignado")
        await update.message.reply_text(
            f"📄 Configuración:\n"
            f"- Intervalo global: {config['intervalo_segundos']}s\n"
            f"- Zona: `{config['timezone']}`\n"
            f"- Canal origen: `{origen}`\n"
            f"- Destinos:\n{destinos}",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # ─── Opción desconocida ───
    await update.message.reply_text("🤖 No reconozco esa opción. Usa /help.", reply_markup=MAIN_KEYBOARD)


async def mostrar_pagina_editar(update, context):
    msgs = cfg.load_mensajes()
    page = context.user_data["page"]
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    subset = msgs[start:end]

    lines = [f"{i+1}. ID `{m['message_id']}` – {m['intervalo_segundos']}s"
             for i, m in enumerate(subset, start=start)]
    text = f"✏️ Mensajes (pág. {page+1}/{(len(msgs)-1)//ITEMS_PER_PAGE+1}):\n\n" + "\n".join(lines)

    buttons = [[str(i+1) for i in range(start, min(end, len(msgs)))]]
    nav = []
    if page>0:     nav.append("⬅️ Ant")
    if end< len(msgs): nav.append("➡️ Sig")
    nav.append("🔙 Volver al menú")
    buttons.append(nav)

    teclado = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=teclado)
    context.user_data["modo_listar_editar"] = True

async def manejar_paginacion_o_seleccion(update, context):
    text = update.message.text.strip()
    msgs = cfg.load_mensajes()
    page = context.user_data["page"]
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    if text=="⬅️ Ant":
        context.user_data["page"] = page-1
        return await mostrar_pagina_editar(update, context)
    if text=="➡️ Sig":
        context.user_data["page"] = page+1
        return await mostrar_pagina_editar(update, context)
    if text=="🔙 Volver al menú":
        await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_listar_editar", None)
        return

    try:
        idx = int(text)-1
        m = msgs[idx]
        context.user_data["editar_index"] = idx
        context.user_data.pop("modo_listar_editar", None)
        teclado = ReplyKeyboardMarkup([["🕒 Cambiar intervalo"], ["❌ Cancelar edición"]], resize_keyboard=True)
        await update.message.reply_text(
            f"✏️ Configurando `{m['message_id']}` (int {m['intervalo_segundos']}s)\nElige:",
            reply_markup=teclado
        )
    except:
        await update.message.reply_text("❌ Selección inválida.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_listar_editar", None)
        return
