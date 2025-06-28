from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os
from forwarder import Forwarder
from admin import admin_handler
import config_manager as cfg

# Teclado principal
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "📄 Ver configuración"],
        ["🚀 Activar reenvío", "⏹️ Detener reenvío"],
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = cfg.load_config()
    user_id = update.effective_user.id
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 Este bot solo puede ser usado por el administrador autorizado.")
        return
    
    await update.message.reply_text(
        "👋 *¡Bienvenido administrador!*\n\n"
        "Este bot reenviará automáticamente los mensajes que le mandes manualmente, "
        "respetando el intervalo y los destinos que configures.\n\n"
        "✅ Usa el teclado de abajo para controlar todas las opciones de forma fácil.\n"
        "👉 Para iniciar, reenvía al bot un mensaje que quieras programar para reenvío.\n\n"
        "Para más información escribe /help.",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda del bot*\n\n"
        "👉 Este bot sirve para reenviar mensajes que TÚ le mandes manualmente.\n"
        "🔹 Conserva emojis premium con *forward_message*.\n"
        "🔹 Configura tiempo de reenvío, destinos y horarios.\n\n"
        "*Comandos disponibles:*\n"
        "• /start - Muestra el panel de bienvenida\n"
        "• /help - Ayuda detallada\n\n"
        "📄 Usa los botones para:\n"
        "➕ Añadir destino\n"
        "🗑️ Eliminar mensaje\n"
        "🔁 Cambiar intervalo\n"
        "📄 Ver configuración\n"
        "🚀 Activar reenvío\n"
        "⏹️ Detener reenvío\n",
        parse_mode="Markdown"
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Comando no reconocido.\n"
        "Usa los botones del teclado o /help para ver todas las opciones."
    )

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
            "message_id": mensaje_id
        })
        cfg.save_mensajes(mensajes)
        await update.message.reply_text(
            f"✅ Mensaje programado con éxito para reenvío.\n"
            f"*Origen*: `{origen_id}`\n"
            f"*ID mensaje*: `{mensaje_id}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ Por favor reenvía directamente desde el canal de origen, no copies y pegues el texto."
        )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❌ ERROR: Debes definir la variable BOT_TOKEN en el entorno.")
        return
    
    app = ApplicationBuilder().token(token).build()

    # crear instancia del reenviador
    forwarder = Forwarder(app.bot)
    app.forwarder = forwarder

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # capturar mensajes reenviados manualmente
    app.add_handler(MessageHandler(filters.FORWARDED & filters.ALL, save_message))

    # botones
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))

    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Bot inicializado correctamente, esperando comandos...")
    app.run_polling()

if __name__ == "__main__":
    main()
