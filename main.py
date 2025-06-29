import os
import asyncio
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

# Teclado principal con todas las opciones
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "✏️ Editar mensaje", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria", "🔗 Vincular canal"],
        ["📄 Ver configuración"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    if update.effective_user.id != int(config["admin_id"]):
        await update.message.reply_text("🚫 Acceso denegado. Solo administrador.", reply_markup=MAIN_KEYBOARD)
        return

    await update.message.reply_text(
        "👋 *¡Hola administrador!*\n\n"
        "1️⃣ Reenvía un mensaje para configurarlo.\n"
        "2️⃣ Ajusta sus parámetros con los botones.\n"
        "3️⃣ Cuando termines, pulsa 🏁 Finalizar configuración para arrancar el reenvío.\n\n"
        "🔗 Usa ‘Vincular canal’ para seleccionar el origen de mensajes.\n"
        "📋 Menú principal abajo.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda*\n"
        "/start – Panel principal\n"
        "/help – Esta ayuda\n\n"
        "👆 Usa los botones para gestionar el bot."
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Comando no reconocido. Usa /help.", reply_markup=MAIN_KEYBOARD)

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captura el mensaje reenviado para iniciar el submenú de configuración."""
    config = cfg.load_config()
    if update.effective_user.id != int(config["admin_id"]):
        return

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
            "▶️ Elige qué deseas hacer con él:",
            parse_mode="Markdown",
            reply_markup=opciones
        )
        context.user_data["mensaje_actual"] = mensaje_id
    else:
        await update.message.reply_text(
            "⚠️ Por favor, reenvía directamente el mensaje desde el canal origen.",
            reply_markup=MAIN_KEYBOARD
        )

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ERROR: Debes definir la variable BOT_TOKEN.")
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
