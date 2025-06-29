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

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "✏️ Editar mensaje", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria", "🔗 Canal de origen"],
        ["📄 Ver configuración"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    if update.effective_user.id != int(config["admin_id"]):
        await update.message.reply_text("🚫 Acceso denegado.", reply_markup=MAIN_KEYBOARD)
        return
    await update.message.reply_text(
        "👋 *¡Hola administrador!*\n\n"
        "1️⃣ Reenvía un mensaje para configurarlo.\n"
        "2️⃣ Ajusta sus parámetros con los botones.\n"
        "3️⃣ Pulsa 🏁 Finalizar configuración para iniciar el reenvío.\n"
        "🔗 Vincula tu canal de origen con ‘Canal de origen’.\n\n"
        "📋 Menú principal abajo.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda*\n"
        "/start – Panel principal\n"
        "/help – Esta ayuda\n\n"
        "👆 Usa los botones para gestionar el bot.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Comando no reconocido. Usa /help.", reply_markup=MAIN_KEYBOARD)

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    uid = update.effective_user.id
    if uid != int(config["admin_id"]):
        return

    # 1) Modo vincular canal
    if context.user_data.get("modo_vincular"):
        if update.message.forward_from_chat:
            cid = update.message.forward_from_chat.id
            config["origen_chat_id"] = str(cid)
            cfg.save_config(config)
            await update.message.reply_text(
                f"✅ Canal de origen vinculado: `{cid}`",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await update.message.reply_text("❌ Reenvía desde el canal a vincular.", reply_markup=MAIN_KEYBOARD)
        context.user_data.pop("modo_vincular", None)
        return

    # 2) Flujo normal de configurar mensaje
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
                ["🕒 Intervalo del mensaje", "✅ Confirmar guardado"],
                ["❌ Cancelar", "🏁 Finalizar configuración"]
            ],
            resize_keyboard=True
        )
        await update.message.reply_text(
            f"📩 *Mensaje detectado* del canal `{origen_id}` (ID `{mensaje_id}`).\n"
            "▶️ Elige una acción:",
            parse_mode="Markdown",
            reply_markup=opciones
        )
        context.user_data["mensaje_actual"] = mensaje_id
    else:
        await update.message.reply_text(
            "⚠️ Reenvía directamente desde el canal origen.",
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

    print("✅ Bot inicializado correctamente, esperando comandos...")
    app.run_polling()

if __name__ == "__main__":
    main()
