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

MAIN_KB = ReplyKeyboardMarkup([
    ["🔗 Canal de Origen", "📂 Destinos"],
    ["✏️ Editar Mensaje", "🗑️ Eliminar Mensaje"],
    ["🔁 Cambiar Intervalo", "🌐 Cambiar Zona"],
    ["📄 Ver Configuración"]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conf = cfg.load_config()
    if update.effective_user.id != int(conf["admin_id"]):
        return await update.message.reply_text(
            "🚫 *Acceso denegado.*",
            parse_mode="Markdown",
            reply_markup=MAIN_KB
        )
    await update.message.reply_text(
        "🚀 *Panel Principal* 🚀\n\n"
        "🔗 Canal de Origen: vincula tu fuente.\n"
        "📂 Destinos: gestiona destinos y listas.\n"
        "✏️ / 🗑️ Mensajes reenviados.\n"
        "🔁 Intervalo / 🌐 Zona.\n"
        "📄 Ver Configuración.",
        parse_mode="Markdown",
        reply_markup=MAIN_KB
    )

async def save_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conf = cfg.load_config()
    uid = update.effective_user.id
    if uid != int(conf["admin_id"]):
        return

    # 1) Vincular origen
    if context.user_data.pop("modo_vincular", False):
        if update.message.forward_from_chat:
            cid = update.message.forward_from_chat.id
            conf["origen_chat_id"] = str(cid)
            cfg.save_config(conf)
            await update.message.reply_text(
                f"✅ *Origen vinculado:* `{cid}`",
                parse_mode="Markdown",
                reply_markup=MAIN_KB
            )
        else:
            await update.message.reply_text(
                "❌ Reenvía desde el canal a vincular.",
                parse_mode="Markdown",
                reply_markup=MAIN_KB
            )
        return

    # 2) Guardar mensaje a configurar
    if update.message.forward_from_chat:
        origen, mid = update.message.forward_from_chat.id, update.message.forward_from_message_id
        ms = cfg.load_mensajes()
        ms.append({
            "from_chat_id": origen,
            "message_id": mid,
            "intervalo_segundos": conf["intervalo_segundos"],
            "dest_all": True,
            "dest_list": None
        })
        cfg.save_mensajes(ms)

        kb = ReplyKeyboardMarkup([
            ["👥 A Todos", "📋 Lista"],
            ["✅ Guardar", "❌ Cancelar"]
        ], resize_keyboard=True)
        await update.message.reply_text(
            f"🔥 *Mensaje detectado!* 🔥\n"
            f"Canal `{origen}` • ID `{mid}`\n\n"
            "¿A dónde reenviar?",
            parse_mode="Markdown",
            reply_markup=kb
        )
        context.user_data["mensaje_actual"] = mid
    else:
        await update.message.reply_text(
            "⚠️ Reenvía directamente desde tu canal origen.",
            parse_mode="Markdown",
            reply_markup=MAIN_KB
        )

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ERROR: define BOT_TOKEN.")
        return

    app = ApplicationBuilder().token(token).build()
    fwd = Forwarder(app.bot, app.job_queue)
    app.forwarder = fwd

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.FORWARDED, save_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler))

    print("✅ Bot listo…")
    app.run_polling()

if __name__ == "__main__":
    main()
