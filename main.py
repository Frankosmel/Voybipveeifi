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

# Teclado principal con la opción de editar mensaje
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "✏️ Editar mensaje", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria"],
        ["📄 Ver configuración"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    if update.effective_user.id != config["admin_id"]:
        await update.message.reply_text("🚫 Acceso denegado.")
        return
    await update.message.reply_text(
        "👋 *¡Hola administrador!*\n\n"
        "1️⃣ Reenvía un mensaje desde tu canal origen para configurarlo.\n"
        "2️⃣ Ajusta sus parámetros (intervalo, destino, zona) con los botones.\n"
        "3️⃣ Pulsa 🏁 *Finalizar configuración* para arrancar el reenvío.\n\n"
        "O usa el menú de abajo para todas las acciones (añadir, editar, eliminar…).",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda*\n"
        "/start – Panel principal\n"
        "/help – Esta ayuda\n\n"
        "Usa ✏️ para editar la configuración de un mensaje ya guardado."
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Comando no reconocido. Usa /help.")

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captura el mensaje reenviado para iniciar la configuración."""
    config = cfg.load_config()
    if update.effective_user.id != config["admin_id"]:
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
            ], resize_keyboard=True
        )
        await update.message.reply_text(
            f"📩 *Mensaje detectado* del canal `{origen_id}` (ID `{mensaje_id}`).\n"
            "▶️ Elige qué deseas hacer con él:",
            reply_markup=opciones,
            parse_mode="Markdown"
        )
        context.user_data["mensaje_actual"] = mensaje_id
    else:
        await update.message.reply_text(
            "⚠️ Por favor, reenvía directamente desde el canal origen."
        )

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Falta definir BOT_TOKEN")
        return

    app = ApplicationBuilder().token(token).build()
    forwarder = Forwarder(app.bot)
    app.forwarder = forwarder

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Captura mensajes reenviados
    app.add_handler(MessageHandler(filters.FORWARDED, save_message))

    # Botones y comandos de administración (incluye ✏️ Editar mensaje)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))

    # Comandos desconocidos
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Bot inicializado correctamente, esperando comandos...")
    app.run_polling()

if __name__ == "__main__":
    main()
