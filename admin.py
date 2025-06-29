from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

ITEMS_PER_PAGE = 3

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["🔗 Canal de Origen", "➕ Añadir Destino"],
        ["✏️ Editar Mensaje", "🗑️ Eliminar Mensaje"],
        ["🔁 Cambiar Intervalo", "🌐 Cambiar Zona"],
        ["📄 Ver Configuración"]
    ],
    resize_keyboard=True
)

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = cfg.load_config()
    text = update.message.text.strip()

    if user_id != int(config["admin_id"]):
        await update.message.reply_text("🚫 No tienes permiso.", reply_markup=MAIN_KEYBOARD)
        return

    # ─── Canal de Origen ───
    if text == "🔗 Canal de Origen":
        await update.message.reply_text(
            "🔗 *Opciones Canal de Origen:*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [["➕ Agregar Canal", "✏️ Editar Canal"], ["❌ Cancelar"]],
                resize_keyboard=True
            )
        )
        context.user_data["modo_origen_menu"] = True
        return

    if context.user_data.get("modo_origen_menu"):
        #  Opciones del submenu
        if text == "➕ Agregar Canal":
            await update.message.reply_text(
                "📢 *Reenvía un mensaje del canal* que quieras AGREGAR como origen.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data["modo_vincular"] = True

        elif text == "✏️ Editar Canal":
            if config.get("origen_chat_id"):
                await update.message.reply_text(
                    "✏️ *Reenvía un mensaje del nuevo canal* para CAMBIAR el origen.",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardRemove()
                )
                context.user_data["modo_vincular"] = True
            else:
                await update.message.reply_text(
                    "⚠️ No hay canal de origen previamente ligado.",
                    reply_markup=MAIN_KEYBOARD
                )

        else:  # Cancelar
            await update.message.reply_text("❌ Acción cancelada.", reply_markup=MAIN_KEYBOARD)

        context.user_data.pop("modo_origen_menu")
        return

    # ─── Configuración puntual de mensaje reenviado ───
    if context.user_data.get("mensaje_actual"):
        mid = context.user_data["mensaje_actual"]

        # Cambiar intervalo de ESTE mensaje
        if context.user_data.get("modo_intervalo_mensaje"):
            try:
                val = int(text)
                msgs = cfg.load_mensajes()
                for m in msgs:
                    if m["message_id"] == mid:
                        m["intervalo_segundos"] = val
                cfg.save_mensajes(msgs)
                await update.message.reply_text(
                    f"✅ Intervalo de `{mid}` → *{val}s*.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Debes enviar un número.",
                    reply_markup=MAIN_KEYBOARD
                )
            context.user_data.pop("modo_intervalo_mensaje")
            context.user_data.pop("mensaje_actual")
            return

        if text == "🕒 Intervalo del Mensaje":
            await update.message.reply_text(
                "🕒 *Escribe el intervalo* (en segundos) para este mensaje:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            context.user_data["modo_intervalo_mensaje"] = True
            return

        # Confirmar / Cancelar / Finalizar
        if text == "✅ Confirmar Guardado":
            await update.message.reply_text(
                "✅ *Mensaje confirmado* para reenvío.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
            context.user_data.pop("mensaje_actual")
            return

        if text == "❌ Cancelar":
            msgs = cfg.load_mensajes()
            cfg.save_mensajes([m for m in msgs if m["message_id"] != mid])
            await update.message.reply_text(
                "❌ Mensaje descartado.",
                reply_markup=MAIN_KEYBOARD
            )
            context.user_data.pop("mensaje_actual")
            return

        if text == "🏁 Finalizar Configuración":
            context.application.forwarder.start_forwarding()
            await update.message.reply_text(
                "🏁 *Configuración finalizada!* Reenvío automático iniciado.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
            context.user_data.pop("mensaje_actual")
            return

        # Si pulsa alguna de esas cuatro sin mensaje_actual
        if text in ["🕒 Intervalo del Mensaje","✅ Confirmar Guardado","❌ Cancelar","🏁 Finalizar Configuración"]:
            await update.message.reply_text(
                "⚠️ Primero reenvía un mensaje al bot antes de usar esta opción.",
                reply_markup=MAIN_KEYBOARD
            )
            return

    # ─── Editar Mensaje (con paginación) ───
    if text == "✏️ Editar Mensaje":
        msgs = cfg.load_mensajes()
        if not msgs:
            await update.message.reply_text("⚠️ No hay mensajes guardados.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data["page"] = 0
        return await mostrar_pagina_editar(update, context)

    if context.user_data.get("modo_listar_editar"):
        return await manejar_paginacion_o_seleccion(update, context)

    # ─── Eliminar Mensaje ───
    if text == "🗑️ Eliminar Mensaje":
        msgs = cfg.load_mensajes()
        if not msgs:
            await update.message.reply_text("⚠️ No hay mensajes para eliminar.", reply_markup=MAIN_KEYBOARD)
            return
        lista = "\n".join(f"{i+1}. `{m['message_id']}` – {m['intervalo_segundos']}s"
                          for i, m in enumerate(msgs))
        await update.message.reply_text(
            f"🗑️ *Mensajes guardados:*\n\n{lista}\n\nEnvía el número a borrar:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["modo_eliminar"] = True
        return

    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text) - 1
            msgs = cfg.load_mensajes()
            eliminado = msgs.pop(idx)
            cfg.save_mensajes(msgs)
            await update.message.reply_text(
                f"✅ Mensaje `{eliminado['message_id']}` eliminado.",
                reply_markup=MAIN_KEYBOARD
            )
        except:
            await update.message.reply_text("❌ Número inválido.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_eliminar")
        return

    # ─── Cambiar Zona Horaria ───
    if text == "🌐 Cambiar Zona":
        await update.message.reply_text(
            "🌍 *Escribe la nueva zona pytz*, ej. `Europe/Madrid`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_timezone"] = True
        return

    if context.user_data.get("modo_timezone"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
        else:
            try:
                pytz.timezone(text)
                config["timezone"] = text
                cfg.save_config(config)
                await update.message.reply_text(
                    f"✅ Zona actualizada a `{text}`.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD
                )
            except:
                await update.message.reply_text("❌ Zona no válida.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_timezone")
        return

    # ─── Cambiar Intervalo Global ───
    if text == "🔁 Cambiar Intervalo":
        await update.message.reply_text(
            "🕒 *Nuevo intervalo global* (segundos):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_intervalo"] = True
        return

    if context.user_data.get("modo_intervalo"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
        else:
            try:
                val = int(text)
                config["intervalo_segundos"] = val
                cfg.save_config(config)
                await update.message.reply_text(
                    f"✅ Intervalo global: *{val}s*.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD
                )
            except:
                await update.message.reply_text("❌ Debes enviar un número.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_intervalo")
        return

    # ─── Añadir Destino ───
    if text == "➕ Añadir Destino":
        await update.message.reply_text(
            "📝 *Escribe el ID* del canal/grupo destino (–100…):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["🔙 Volver al menú"]], resize_keyboard=True)
        )
        context.user_data["modo_destino"] = True
        return

    if context.user_data.get("modo_destino"):
        if text == "🔙 Volver al menú":
            await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
        else:
            destino = text.strip()
            if destino not in config["destinos"]:
                config["destinos"].append(destino)
                cfg.save_config(config)
                await update.message.reply_text(
                    f"✅ Destino `{destino}` agregado.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD
                )
            else:
                await update.message.reply_text("⚠️ Ese destino ya existe.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_destino")
        return

    # ─── Ver Configuración ───
    if text == "📄 Ver Configuración":
        destinos_list = "\n".join(config["destinos"]) or "Ninguno"
        origen = config.get("origen_chat_id","No asignado")
        await update.message.reply_text(
            f"📄 *Configuración actual:*\n"
            f"- Intervalo global: {config['intervalo_segundos']}s\n"
            f"- Zona horaria: `{config['timezone']}`\n"
            f"- Canal origen: `{origen}`\n"
            f"- Destinos:\n{destinos_list}",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # ─── Opción desconocida ───
    await update.message.reply_text(
        "🤖 Opción no reconocida. Usa /help.",
        reply_markup=MAIN_KEYBOARD
    )

# ——— Funciones de paginación ———

async def mostrar_pagina_editar(update, context):
    msgs = cfg.load_mensajes()
    page = context.user_data["page"]
    start = page*ITEMS_PER_PAGE
    end = start+ITEMS_PER_PAGE
    subset = msgs[start:end]

    lines = [f"{i+1}. `{m['message_id']}` – {m['intervalo_segundos']}s"
             for i,m in enumerate(subset, start=start)]
    text = (f"✏️ *Editar Mensaje* (pág {page+1}/"
            f"{(len(msgs)-1)//ITEMS_PER_PAGE+1}):\n\n" + "\n".join(lines))

    nav = []
    if page>0:     nav.append("⬅️ Ant")
    if end<len(msgs): nav.append("➡️ Sig")
    nav.append("🔙 Volver al menú")

    teclado = ReplyKeyboardMarkup([ [str(i+1) for i in range(start,min(end,len(msgs)))], nav ],
                                  resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=teclado)
    context.user_data["modo_listar_editar"] = True

async def manejar_paginacion_o_seleccion(update, context):
    text = update.message.text.strip()
    msgs = cfg.load_mensajes()
    page = context.user_data["page"]
    start = page*ITEMS_PER_PAGE
    end = start+ITEMS_PER_PAGE

    if text=="⬅️ Ant":
        context.user_data["page"] = page-1
        return await mostrar_pagina_editar(update, context)
    if text=="➡️ Sig":
        context.user_data["page"] = page+1
        return await mostrar_pagina_editar(update, context)
    if text=="🔙 Volver al menú":
        await update.message.reply_text("🔙 Menú principal:", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_listar_editar")
        return

    try:
        idx = int(text)-1
        m = msgs[idx]
        context.user_data["editar_index"] = idx
        context.user_data.pop("modo_listar_editar")
        teclado = ReplyKeyboardMarkup([["🕒 Cambiar Intervalo"],["❌ Cancelar edición"]], resize_keyboard=True)
        await update.message.reply_text(
            f"✏️ Configurando `{m['message_id']}` (int {m['intervalo_segundos']}s)\nElige acción:",
            parse_mode="Markdown",
            reply_markup=teclado
        )
    except:
        await update.message.reply_text("❌ Selección inválida.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_listar_editar")
        return
