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

# Teclado principal sin botones de inicio/parada manual
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "🌐 Cambiar zona horaria"],
        ["📄 Ver configuración"],
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    if update.effective_user.id != config["admin_id"]:
        await update.message.reply_text("🚫 Acceso denegado. Solo administrador.")
        return
    await update.message.reply_text(
        "👋 *¡Hola administrador!*\n\n"
        "1️⃣ Reenvía un mensaje desde tu canal origen para configurarlo.\n"
        "2️⃣ Ajusta intervalo, destinos o zona horaria con los botones.\n"
        "3️⃣ Cuando termines, pulsa *🏁 Finalizar configuración* para iniciar el reenvío automático.\n\n"
        "📋 Usa el menú de abajo para todo lo demás.",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda del bot*\n\n"
        "• Envía /start para ver el menú.\n"
        "• Reenvía un mensaje para configurarlo.\n"
        "• Usa los botones para agregar destinos, cambiar intervalos o zona horaria.\n"
        "• Pulsa 🏁 para finalizar y arrancar el reenvío.\n"
        "• /help para este mensaje.",
        parse_mode="Markdown"
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Comando no reconocido. Usa /help.")

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    if update.effective_user.id != config["admin_id"]:
        return

    if update.message.forward_from_chat:
        origen_id = update.message.forward_from_chat.id
        mensaje_id = update.message.forward_from_message_id

        mensajes = cfg.load_mensajes()
        # Guardamos con intervalo por defecto
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
            f"📩 *Mensaje detectado* del canal `{origen_id}` (ID `{mensaje_id}`).\n\n"
            "▶️ Elige una acción para este mensaje:",
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
        print("❌ Falta definir BOT_TOKEN en el entorno.")
        return

    app = ApplicationBuilder().token(token).build()

    forwarder = Forwarder(app.bot)
    app.forwarder = forwarder

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Captura mensajes reenviados para configuración
    app.add_handler(MessageHandler(filters.FORWARDED, save_message))

    # Resto de botones y comandos administrativos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))

    # Comandos desconocidos
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Bot inicializado correctamente, esperando comandos...")
    app.run_polling()

if __name__ == "__main__":
    main()
