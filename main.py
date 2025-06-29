import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from forwarder import Forwarder
import config_manager as cfg
from admin import admin_handler

# Teclado principal: 2 botones por fila, hasta 4 filas
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["🔗 Canal de Origen", "➕ Añadir Destino"],
        ["✏️ Editar Mensaje", "🗑️ Eliminar Mensaje"],
        ["🔁 Cambiar Intervalo", "🌐 Cambiar Zona"],
        ["📄 Ver Configuración"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    if update.effective_user.id != int(config["admin_id"]):
        await update.message.reply_text(
            "🚫 *Acceso denegado.* Solo el administrador puede usar este bot.",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
        return

    await update.message.reply_text(
        "🚀 *¡Bienvenido, Administrador!* 🚀\n\n"
        "Usa el menú de abajo para controlar tu bot:\n"
        "▶️ 🔗 Canal de Origen: vincula o cambia tu canal fuente.\n"
        "▶️ ➕ Añadir Destino: envía donde reenviar.\n"
        "▶️ ✏️ Editar Mensaje / 🗑️ Eliminar Mensaje: gestiona mensajes guardados.\n"
        "▶️ 🔁 Cambiar Intervalo / 🌐 Cambiar Zona: ajustes globales.\n"
        "▶️ 📄 Ver Configuración: repasa todo.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda rápida*\n"
        "/start – Menú principal\n"
        "/help  – Esta ayuda\n\n"
        "❗ Primero vincula un canal, luego guarda mensajes y ajusta a tu gusto.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Comando no reconocido.* Usa /help.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    1) Si estamos en modo_vincular: graba ORIGEN
    2) Si no, asume mensaje para configurar reenvío
    """
    config = cfg.load_config()
    uid = update.effective_user.id
    if uid != int(config["admin_id"]):
        return

    # 1) Canal de Origen
    if context.user_data.get("modo_vincular"):
        if update.message.forward_from_chat:
            cid = update.message.forward_from_chat.id
            config["origen_chat_id"] = str(cid)
            cfg.save_config(config)
            await update.message.reply_text(
                f"✅🔥 *Canal de Origen vinculado!* `{cid}`",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await update.message.reply_text(
                "❌ Debes reenviar un mensaje DESDE el canal a vincular.",
                reply_markup=MAIN_KEYBOARD
            )
        context.user_data.pop("modo_vincular")
        return

    # 2) Flujo estándar de guardar mensaje para reenvío
    if update.message.forward_from_chat:
        origen_id = update.message.forward_from_chat.id
        mensaje_id = update.message.forward_from_message_id

        mensajes = cfg.load_mensajes()
        mensajes.append({
            "from_chat_id": origen_id,
            "message_id": mensaje_id,
            "intervalo_segundos": config["intervalo_segundos"]
        })
        cfg.save_mensajes(mensajes)

        opciones = ReplyKeyboardMarkup(
            keyboard=[
                ["🕒 Intervalo del Mensaje", "✅ Confirmar Guardado"],
                ["❌ Cancelar", "🏁 Finalizar Configuración"]
            ],
            resize_keyboard=True
        )
        await update.message.reply_text(
            f"🔥 *Nuevo Mensaje detectado!* 🔥\n"
            f"Canal `{origen_id}`, ID `{mensaje_id}`\n\n"
            "Elige tu próxima acción:",
            parse_mode="Markdown",
            reply_markup=opciones
        )
        context.user_data["mensaje_actual"] = mensaje_id
    else:
        await update.message.reply_text(
            "⚠️ Por favor, reenvía *directamente* desde el canal fuente.",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ERROR: BOT_TOKEN no definido.")
        return

    app = ApplicationBuilder().token(token).build()
    forwarder = Forwarder(app.bot)
    app.forwarder = forwarder

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.FORWARDED, save_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Bot iniciado correctamente, esperando comandos…")
    app.run_polling()

if __name__ == "__main__":
    main()
