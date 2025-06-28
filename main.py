import os
import json
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

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria"],
        ["📄 Ver configuración", "🚀 Activar reenvío", "⏹️ Detener reenvío"],
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    user_id = update.effective_user.id
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permiso para usar este bot.")
        return

    await update.message.reply_text(
        "👋 Bienvenido Administrador.\n"
        "Usa los botones abajo para gestionar el reenvío automático.",
        reply_markup=main_keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ Ayuda:\n\n"
        "/start - Panel principal\n"
        "/help - Este mensaje"
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Comando no reconocido. Usa /help.")

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    user_id = update.effective_user.id
    if user_id != config["admin_id"]:
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

        botones = ReplyKeyboardMarkup([
            ["🕒 Intervalo del mensaje", "✅ Confirmar guardado"],
            ["❌ Cancelar"]
        ], resize_keyboard=True)

        await update.message.reply_text(
            f"📩 Mensaje detectado del canal {origen_id}\n¿Qué deseas hacer con él?",
            reply_markup=botones
        )
        context.user_data["mensaje_actual"] = mensaje_id
    else:
        await update.message.reply_text(
            "⚠️ Debes reenviar directamente el mensaje desde el canal origen."
        )

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Falta el token del bot.")
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
