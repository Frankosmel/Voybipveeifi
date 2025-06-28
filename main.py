from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os

# Archivo de configuración en el mismo nivel
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

config = load_config()

# Teclado principal (bajo teclado)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Añadir destino", "🗑️ Eliminar mensaje"],
        ["🔁 Cambiar intervalo", "📄 Ver configuración"],
        ["🚀 Activar reenvío", "⏹️ Detener reenvío"],
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != config["admin_id"]:
        await update.message.reply_text(
            "🚫 Lo siento, este bot es solo para uso del administrador autorizado."
        )
        return
    
    await update.message.reply_text(
        "👋 *¡Bienvenido administrador!*\n\n"
        "Este bot te ayudará a reenviar automáticamente los mensajes que le envíes manualmente, "
        "respetando el intervalo y configuraciones que ajustes.\n\n"
        "✅ *Usa el teclado de abajo para gestionar todas las opciones fácilmente.*\n"
        "👉 Puedes comenzar reenviando un mensaje que quieras programar.\n\n"
        "Si necesitas ayuda, escribe /help.",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Ayuda del bot*\n\n"
        "👉 Este bot sirve para reenviar mensajes que tú le mandes de forma manual.\n"
        "🔹 Conserva emojis premium usando *forward_message*.\n"
        "🔹 Configura el tiempo de reenvío, destinos y horarios.\n\n"
        "*Comandos disponibles:*\n"
        "• /start - Mostrar mensaje de bienvenida y menú\n"
        "• /help - Mostrar esta ayuda\n\n"
        "📄 Además usa los botones para:\n"
        "➕ Añadir destino\n"
        "🗑️ Eliminar mensaje\n"
        "🔁 Cambiar intervalo\n"
        "📄 Ver configuración actual\n"
        "🚀 Activar reenvío\n"
        "⏹️ Detener reenvío\n",
        parse_mode="Markdown"
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Comando no reconocido.*\n"
        "Usa los botones del teclado o escribe /help para ver las opciones disponibles.",
        parse_mode="Markdown"
    )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❌ ERROR: Debes exportar BOT_TOKEN en tus variables de entorno.")
        return
    
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Bot inicializado correctamente. Esperando mensajes...")
    app.run_polling()

if __name__ == "__main__":
    main()
