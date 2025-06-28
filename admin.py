from telegram import Update
from telegram.ext import ContextTypes
import json

CONFIG_FILE = "config.json"
MENSAJES_FILE = "mensajes.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_mensajes():
    with open(MENSAJES_FILE, "r") as f:
        return json.load(f)

def save_mensajes(mensajes):
    with open(MENSAJES_FILE, "w") as f:
        json.dump(mensajes, f, indent=4)

# Handler de texto general
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    
    if user_id != config["admin_id"]:
        await update.message.reply_text("🚫 No tienes permisos para usar esta función.")
        return

    text = update.message.text.strip()
    
    if text == "➕ Añadir destino":
        await update.message.reply_text(
            "📝 Por favor escribe el *ID* del canal o grupo al que quieres reenviar mensajes.\n"
            "Ejemplo: `-1001234567890`",
            parse_mode="Markdown"
        )
        return
    
    if text.startswith("-100"):
        destinos = config["destinos"]
        if text in destinos:
            await update.message.reply_text("⚠️ Ese destino ya está en la lista.")
        else:
            destinos.append(text)
            save_config(config)
            await update.message.reply_text(f"✅ Destino agregado correctamente: `{text}`", parse_mode="Markdown")
        return

    if text == "🗑️ Eliminar mensaje":
        mensajes = load_mensajes()
        if not mensajes:
            await update.message.reply_text("⚠️ No hay mensajes programados para eliminar.")
            return
        
        lista = "\n".join(
            [f"{idx+1}. ID: {m['message_id']}" for idx, m in enumerate(mensajes)]
        )
        await update.message.reply_text(
            f"🗑️ Estos son los mensajes programados:\n{lista}\n\n"
            "Envía el número del mensaje que quieres eliminar.",
            parse_mode="Markdown"
        )
        context.user_data["modo_eliminar"] = True
        return
    
    # Modo eliminación
    if context.user_data.get("modo_eliminar"):
        try:
            idx = int(text) - 1
            mensajes = load_mensajes()
            if 0 <= idx < len(mensajes):
                eliminado = mensajes.pop(idx)
                save_mensajes(mensajes)
                await update.message.reply_text(
                    f"✅ Mensaje con ID `{eliminado['message_id']}` eliminado correctamente.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Número fuera de rango.")
        except ValueError:
            await update.message.reply_text("⚠️ Por favor escribe un número válido.")
        context.user_data["modo_eliminar"] = False
        return

    if text == "🔁 Cambiar intervalo":
        await update.message.reply_text(
            "🕒 Escribe el nuevo intervalo en *segundos* entre cada reenvío.\n"
            "Ejemplo: `120` para 2 minutos.",
            parse_mode="Markdown"
        )
        context.user_data["modo_intervalo"] = True
        return
    
    if context.user_data.get("modo_intervalo"):
        try:
            nuevo = int(text)
            config["intervalo_segundos"] = nuevo
            save_config(config)
            await update.message.reply_text(f"✅ Intervalo actualizado a {nuevo} segundos.")
        except ValueError:
            await update.message.reply_text("⚠️ Debes escribir un número entero.")
        context.user_data["modo_intervalo"] = False
        return

    if text == "📄 Ver configuración":
        destinos = "\n".join(config["destinos"]) if config["destinos"] else "Ninguno"
        await update.message.reply_text(
            f"📄 *Configuración actual:*\n"
            f"• Intervalo: `{config['intervalo_segundos']}s`\n"
            f"• Destinos:\n{destinos}",
            parse_mode="Markdown"
        )
        return

    if text == "🚀 Activar reenvío":
        context.application.forwarder.start_forwarding()
        await update.message.reply_text("🚀 Reenvío activado con éxito.")
        return

    if text == "⏹️ Detener reenvío":
        context.application.forwarder.stop_forwarding()
        await update.message.reply_text("⏹️ Reenvío detenido correctamente.")
        return

    # Cualquier otro texto
    await update.message.reply_text(
        "🤖 Opción no reconocida. Usa los botones del teclado para gestionar el bot o escribe /help para más información."
      )
