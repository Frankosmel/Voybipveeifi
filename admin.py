from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import config_manager as cfg
import pytz

MAIN_KB = ReplyKeyboardMarkup([
    ["🔗 Canal de Origen", "📂 Destinos"],
    ["🔁 Cambiar Intervalo", "🌐 Cambiar Zona"],
    ["📄 Ver Configuración"]
], resize_keyboard=True)

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    conf = cfg.load_config()
    uid = update.effective_user.id
    if uid != int(conf["admin_id"]):
        return await update.message.reply_text("🚫 Sin permiso.", reply_markup=MAIN_KB)

    # ─ Canal de Origen ─
    if txt == "🔗 Canal de Origen":
        kb = ReplyKeyboardMarkup([["➕ Agregar Canal","✏️ Editar Canal"],["❌ Cancelar"]], resize_keyboard=True)
        await update.message.reply_text("🔗 *Origen:* elige", parse_mode="Markdown", reply_markup=kb)
        context.user_data["modo_origen_menu"] = True
        return
    if context.user_data.pop("modo_origen_menu", False):
        if txt in ("➕ Agregar Canal","✏️ Editar Canal"):
            await update.message.reply_text("📢 Reenvía un mensaje *del canal* a vincular.", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_vincular"] = True
        else:
            await update.message.reply_text("❌ Cancelado.", reply_markup=MAIN_KB)
        return

    # ─ Destinos y Listas ─
    if txt == "📂 Destinos":
        kb = ReplyKeyboardMarkup([
            ["➕ Agregar Destino","🗑️ Eliminar Destino"],
            ["📁 Crear Lista","📂 Gestionar Listas"],
            ["🔙 Volver"]
        ], resize_keyboard=True)
        await update.message.reply_text("📂 *Destinos:* elige", parse_mode="Markdown", reply_markup=kb)
        context.user_data["modo_destinos_menu"] = True
        return
    if context.user_data.pop("modo_destinos_menu", False):
        # Añadir destino
        if txt == "➕ Agregar Destino":
            await update.message.reply_text("📝 Envía ID destino (–100…)", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_add_dest"] = True
        # Eliminar destino
        elif txt == "🗑️ Eliminar Destino":
            ds = conf["destinos"]
            if not ds:
                await update.message.reply_text("⚠️ No hay destinos.", reply_markup=MAIN_KB)
            else:
                lista = "\n".join(f"{i+1}. `{d}`" for i,d in enumerate(ds))
                await update.message.reply_text(f"🗑️ Destinos:\n{lista}\nEnvía nº a borrar", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
                context.user_data["modo_del_dest"] = True
        # Crear lista
        elif txt == "📁 Crear Lista":
            await update.message.reply_text("📌 Nombre de la nueva lista:", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_new_list_name"] = True
        # Gestionar listas
        elif txt == "📂 Gestionar Listas":
            lists = conf["listas_destinos"]
            if not lists:
                await update.message.reply_text("⚠️ No hay listas.", reply_markup=MAIN_KB)
            else:
                menu = [[name] for name in lists.keys()] + [["🔙 Volver"]]
                kb2 = ReplyKeyboardMarkup(menu, resize_keyboard=True)
                await update.message.reply_text("📂 *Listas Disponibles:*", parse_mode="Markdown", reply_markup=kb2)
                context.user_data["modo_manage_lists"] = True
        else:
            await update.message.reply_text("🔙 Volver", reply_markup=MAIN_KB)
        return

    # manejar añadir destino
    if context.user_data.pop("modo_add_dest", False):
        d = txt.strip()
        if d not in conf["destinos"]:
            conf["destinos"].append(d); cfg.save_config(conf)
            await update.message.reply_text(f"✅ Destino `{d}` agregado.", reply_markup=MAIN_KB)
        else:
            await update.message.reply_text("⚠️ Ya existe.", reply_markup=MAIN_KB)
        return

    # manejar eliminar destino
    if context.user_data.pop("modo_del_dest", False):
        try:
            i = int(txt)-1; d = conf["destinos"].pop(i); cfg.save_config(conf)
            await update.message.reply_text(f"✅ Destino `{d}` eliminado.", reply_markup=MAIN_KB)
        except:
            await update.message.reply_text("❌ Inválido.", reply_markup=MAIN_KB)
        return

    # crear lista: nombre ➔ ids
    if context.user_data.pop("modo_new_list_name", False):
        context.user_data["new_list_name"] = txt
        await update.message.reply_text("📋 IDs (coma o línea):", reply_markup=ReplyKeyboardRemove())
        context.user_data["modo_new_list_ids"] = True
        return
    if context.user_data.pop("modo_new_list_ids", False):
        name = context.user_data.pop("new_list_name")
        ids = [x.strip() for x in txt.replace("\n",",").split(",") if x.strip()]
        conf["listas_destinos"][name] = ids; cfg.save_config(conf)
        await update.message.reply_text(f"✅ Lista `{name}` con {len(ids)} IDs.", reply_markup=MAIN_KB)
        return

    # gestionar lista seleccionada
    if context.user_data.pop("modo_manage_lists", False):
        if txt == "🔙 Volver":
            return await update.message.reply_text("🔙 Principal", reply_markup=MAIN_KB)
        name = txt
        if name in conf["listas_destinos"]:
            kb3 = ReplyKeyboardMarkup([["📋 Ver","❌ Eliminar"],["🔙 Volver"]], resize_keyboard=True)
            context.user_data["modo_list_selected"] = name
            await update.message.reply_text(f"📂 *{name}*", parse_mode="Markdown", reply_markup=kb3)
        else:
            await update.message.reply_text("❌ No existe.", reply_markup=MAIN_KB)
        return

    if "modo_list_selected" in context.user_data:
        name = context.user_data.pop("modo_list_selected")
        if txt == "📋 Ver":
            ids = conf["listas_destinos"][name]
            await update.message.reply_text("🔍 " + "\n".join(ids), reply_markup=MAIN_KB)
        elif txt == "❌ Eliminar":
            conf["listas_destinos"].pop(name, None); cfg.save_config(conf)
            await update.message.reply_text(f"❌ Lista `{name}` borrada.", reply_markup=MAIN_KB)
        else:
            await update.message.reply_text("🔙 Principal", reply_markup=MAIN_KB)
        return

    # ─ Intervalo ─
    if txt == "🔁 Cambiar Intervalo":
        kb4 = ReplyKeyboardMarkup([["🔁 Global","✏️ Mensaje"],["📋 Lista","🔙 Volver"]], resize_keyboard=True)
        await update.message.reply_text("🕒 Modo Intervalo:", reply_markup=kb4)
        context.user_data["modo_intervalo_menu"] = True
        return
    if context.user_data.pop("modo_intervalo_menu", False):
        if txt == "🔁 Global":
            await update.message.reply_text("🕒 Nuevo global (s):", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_intervalo_global"] = True
        elif txt == "✏️ Mensaje":
            await update.message.reply_text("✏️ ID de mensaje:", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_intervalo_msg"] = True
        elif txt == "📋 Lista":
            lists = conf["listas_destinos"]
            if not lists:
                await update.message.reply_text("⚠️ No hay listas.", reply_markup=MAIN_KB)
            else:
                kb5 = ReplyKeyboardMarkup([[n] for n in lists] + [["🔙 Volver"]], resize_keyboard=True)
                await update.message.reply_text("📋 Elige Lista:", reply_markup=kb5)
                context.user_data["modo_intervalo_list_menu"] = True
        else:
            await update.message.reply_text("🔙 Principal", reply_markup=MAIN_KB)
        return

    if context.user_data.pop("modo_intervalo_global", False):
        try:
            v = int(txt); conf["intervalo_segundos"] = v; cfg.save_config(conf)
            await update.message.reply_text(f"✅ Global: {v}s", reply_markup=MAIN_KB)
        except:
            await update.message.reply_text("❌ Número inválido.", reply_markup=MAIN_KB)
        return

    if context.user_data.pop("modo_intervalo_msg", False):
        try:
            mid = int(txt)
            context.user_data["set_msg_id"] = mid
            await update.message.reply_text("🕒 Nuevo (s):", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_intervalo_msg_val"] = True
        except:
            await update.message.reply_text("❌ ID inválido.", reply_markup=MAIN_KB)
        return
    if context.user_data.pop("modo_intervalo_msg_val", False):
        try:
            v = int(txt); mid = context.user_data.pop("set_msg_id")
            ms = cfg.load_mensajes()
            for m in ms:
                if m["message_id"] == mid:
                    m["intervalo_segundos"] = v
            cfg.save_mensajes(ms)
            await update.message.reply_text(f"✅ {mid} → {v}s", reply_markup=MAIN_KB)
        except:
            await update.message.reply_text("❌ Error.", reply_markup=MAIN_KB)
        return

    if context.user_data.pop("modo_intervalo_list_menu", False):
        if txt == "🔙 Volver":
            return await update.message.reply_text("🔙 Principal", reply_markup=MAIN_KB)
        if txt in conf["listas_destinos"]:
            context.user_data["intervalo_list_name"] = txt
            await update.message.reply_text("🕒 Nuevo (s):", reply_markup=ReplyKeyboardRemove())
            context.user_data["modo_intervalo_list_val"] = True
        else:
            await update.message.reply_text("❌ No existe.", reply_markup=MAIN_KB)
        return
    if context.user_data.pop("modo_intervalo_list_val", False):
        try:
            v = int(txt); name = context.user_data.pop("intervalo_list_name")
            ms = cfg.load_mensajes()
            for m in ms:
                if m.get("dest_list") == name:
                    m["intervalo_segundos"] = v
            cfg.save_mensajes(ms)
            await update.message.reply_text(f"✅ Lista `{name}` → {v}s", reply_markup=MAIN_KB)
        except:
            await update.message.reply_text("❌ Error.", reply_markup=MAIN_KB)
        return

    # ── Mensaje reenviado: elegir todos o lista ──
    if context.user_data.get("mensaje_actual"):
        mid = context.user_data["mensaje_actual"]
        if txt == "👥 A Todos":
            ms = cfg.load_mensajes()
            for m in ms:
                if m["message_id"] == mid:
                    m["dest_all"] = True; m["dest_list"] = None
            cfg.save_mensajes(ms)
            await update.message.reply_text("✅ A todos", reply_markup=MAIN_KB)
            context.user_data.pop("mensaje_actual")
            return
        if txt == "📋 Lista":
            lists = conf["listas_destinos"]
            if not lists:
                return await update.message.reply_text("⚠️ No hay listas.", reply_markup=MAIN_KB)
            kb6 = ReplyKeyboardMarkup([[n] for n in lists]+[["🔙 Volver"]], resize_keyboard=True)
            await update.message.reply_text("📋 Elige lista:", reply_markup=kb6)
            context.user_data["modo_set_msg_list"] = True
            return
    if context.user_data.pop("modo_set_msg_list", False):
        mid = context.user_data.pop("mensaje_actual", None)
        if txt == "🔙 Volver":
            await update.message.reply_text("🔙 Principal", reply_markup=MAIN_KB)
        else:
            name = txt; ms = cfg.load_mensajes()
            for m in ms:
                if m["message_id"] == mid:
                    m["dest_all"] = False; m["dest_list"] = name
            cfg.save_mensajes(ms)
            await update.message.reply_text(f"✅ Lista `{name}`", reply_markup=MAIN_KB)
        return

    # ─ Ver Configuración ─
    if txt == "📄 Ver Configuración":
        listas = "\n".join(f"{n}: {len(l)}" for n,l in conf["listas_destinos"].items()) or "Ninguna"
        await update.message.reply_text(
            f"📄 *Actual:*\n"
            f"- Origen: `{conf['origen_chat_id']}`\n"
            f"- Destinos: {len(conf['destinos'])}\n"
            f"- Listas: {listas}\n"
            f"- Intervalo global: {conf['intervalo_segundos']}s\n"
            f"- Zona: `{conf['zone']}`",
            parse_mode="Markdown", reply_markup=MAIN_KB
        )
        return

    # desconocido
    await update.message.reply_text("🤖 Opción no reconocida.", reply_markup=MAIN_KB)
