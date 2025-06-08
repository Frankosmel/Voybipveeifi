import json
import os
import threading
import asyncio
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Flask app para compatibilidad con Autoscale
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🤖 Bot VIP está funcionando correctamente!"

@flask_app.route('/health')
def health():
    return {"status": "OK", "bot": "running"}

@flask_app.route('/status')
def status():
    vip_count = len(cargar_vip_users())
    admin_count = len(cargar_admins())
    return {
        "status": "active",
        "vip_users": vip_count,
        "admins": admin_count,
        "bot_name": "VIP Verification Bot",
        "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        "uptime": "running"
    }

@flask_app.route('/ping')
def ping():
    return {"status": "pong", "time": datetime.now().strftime('%H:%M:%S')}

@flask_app.route('/bot-status')
def bot_status():
    return {
        "bot_running": True,
        "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        "message": "Bot VIP está funcionando correctamente"
    }

# Archivos
VIP_FILE = "vip_users.json"
ADMIN_FILE = "admins.json"
BLACKLIST_FILE = "blacklist.json"


# Función para resolver conflictos de bot
def resolver_conflicto_bot():
    """Intenta resolver conflictos de instancias de bot duplicadas"""
    try:
        print("🔧 Intentando resolver conflicto de bot...")
        
        # Usar requests directamente para limpiar updates pendientes
        import requests
        
        token = "7533600198:AAEeBFnArsntb2Ahjq8Rw20e77nw0nLZ9zI"
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        
        # Obtener updates pendientes con offset alto para limpiarlos
        try:
            response = requests.get(url, params={'offset': -1, 'limit': 1, 'timeout': 1})
            if response.status_code == 200:
                print("✅ Updates pendientes limpiados")
            else:
                print(f"⚠️ Respuesta API: {response.status_code}")
        except Exception as e:
            print(f"⚠️ No se pudieron limpiar updates: {e}")
            
        print("🔧 Conflicto resuelto")
        return True
        
    except Exception as e:
        print(f"❌ Error resolviendo conflicto: {e}")
        return False


# Estados de conversación para agregar VIP, administradores y blacklist paso a paso
user_states = {}

# Cargar archivos
def cargar_admins():
    try:
        with open(ADMIN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return [1383931339]

def guardar_admins(admins):
    with open(ADMIN_FILE, "w") as f:
        json.dump(admins, f, indent=4)

def cargar_vip_users():
    try:
        with open(VIP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def guardar_vip_users(users):
    with open(VIP_FILE, "w") as f:
        json.dump(users, f, indent=4)

def buscar_vip_por_username(username):
    users = cargar_vip_users()
    # Normalizar el username de búsqueda
    search_username = username.strip().lower()
    if not search_username.startswith('@'):
        search_username = '@' + search_username
    
    for user in users:
        user_username = user.get("username", "").strip().lower()
        # Comparación directa
        if user_username == search_username:
            return user
        # Comparación sin @ al inicio si es necesario
        if user_username.lstrip('@') == search_username.lstrip('@'):
            return user
    return None

def buscar_vip_por_id(user_id):
    users = cargar_vip_users()
    for user in users:
        if user["user_id"] == user_id:
            return user
    return None

# Funciones para blacklist
def cargar_blacklist():
    try:
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def guardar_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(blacklist, f, indent=4)

def buscar_blacklist_por_username(username):
    blacklist = cargar_blacklist()
    # Normalizar el username de búsqueda
    search_username = username.strip().lower()
    if not search_username.startswith('@'):
        search_username = '@' + search_username
    
    print(f"DEBUG buscar_blacklist_por_username: Buscando '{search_username}'")
    
    for user in blacklist:
        user_username = user.get("username", "").strip().lower()
        print(f"DEBUG: Comparando '{user_username}' con '{search_username}'")
        
        # Comparación exacta
        if user_username == search_username:
            print(f"DEBUG: ¡ENCONTRADO! {user['username']}")
            return user
        
        # Comparación sin @ al inicio
        if user_username.lstrip('@') == search_username.lstrip('@'):
            print(f"DEBUG: ¡ENCONTRADO SIN @! {user['username']}")
            return user
    
    print(f"DEBUG: No encontrado en blacklist")
    return None

def mostrar_datos_completos_blacklist(user):
    """Generar mensaje con todos los datos de un usuario baneado"""
    mensaje = f"🚫 **USUARIO EN BLACKLIST - DATOS COMPLETOS**\n\n"
    mensaje += f"👤 **Información Básica:**\n"
    mensaje += f"• Username: {user.get('username', 'N/A')}\n"
    mensaje += f"• ID: `{user.get('user_id', 'N/A')}`\n"
    mensaje += f"• Estado: {user.get('estado', 'baneado').upper()}\n\n"
    
    mensaje += f"⚠️ **Motivo del Baneo:**\n"
    mensaje += f"• {user.get('motivo', 'Sin motivo especificado')}\n\n"
    
    # Mostrar todas las tarjetas
    tarjetas = user.get('tarjetas', [])
    if tarjetas and tarjetas != ['N/A']:
        mensaje += f"💳 **Tarjetas Comprometidas ({len(tarjetas)}):**\n"
        for i, tarjeta in enumerate(tarjetas, 1):
            tarjeta_str = str(tarjeta).strip()
            if tarjeta_str and tarjeta_str != 'N/A':
                # Formatear tarjeta si es un número completo
                if len(tarjeta_str) >= 16 and tarjeta_str.isdigit():
                    tarjeta_formatted = ' '.join([tarjeta_str[j:j+4] for j in range(0, len(tarjeta_str), 4)])
                    mensaje += f"   {i}. `{tarjeta_formatted}`\n"
                else:
                    mensaje += f"   {i}. `{tarjeta_str}`\n"
    else:
        mensaje += f"💳 **Tarjetas:** Sin tarjetas registradas\n"
    
    # Mostrar teléfonos
    telefono = user.get('telefono', 'N/A')
    if telefono and telefono != 'N/A':
        # Dividir por saltos de línea para múltiples teléfonos
        telefonos = telefono.split('\n')
        if len(telefonos) == 1:
            mensaje += f"\n📱 **Teléfono:** `{telefonos[0].strip()}`\n"
        else:
            mensaje += f"\n📱 **Teléfonos ({len(telefonos)}):**\n"
            for i, tel in enumerate(telefonos, 1):
                tel_clean = tel.strip()
                if tel_clean:
                    mensaje += f"   {i}. `{tel_clean}`\n"
    else:
        mensaje += f"\n📱 **Teléfono:** Sin teléfono registrado\n"
    
    # Información adicional
    info_adicional = user.get('info_adicional', 'N/A')
    if info_adicional and info_adicional != 'N/A':
        mensaje += f"\n📊 **Información Adicional:**\n"
        mensaje += f"• {info_adicional}\n"
    
    # Datos administrativos
    mensaje += f"\n📋 **Datos Administrativos:**\n"
    mensaje += f"• Baneado por: {user.get('agregado_por', 'N/A')}\n"
    mensaje += f"• Fecha de baneo: {user.get('fecha_agregado', 'N/A')}\n"
    mensaje += f"• Tipo de baneo: {user.get('tipo_baneo', 'manual')}\n\n"
    
    mensaje += f"🔴 **ADVERTENCIA: NO interactúes con este usuario**\n"
    mensaje += f"⚠️ **RIESGO DE ESTAFA CONFIRMADO**\n"
    mensaje += f"📞 **Reportar problemas:** @frankosmel"
    
    return mensaje

def mostrar_datos_limitados_blacklist(user):
    """Generar mensaje con datos limitados de un usuario baneado para usuarios normales"""
    mensaje = f"🚫 **USUARIO EN BLACKLIST**\n\n"
    mensaje += f"👤 **Información Básica:**\n"
    mensaje += f"• Username: {user.get('username', 'N/A')}\n"
    mensaje += f"• ID: `{user.get('user_id', 'N/A')}`\n"
    mensaje += f"• Estado: {user.get('estado', 'baneado').upper()}\n\n"
    
    mensaje += f"⚠️ **Motivo del Baneo:**\n"
    mensaje += f"• {user.get('motivo', 'Sin motivo especificado')}\n\n"
    
    mensaje += f"📅 **Fecha de baneo:** {user.get('fecha_agregado', 'N/A')}\n\n"
    
    mensaje += f"🔴 **ADVERTENCIA: NO interactúes con este usuario**\n"
    mensaje += f"⚠️ **RIESGO DE ESTAFA CONFIRMADO**\n"
    mensaje += f"📞 **Para más información contacta:** @frankosmel"
    
    return mensaje

def buscar_blacklist_por_id(user_id):
    try:
        blacklist = cargar_blacklist()
        print(f"DEBUG buscar_blacklist_por_id: Buscando ID {user_id} en {len(blacklist)} usuarios")
        
        for i, user in enumerate(blacklist):
            stored_id = user.get("user_id")
            print(f"DEBUG:   {i+1}. Comparando {user_id} con {stored_id} (tipo: {type(stored_id)}) - Usuario: {user.get('username', 'N/A')}")
            
            # Comparar de forma segura
            try:
                # Intentar comparación directa
                if stored_id == user_id:
                    print(f"DEBUG:   ¡ENCONTRADO (directo)! Usuario {user.get('username', 'N/A')} con ID {stored_id}")
                    return user
                
                # Comparar como strings
                if str(stored_id) == str(user_id):
                    print(f"DEBUG:   ¡ENCONTRADO (string)! Usuario {user.get('username', 'N/A')} con ID {stored_id}")
                    return user
                
                # Comparar como enteros si es posible
                if isinstance(stored_id, (int, str)) and isinstance(user_id, (int, str)):
                    if int(stored_id) == int(user_id):
                        print(f"DEBUG:   ¡ENCONTRADO (int)! Usuario {user.get('username', 'N/A')} con ID {stored_id}")
                        return user
            except (ValueError, TypeError) as e:
                print(f"DEBUG:   Error comparando IDs: {e}")
                continue
        
        print(f"DEBUG: ID {user_id} NO encontrado en blacklist")
        return None
        
    except Exception as e:
        print(f"ERROR en buscar_blacklist_por_id: {e}")
        return None

def buscar_blacklist_por_tarjeta(tarjeta):
    blacklist = cargar_blacklist()
    found_users = []
    
    # Normalizar el número de búsqueda (quitar espacios, guiones y otros caracteres)
    tarjeta_clean = ''.join(filter(str.isdigit, str(tarjeta)))
    tarjeta_original = str(tarjeta).strip()
    
    print(f"DEBUG buscar_blacklist_por_tarjeta: Buscando '{tarjeta_original}' (limpio: '{tarjeta_clean}')")
    
    for user in blacklist:
        username = user.get("username", "Sin username")
        tarjetas = user.get("tarjetas", [])
        print(f"DEBUG: Verificando usuario {username} con {len(tarjetas)} tarjetas")
        
        for i, t in enumerate(tarjetas):
            # Limpiar la tarjeta almacenada
            t_clean = ''.join(filter(str.isdigit, str(t)))
            t_original = str(t).strip()
            
            print(f"DEBUG:   Tarjeta {i+1}: '{t_original}' (limpio: '{t_clean}')")
            
            match_found = False
            match_reason = ""
            
            # 1. Coincidencia exacta (números limpios)
            if tarjeta_clean and t_clean and tarjeta_clean == t_clean:
                match_found = True
                match_reason = "coincidencia exacta"
            
            # 2. Coincidencia parcial en números limpios
            elif tarjeta_clean and t_clean and len(tarjeta_clean) >= 10 and len(t_clean) >= 10:
                if tarjeta_clean in t_clean or t_clean in tarjeta_clean:
                    match_found = True
                    match_reason = "coincidencia parcial"
            
            # 3. Formato original directo
            elif tarjeta_original == t_original:
                match_found = True
                match_reason = "formato original exacto"
            
            # 4. Últimos 4 dígitos (solo si ambos tienen al menos 4 dígitos)
            elif len(tarjeta_clean) >= 4 and len(t_clean) >= 4:
                if t_clean.endswith(tarjeta_clean[-4:]) or tarjeta_clean.endswith(t_clean[-4:]):
                    match_found = True
                    match_reason = "últimos 4 dígitos"
            
            # 5. Primeros 4 dígitos (solo si ambos tienen al menos 4 dígitos)
            elif len(tarjeta_clean) >= 4 and len(t_clean) >= 4:
                if t_clean.startswith(tarjeta_clean[:4]) or tarjeta_clean.startswith(t_clean[:4]):
                    match_found = True
                    match_reason = "primeros 4 dígitos"
            
            # 6. Formato con espacios cada 4 dígitos
            elif len(tarjeta_clean) >= 8 and len(t_clean) >= 8:
                # Convertir búsqueda a formato espaciado: 1234 5678 9012 3456
                tarjeta_spaced = ' '.join([tarjeta_clean[i:i+4] for i in range(0, len(tarjeta_clean), 4)])
                t_spaced = ' '.join([t_clean[i:i+4] for i in range(0, len(t_clean), 4)])
                if tarjeta_spaced == t_spaced or tarjeta_spaced in t_original or t_original.replace('-', ' ') == tarjeta_spaced:
                    match_found = True
                    match_reason = "formato espaciado"
            
            # 7. Formato con guiones cada 4 dígitos
            elif len(tarjeta_clean) >= 8 and len(t_clean) >= 8:
                # Convertir búsqueda a formato con guiones: 1234-5678-9012-3456
                tarjeta_dashed = '-'.join([tarjeta_clean[i:i+4] for i in range(0, len(tarjeta_clean), 4)])
                t_dashed = '-'.join([t_clean[i:i+4] for i in range(0, len(t_clean), 4)])
                if tarjeta_dashed == t_dashed or tarjeta_dashed in t_original or t_original.replace(' ', '-') == tarjeta_dashed:
                    match_found = True
                    match_reason = "formato con guiones"
            
            if match_found:
                print(f"DEBUG:     ¡MATCH ENCONTRADO! Razón: {match_reason}")
                if user not in found_users:  # Evitar duplicados
                    found_users.append(user)
                    print(f"DEBUG:     Usuario {username} agregado a resultados")
                break
            else:
                print(f"DEBUG:     No hay coincidencia")
    
    print(f"DEBUG: Total encontrados: {len(found_users)} usuarios")
    return found_users

# Obtener teclado según tipo de usuario (solo para chats privados)
def obtener_teclado_principal(user_id, chat_type="private"):
    # No mostrar teclado personalizado en grupos
    if chat_type in ["group", "supergroup", "channel"]:
        return ReplyKeyboardRemove()

    es_admin = user_id in cargar_admins()

    if es_admin:
        keyboard = [
            ["👑 ADD ADM", "💎 Gestión VIPs"],
            ["📢 Mensajes Masivos", "🚫 Blacklist"],
            ["❓ Ayuda", "📋 Comandos"], 
            ["📞 Contacto ADM", "🔍 Buscar Usuarios"],
            ["⚙️ Configuraciones"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    else:
        # Los usuarios regulares NO tienen teclado personalizado
        return ReplyKeyboardRemove()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("🔵 INICIO DEL COMANDO /start")
        
        user_id = update.effective_user.id
        username = update.effective_user.username or "Usuario"
        chat_type = update.effective_chat.type
        
        print(f"📝 Comando /start recibido:")
        print(f"   👤 Usuario: {username} (ID: {user_id})")
        print(f"   💬 Chat tipo: {chat_type}")
        print(f"   🕐 Timestamp: {datetime.now().strftime('%H:%M:%S')}")
        
        # Verificar archivos
        admins = cargar_admins()
        print(f"   👑 Administradores cargados: {len(admins)}")
        print(f"   💎 VIPs cargados: {len(cargar_vip_users())}")
        
        es_admin = user_id in admins
        es_vip = buscar_vip_por_id(user_id)
        print(f"   🔐 Es admin: {es_admin}")
        print(f"   💎 Es VIP: {bool(es_vip)}")

        mensaje = "🤖 Bot de Verificación VIP\n\n"
        mensaje += f"👋 ¡Hola @{username}!\n\n"

        # Estado del usuario
        if es_admin:
            mensaje += "👑 Estado: Administrador\n"
        elif es_vip:
            mensaje += "💎 Estado: Usuario VIP Verificado\n"
        else:
            mensaje += "👤 Estado: Usuario Regular\n"

        mensaje += "\n"

        # Mensaje diferente para grupos
        if chat_type in ["group", "supergroup"]:
            mensaje += "🔍 **Comandos disponibles en este grupo:**\n"
            mensaje += "• `/vip @usuario` - Verificar si un usuario es VIP\n"
            mensaje += "• `/start` - Ver información del bot\n\n"
            mensaje += "💡 Para funciones administrativas, escríbeme en privado.\n"
            mensaje += "📞 Contacto para ser VIP: @frankosmel"
            keyboard = ReplyKeyboardRemove()
            print("   📱 Tipo: Grupo/Supergrupo - Sin teclado personalizado")
        elif chat_type == "channel":
            mensaje += "📢 Bot de verificación VIP disponible.\n"
            mensaje += "💡 Escríbeme en privado para usar todas las funciones."
            keyboard = ReplyKeyboardRemove()
            print("   📢 Tipo: Canal - Sin teclado personalizado")
        else:
            # Chat privado
            if es_admin:
                mensaje += "👑 Panel de administración disponible\n"
                mensaje += "🔽 Utiliza los botones para gestionar el sistema:"
                print("   🔧 Creando teclado de administrador...")
            else:
                mensaje += "💡 Para obtener estatus VIP, contacta a un administrador: @frankosmel\n"
                mensaje += "📋 Comandos disponibles:\n"
                mensaje += "• `/vip @usuario` - Verificar si un usuario es VIP\n"
                mensaje += "• `/start` - Ver información del bot\n"
                mensaje += "• `/checkblacklist @usuario` - Verificar lista negra\n\n"
                mensaje += "❓ Para ayuda y más comandos usa: `/start`\n"
                mensaje += "📞 Contacto para soporte: @frankosmel"
                print("   👤 Sin teclado para usuario regular...")
            
            keyboard = obtener_teclado_principal(user_id, chat_type)
            print(f"   ⌨️ Teclado creado: {type(keyboard).__name__}")

        print("📤 Enviando respuesta...")
        await update.message.reply_text(mensaje, reply_markup=keyboard)
        print(f"✅ Respuesta enviada exitosamente a {username}")
        print("🔵 FIN DEL COMANDO /start\n")
        
    except Exception as e:
        error_msg = f"❌ ERROR CRÍTICO en comando /start: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        try:
            await update.message.reply_text("❌ Error interno del bot. Contacta al administrador.")
            print("📤 Mensaje de error enviado")
        except Exception as reply_error:
            print(f"❌ FALLO TOTAL - No se pudo enviar mensaje de error: {reply_error}")

# Handler para mensajes de texto (botones del teclado)
async def manejar_mensaje_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        texto = update.message.text
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        
        print(f"📝 Mensaje recibido: '{texto}' de usuario {user_id} en chat {chat_type}")

        # No procesar botones de teclado en grupos
        if chat_type != "private":
            print(f"🚫 Ignorando mensaje en grupo/canal")
            return
            
        # Verificar si es administrador para funciones admin
        es_admin = user_id in cargar_admins()
        
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        return

    # VERIFICACIÓN PRIORITARIA: Procesos paso a paso ANTES que cualquier otra lógica
    if user_id in user_states:
        current_state = user_states[user_id]
        print(f"DEBUG: Usuario {user_id} en estado: {current_state}")
        
        if current_state.get('adding_vip'):
            print(f"DEBUG: Procesando creación VIP para usuario {user_id}")
            await handle_vip_creation_step(update, context)
            return
        elif current_state.get('adding_admin'):
            print(f"DEBUG: Procesando creación Admin para usuario {user_id}")
            await handle_admin_creation_step(update, context)
            return
        elif current_state.get('adding_blacklist'):
            print(f"DEBUG: Procesando creación Blacklist para usuario {user_id}")
            await handle_blacklist_creation_step(update, context)
            return
        else:
            print(f"DEBUG: Estado no reconocido, limpiando: {current_state}")
            del user_states[user_id]

    # Solo procesar botones de teclado y comandos SI NO está en ningún proceso
    print(f"DEBUG: Procesando botón de teclado: '{texto}' para usuario {user_id}")
    if texto == "👑 ADD ADM":
        if user_id in cargar_admins():
            # Crear panel de administradores
            keyboard = [
                [InlineKeyboardButton("🔧 Agregar ADM Paso a Paso", callback_data="admin_add_stepbystep")],
                [InlineKeyboardButton("📋 Ver Admins", callback_data="admin_list")],
                [InlineKeyboardButton("🗑️ Eliminar Admin", callback_data="admin_remove")],
                [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
            ]

            mensaje = "👑 Panel de Administradores\n\n"
            mensaje += "🔧 Funciones disponibles:\n"
            mensaje += "• 🔧 Agregar administradores paso a paso\n"
            mensaje += "• 📋 Ver lista de administradores\n"
            mensaje += "• 🗑️ Eliminar administradores\n\n"
            mensaje += "⚠️ Solo los administradores pueden gestionar otros administradores.\n\n"
            mensaje += "🔽 Selecciona una opción:"

            await update.message.reply_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text("❌ No tienes permisos de administrador.")

    elif texto == "💎 Gestión VIPs":
        if user_id in cargar_admins():
            # Crear submenú para VIPs con botones en línea
            keyboard = [
                [
                    InlineKeyboardButton("➕ Agregar VIP", callback_data="vip_add_stepbystep"),
                    InlineKeyboardButton("📋 Ver VIPs", callback_data="vip_list"),
                    InlineKeyboardButton("🗑️ Eliminar VIP", callback_data="vip_remove")
                ],
                [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
            ]

            vip_count = len(cargar_vip_users())
            mensaje = "💎 **Gestión de Usuarios VIP**\n\n"
            mensaje += f"👥 **Total de usuarios VIP registrados:** {vip_count}\n\n"
            mensaje += "🔧 **Funciones disponibles:**\n"
            mensaje += "• ➕ **Agregar VIP:** Proceso paso a paso para nuevos usuarios\n"
            mensaje += "• 📋 **Ver VIPs:** Lista completa de usuarios verificados\n"
            mensaje += "• 🗑️ **Eliminar VIP:** Remover usuarios del sistema\n\n"
            mensaje += "⚠️ Solo los administradores pueden gestionar usuarios VIP.\n\n"
            mensaje += "🔽 **Selecciona una opción:**"

            await update.message.reply_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ No tienes permisos de administrador.")

    elif texto == "🚫 Blacklist":
        if es_admin:
            keyboard = [
                [InlineKeyboardButton("🚫 Agregar a Blacklist", callback_data="blacklist_add_stepbystep")],
                [InlineKeyboardButton("📋 Ver Blacklist", callback_data="blacklist_list")],
                [InlineKeyboardButton("🗑️ Eliminar de Blacklist", callback_data="blacklist_remove")],
                [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
            ]

            blacklist_count = len(cargar_blacklist())
            mensaje = "🚫 **Panel de Blacklist (Lista Negra)**\n\n"
            mensaje += "⚠️ **Gestión de usuarios baneados:**\n"
            mensaje += "• 🚫 Agregar usuarios problemáticos paso a paso\n"
            mensaje += "• 📋 Ver lista completa de usuarios baneados\n"
            mensaje += "• 🗑️ Eliminar usuarios de blacklist\n\n"
            mensaje += f"📊 **Usuarios baneados actualmente:** {blacklist_count}\n\n"
            mensaje += "💡 **Tip:** Usa 'Búsqueda Universal' del menú principal para buscar en todas las bases de datos\n\n"
            mensaje += "🔽 Selecciona una opción:"

            await update.message.reply_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ No tienes permisos de administrador.")

    elif texto == "📢 Mensajes Masivos":
        if user_id in cargar_admins():
            keyboard = [
                [InlineKeyboardButton("📨 Enviar a Todos los VIPs", callback_data="mass_message_vips")],
                [InlineKeyboardButton("📧 Enviar a Todos los Admins", callback_data="mass_message_admins")],
                [InlineKeyboardButton("🌐 Enviar a Todos los Usuarios", callback_data="mass_message_all")],
                [InlineKeyboardButton("📤 Mensaje Personalizado", callback_data="mass_message_custom")],
                [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
            ]

            mensaje = "📢 Sistema de Mensajes Masivos\n\n"
            mensaje += "🎯 Opciones disponibles:\n"
            mensaje += "• 📨 Enviar mensaje a todos los usuarios VIP\n"
            mensaje += "• 📧 Enviar mensaje a todos los administradores\n"
            mensaje += "• 🌐 Enviar mensaje a TODOS los usuarios (ADM + VIP + Normales)\n"
            mensaje += "• 📤 Crear mensaje personalizado\n\n"
            mensaje += "⚠️ Los mensajes masivos son poderosos, úsalos responsablemente.\n\n"
            mensaje += "🔽 Selecciona una opción:"

            await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ No tienes permisos de administrador.")

    elif texto == "❓ Ayuda":
        es_admin = user_id in cargar_admins()

        mensaje = "❓ Ayuda del Bot VIP\n\n"

        if es_admin:
            mensaje += "👑 **Funciones de Administrador:**\n"
            mensaje += "• **👑 ADD ADM** - Gestionar administradores\n"
            mensaje += "• **💎 Agregar Usuario VIP** - Gestionar usuarios VIP\n"
            mensaje += "• **📢 Mensajes Masivos** - Enviar notificaciones\n"
            mensaje += "• **🔍 Buscar Usuarios** - Buscar en la base de datos\n"
            mensaje += "• **⚙️ Configuraciones** - Ajustes del sistema\n\n"
            mensaje += "📋 **Comandos Administrativos:**\n"
            mensaje += "• `/addvip @usuario ID nombre tel mlc cup` - Agregar VIP manual\n"
            mensaje += "• `/addadmin @usuario ID` - Agregar administrador\n"
            mensaje += "• `/delvip ID` - Eliminar usuario VIP\n"
            mensaje += "• `/deladmin ID` - Eliminar administrador\n"
            mensaje += "• `/editvip ID campo valor` - Editar datos VIP\n\n"
        else:
            mensaje += "👤 **Comandos para Usuarios:**\n"
            mensaje += "• `/vip @usuario` - Verificar si un usuario es VIP\n"
            mensaje += "• `/checkblacklist @usuario` - Verificar lista negra\n"
            mensaje += "• `/start` - Ver información del bot\n\n"

        mensaje += "💡 **¿Cómo funciona el sistema VIP?**\n"
        mensaje += "Los usuarios VIP son verificados por administradores y tienen respaldo KYC completo para intercambios seguros.\n\n"
        mensaje += "📞 **¿Necesitas más ayuda?** Contacta: @frankosmel"

        await update.message.reply_text(mensaje, parse_mode='Markdown')

    elif texto == "📋 Comandos":
        es_admin = user_id in cargar_admins()

        mensaje = "📋 Lista de Comandos Disponibles\n\n"

        mensaje += "🔍 **Comandos de Verificación:**\n"
        mensaje += "• `/start` - Iniciar/reiniciar el bot\n"
        mensaje += "• `/vip @usuario` - Verificar si un usuario es VIP\n\n"

        if es_admin:
            mensaje += "👑 **Comandos de Administrador:**\n\n"
            mensaje += "**Gestión de VIPs:**\n"
            mensaje += "• `/addvip @user ID nombre tel mlc cup` - Agregar VIP\n"
            mensaje += "• `/delvip ID` - Eliminar usuario VIP\n"
            mensaje += "• `/editvip ID campo valor` - Editar datos VIP\n\n"
            mensaje += "**Gestión de Administradores:**\n"
            mensaje += "• `/addadmin @usuario ID` - Agregar administrador\n"
            mensaje += "• `/deladmin ID` - Eliminar administrador\n\n"
            mensaje += "**Gestión de Blacklist:**\n"
            mensaje += "• `/addblacklist @user ID motivo [tarjetas] [tel]` - Banear usuario\n"
            mensaje += "• `/delblacklist ID` - Quitar de blacklist\n"
            mensaje += "• `/checkblacklist @usuario` - Verificar si está baneado\n\n"
            mensaje += "**Campos editables en VIPs:**\n"
            mensaje += "• `username` - Cambiar username\n"
            mensaje += "• `nombre` - Cambiar nombre completo\n"
            mensaje += "• `telefono` - Cambiar teléfono\n"
            mensaje += "• `tarjeta_mlc` - Cambiar tarjeta MLC\n"
            mensaje += "• `tarjeta_cup` - Cambiar tarjeta CUP\n\n"
            mensaje += "📋 **Ejemplo de uso:**\n"
            mensaje += "`/editvip 1383931339 telefono 58012345`\n\n"

        mensaje += "💡 **Nota:** Los comandos administrativos solo funcionan para administradores registrados.\n\n"
        mensaje += "📞 **Soporte:** @frankosmel"

        await update.message.reply_text(mensaje, parse_mode='Markdown')

    elif texto == "📞 Contacto ADM":
        mensaje = "📞 Contacto con Administradores\n\n"
        mensaje += "👑 **Administrador Principal:**\n"
        mensaje += "• @frankosmel - Administrador principal\n"
        mensaje += "• Soporte técnico y consultas VIP\n\n"

        # Mostrar lista de administradores
        admins = cargar_admins()
        if len(admins) > 1:
            mensaje += "👥 **Otros Administradores Disponibles:**\n"
            for admin_id in admins:
                if admin_id != 1383931339:  # No mostrar el admin principal de nuevo
                    try:
                        chat = await context.bot.get_chat(admin_id)
                        username = f"@{chat.username}" if chat.username else f"ID: {admin_id}"
                        nombre = chat.full_name if chat.full_name else "Admin"
                        mensaje += f"• {username} - {nombre}\n"
                    except:
                        mensaje += f"• ID: {admin_id} - Admin\n"

        mensaje += "\n🔍 **Para qué contactar:**\n"
        mensaje += "• 💎 Solicitar estatus VIP\n"
        mensaje += "• ❓ Consultas sobre verificaciones\n"
        mensaje += "• 🚫 Reportar problemas\n"
        mensaje += "• 💡 Sugerencias y mejoras\n\n"
        mensaje += "⏰ **Horario de atención:** 24/7\n"
        mensaje += "📱 **Respuesta promedio:** 1-6 horas"

        keyboard = [
            [InlineKeyboardButton("💬 Contactar @frankosmel", url="https://t.me/frankosmel")],
            [InlineKeyboardButton("📞 Soporte Técnico", url="https://t.me/frankosmel")]
        ]

        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif texto == "🔍 Buscar Usuarios" and es_admin:
        # Solo para administradores
        keyboard = [
            [InlineKeyboardButton("🌐 Búsqueda Universal", callback_data="universal_search_start")],
            [InlineKeyboardButton("📊 Estadísticas Generales", callback_data="search_stats")]
        ]
        
        mensaje = "🔍 Sistema de Búsqueda - Modo Administrador\n\n"
        mensaje += "👑 Acceso completo a todas las bases de datos:\n"
        mensaje += "• 💎 Base de datos VIP\n"
        mensaje += "• 🚫 Base de datos Blacklist\n"
        mensaje += "• 👑 Lista de administradores\n\n"
        mensaje += "🎯 Opciones disponibles:\n"
        mensaje += "• 🌐 Búsqueda Universal: Buscar en todas las bases simultáneamente\n"
        mensaje += "• 📊 Estadísticas: Ver resumen completo del sistema\n\n"
        mensaje += "🔽 Selecciona una opción:"

        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif texto == "⚙️ Configuraciones":
        if user_id in cargar_admins():
            keyboard = [
                [InlineKeyboardButton("🛡️ Seguridad del Sistema", callback_data="config_security")],
                [InlineKeyboardButton("📝 Mensajes Automáticos", callback_data="config_messages")],
                [InlineKeyboardButton("⏰ Configurar Timeouts", callback_data="config_timeouts")],
                [InlineKeyboardButton("📊 Logs del Sistema", callback_data="config_logs")],
                [InlineKeyboardButton("🔄 Backup y Restauración", callback_data="config_backup")],
                [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
            ]

            mensaje = "⚙️ Configuraciones del Sistema\n\n"
            mensaje += "🔧 Opciones de configuración disponibles:\n"
            mensaje += "• 🛡️ Ajustes de seguridad y permisos\n"
            mensaje += "• 📝 Personalizar mensajes automáticos\n"
            mensaje += "• ⏰ Configurar tiempos de espera\n"
            mensaje += "• 📊 Gestionar logs y registros\n"
            mensaje += "• 🔄 Opciones de respaldo de datos\n\n"
            mensaje += "⚠️ Solo administradores pueden modificar configuraciones.\n\n"
            mensaje += "🔽 Selecciona una opción:"

            await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ No tienes permisos de administrador.")

    # COMANDO ESPECIAL PARA ELIMINAR ADMINISTRADOR POR USERNAME
    # Solo si NO está en ningún proceso Y el mensaje es SOLO un username Y es para eliminar admin
    elif (texto.startswith("@") and 
          user_id in cargar_admins() and 
          user_id not in user_states and 
          len(texto.strip()) > 1 and 
          not any(char.isdigit() for char in texto) and  # No contiene números (no es ID)
          texto.count('@') == 1):  # Solo contiene un @
        
        username = texto.strip().lstrip('@')
        
        # Verificar que es realmente para eliminar admin (agregar confirmación)
        print(f"DEBUG: Posible eliminación de admin: @{username}")
        
        # Buscar admin por username
        try:
            admins = cargar_admins()
            admin_encontrado = None

            for admin_id in admins:
                try:
                    chat = await context.bot.get_chat(admin_id)
                    if chat.username and chat.username.lower() == username.lower():
                        admin_encontrado = admin_id
                        break
                except:
                    continue

            if not admin_encontrado:
                return await update.message.reply_text(f"❌ No se encontró ningún administrador con username @{username}")

            if admin_encontrado == user_id:
                return await update.message.reply_text("❌ No puedes eliminarte a ti mismo como administrador.")

            # Mostrar confirmación antes de eliminar
            keyboard = [
                [InlineKeyboardButton("✅ Confirmar Eliminación", callback_data=f"confirm_delete_admin_{admin_encontrado}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_delete_admin")]
            ]
            
            mensaje = f"⚠️ **Confirmar Eliminación de Administrador**\n\n"
            mensaje += f"👤 Usuario: @{username}\n"
            mensaje += f"🆔 ID: {admin_encontrado}\n\n"
            mensaje += f"🔴 **¿Estás seguro de que quieres eliminar este administrador?**\n"
            mensaje += f"Esta acción no se puede deshacer."

            await update.message.reply_text(
                mensaje, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            print(f"❌ Error procesando eliminación de administrador: {e}")
            await update.message.reply_text("❌ Error al procesar la eliminación del administrador.")

# Funciones de administradores
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = cargar_admins()
    if update.effective_user.id not in admins:
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) != 2:
        return await update.message.reply_text("📝 Uso: /addadmin @usuario ID_telegram")

    username = context.args[0].lstrip('@')
    try:
        user_id = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ El ID debe ser un número válido.")

    if user_id in admins:
        return await update.message.reply_text("ℹ️ Este usuario ya es administrador.")

    admins.append(user_id)
    guardar_admins(admins)

    mensaje = f"✅ **Administrador Agregado**\n\n"
    mensaje += f"👤 Usuario: @{username}\n"
    mensaje += f"🆔 ID: {user_id}\n"
    mensaje += f"📅 Agregado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    mensaje += f"👑 Agregado por: @{update.effective_user.username or 'admin'}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

# Función para agregar VIP manual (con datos completos)
async def agregar_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) < 6:
        mensaje = "📝 **Para agregar VIP manual usa:**\n"
        mensaje += "`/addvip @usuario ID_telegram nombre_completo telefono tarjeta_mlc tarjeta_cup`\n\n"
        mensaje += "📋 **Ejemplo:**\n"
        mensaje += "`/addvip @frankosmel 1383931339 Frank_Del_Rio_Cambra 56246700 9235129976578315 9204129976918161`\n\n"
        mensaje += "⚠️ Todos los datos son obligatorios para crear un VIP completo"
        return await update.message.reply_text(mensaje, parse_mode='Markdown')

    username = context.args[0].lstrip('@')
    try:
        user_id = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ El ID de Telegram debe ser un número válido.")

    nombre_completo = context.args[2].replace('_', ' ')
    telefono = context.args[3]
    tarjeta_mlc = context.args[4]
    tarjeta_cup = context.args[5]

    users = cargar_vip_users()

    # Verificar si ya existe
    if buscar_vip_por_id(user_id):
        return await update.message.reply_text("❗Este usuario ya está registrado como VIP.")

    nuevo_vip = {
        "user_id": user_id,
        "username": f"@{username}",
        "kyc": "sí",
        "telegram_id": user_id,
        "telefono": telefono,
        "tarjeta_mlc": tarjeta_mlc,
        "tarjeta_cup": tarjeta_cup,
        "nombre_completo": nombre_completo,
        "agregado_por": f"@{update.effective_user.username or 'admin'}",
        "fecha_agregado": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "estado": "activo",
        "tipo_registro": "manual_admin"
    }

    users.append(nuevo_vip)
    guardar_vip_users(users)

    mensaje = f"✅ **Usuario VIP Agregado Exitosamente**\n\n"
    mensaje += f"👤 Usuario: @{username}\n"
    mensaje += f"🆔 ID: {user_id}\n"
    mensaje += f"👨‍💼 Nombre: {nombre_completo}\n"
    mensaje += f"📞 Teléfono: {telefono}\n"
    mensaje += f"💳 Tarjeta MLC: {tarjeta_mlc}\n"
    mensaje += f"💳 Tarjeta CUP: {tarjeta_cup}\n"
    mensaje += f"📅 Agregado: {nuevo_vip['fecha_agregado']}\n"
    mensaje += f"👑 Agregado por: {nuevo_vip['agregado_por']}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Notificar al usuario que fue agregado como VIP
    try:
        mensaje_notificacion = f"🎉 **¡Felicidades! Has sido agregado como Usuario VIP**\n\n"
        mensaje_notificacion += f"✅ Tu cuenta ha sido verificada por un administrador\n"
        mensaje_notificacion += f"💎 Ahora eres parte del sistema VIP de confianza\n\n"
        mensaje_notificacion += f"🔍 Los usuarios pueden verificar tu estatus usando `/vip @{username}`\n"
        mensaje_notificacion += f"🛡️ Tienes respaldo administrativo completo\n\n"
        mensaje_notificacion += f"📞 **Soporte:** @frankosmel"

        await context.bot.send_message(
            chat_id=user_id,
            text=mensaje_notificacion,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"No se pudo notificar al usuario {user_id}: {e}")

# Comando para eliminar administrador
async def eliminar_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) != 1:
        return await update.message.reply_text("📝 Uso: /deladmin ID_telegram\n\nEjemplo: /deladmin 1383931339")

    try:
        user_id_to_remove = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ El ID debe ser un número válido.")

    # No permitir auto-eliminación
    if user_id_to_remove == update.effective_user.id:
        return await update.message.reply_text("❌ No puedes eliminarte a ti mismo como administrador.")

    admins = cargar_admins()

    if user_id_to_remove not in admins:
        return await update.message.reply_text("ℹ️ Este usuario no es administrador.")

    admins.remove(user_id_to_remove)
    guardar_admins(admins)

    mensaje = f"✅ **Administrador Eliminado**\n\n"
    mensaje += f"🆔 ID eliminado: {user_id_to_remove}\n"
    mensaje += f"📅 Eliminado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    mensaje += f"👤 Eliminado por: @{update.effective_user.username or 'admin'}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Notificar al usuario eliminado
    try:
        mensaje_notificacion = f"⚠️ **Cambio en tu Estatus Administrativo**\n\n"
        mensaje_notificacion += f"🚫 Tu acceso como administrador ha sido revocado\n"
        mensaje_notificacion += f"📅 Revocado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        mensaje_notificacion += f"❓ Si tienes dudas, contacta: @frankosmel"

        await context.bot.send_message(
            chat_id=user_id_to_remove,
            text=mensaje_notificacion,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"No se pudo notificar al usuario {user_id_to_remove}: {e}")

# Comando para eliminar VIP
async def eliminar_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) != 1:
        return await update.message.reply_text("📝 Uso: /delvip ID_telegram\n\nEjemplo: /delvip 1383931339")

    try:
        user_id_to_remove = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ El ID debe ser un número válido.")

    users = cargar_vip_users()
    vip_to_remove = buscar_vip_por_id(user_id_to_remove)

    if not vip_to_remove:
        return await update.message.reply_text("ℹ️ Este usuario no está registrado como VIP.")

    # Eliminar el usuario VIP
    users = [user for user in users if user['user_id'] != user_id_to_remove]
    guardar_vip_users(users)

    mensaje = f"✅ **Usuario VIP Eliminado**\n\n"
    mensaje += f"👤 Usuario: {vip_to_remove['username']}\n"
    mensaje += f"🆔 ID: {user_id_to_remove}\n"
    mensaje += f"👨‍💼 Nombre: {vip_to_remove.get('nombre_completo', 'N/A')}\n"
    mensaje += f"📅 Eliminado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    mensaje += f"👤 Eliminado por: @{update.effective_user.username or 'admin'}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Notificar al usuario
    try:
        mensaje_notificacion = f"⚠️ **Cambio en tu Estatus VIP**\n\n"
        mensaje_notificacion += f"🚫 Tu estatus VIP ha sido revocado\n"
        mensaje_notificacion += f"📅 Revocado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        mensaje_notificacion += f"❓ Si tienes dudas, contacta: @frankosmel"

        await context.bot.send_message(
            chat_id=user_id_to_remove,
            text=mensaje_notificacion,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"No se pudo notificar al usuario {user_id_to_remove}: {e}")

# Comando para editar VIP
async def editar_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) != 3:
        mensaje = "📝 **Uso:** /editvip ID_usuario campo nuevo_valor\n\n"
        mensaje += "📋 **Campos editables:**\n"
        mensaje += "• username - Cambiar username\n"
        mensaje += "• nombre - Cambiar nombre completo\n"
        mensaje += "• telefono - Cambiar teléfono\n"
        mensaje += "• tarjeta_mlc - Cambiar tarjeta MLC\n"
        mensaje += "• tarjeta_cup - Cambiar tarjeta CUP\n\n"
        mensaje += "📋 **Ejemplo:**\n"
        mensaje += "/editvip 1383931339 telefono 58012345"
        return await update.message.reply_text(mensaje, parse_mode='Markdown')

    try:
        user_id_to_edit = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ El ID debe ser un número válido.")

    campo = context.args[1].lower()
    nuevo_valor = context.args[2]

    campos_validos = ['username', 'nombre', 'telefono', 'tarjeta_mlc', 'tarjeta_cup']
    if campo not in campos_validos:
        return await update.message.reply_text(f"❌ Campo inválido. Campos permitidos: {', '.join(campos_validos)}")

    users = cargar_vip_users()
    vip_to_edit = buscar_vip_por_id(user_id_to_edit)

    if not vip_to_edit:
        return await update.message.reply_text("ℹ️ Este usuario no está registrado como VIP.")

    # Guardar valor anterior para el mensaje
    valor_anterior = vip_to_edit.get(campo if campo != 'nombre' else 'nombre_completo', 'N/A')

    # Actualizar el campo
    for user in users:
        if user['user_id'] == user_id_to_edit:
            if campo == 'nombre':
                user['nombre_completo'] = nuevo_valor.replace('_', ' ')
            else:
                user[campo] = nuevo_valor
            break

    guardar_vip_users(users)

    mensaje = f"✅ **Usuario VIP Editado**\n\n"
    mensaje += f"👤 Usuario: {vip_to_edit['username']}\n"
    mensaje += f"🆔 ID: {user_id_to_edit}\n"
    mensaje += f"📝 Campo: {campo}\n"
    mensaje += f"📄 Valor anterior: {valor_anterior}\n"
    mensaje += f"📄 Valor nuevo: {nuevo_valor}\n"
    mensaje += f"📅 Editado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    mensaje += f"👤 Editado por: @{update.effective_user.username or 'admin'}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Notificar al usuario
    try:
        mensaje_notificacion = f"ℹ️ **Actualización en tu Perfil VIP**\n\n"
        mensaje_notificacion += f"📝 Campo actualizado: {campo}\n"
        mensaje_notificacion += f"📄 Nuevo valor: {nuevo_valor}\n"
        mensaje_notificacion += f"📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        mensaje_notificacion += f"💎 Tu estatus VIP sigue activo\n"
        mensaje_notificacion += f"❓ Si tienes dudas, contacta: @frankosmel"

        await context.bot.send_message(
            chat_id=user_id_to_edit,
            text=mensaje_notificacion,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"No se pudo notificar al usuario {user_id_to_edit}: {e}")

# Comando de diagnóstico para administradores
async def diagnostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Sin username"
    
    try:
        vip_users = cargar_vip_users()
        admins = cargar_admins()
        
        mensaje = "🔧 **Diagnóstico del Sistema**\n\n"
        mensaje += f"👤 **Usuario solicitante:**\n"
        mensaje += f"• ID: {user_id}\n"
        mensaje += f"• Username: @{username}\n"
        mensaje += f"• Es Admin: {'✅ SÍ' if user_id in admins else '❌ NO'}\n\n"
        
        mensaje += f"📊 **Estado actual:**\n"
        mensaje += f"• VIPs registrados: {len(vip_users)}\n"
        mensaje += f"• Administradores: {len(admins)}\n"
        mensaje += f"• Estados de conversación activos: {len(user_states)}\n\n"
        
        mensaje += f"👑 **Lista de Administradores:**\n"
        for i, admin_id in enumerate(admins, 1):
            try:
                if admin_id == 1383931339:
                    mensaje += f"• {i}. ID: {admin_id} (TÚ - Admin Principal) ✅\n"
                else:
                    mensaje += f"• {i}. ID: {admin_id}\n"
            except:
                mensaje += f"• {i}. ID: {admin_id}\n"
        
        mensaje += f"\n🎯 **Archivos del sistema:**\n"
        mensaje += f"• vip_users.json: {'✅' if os.path.exists('vip_users.json') else '❌'}\n"
        mensaje += f"• admins.json: {'✅' if os.path.exists('admins.json') else '❌'}\n\n"
        
        mensaje += f"🔄 **Bot Status:** Funcionando ✅\n"
        mensaje += f"📅 **Última verificación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Error en diagnóstico: {str(e)}"
        print(error_msg)
        await update.message.reply_text(error_msg)

# Comando /vip - función principal de verificación (accesible para todos)
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    
    # Detectar si el comando fue usado incorrectamente como /vip@usuario
    command_text = update.message.text or ""
    if "@" in command_text and len(context.args) == 0:
        # El usuario escribió algo como /vip@usuario en lugar de /vip @usuario
        mensaje = "📝 **Uso correcto del comando /vip:**\n\n"
        mensaje += "`/vip @usuario` o `/vip usuario`\n\n"
        mensaje += "📋 **Ejemplos:**\n"
        mensaje += "• `/vip @frankosmel`\n"
        mensaje += "• `/vip frankosmel` (sin @)\n\n"
        mensaje += "⚠️ **Error detectado:** Usar espacio entre `/vip` y `@usuario`"
        
        # Enviar mensaje y programar eliminación automática
        sent_message = await update.message.reply_text(mensaje, parse_mode='Markdown')
        
        # Programar eliminación del mensaje después de 25 segundos
        async def delete_message():
            try:
                await asyncio.sleep(25)
                await sent_message.delete()
            except Exception as e:
                print(f"No se pudo eliminar el mensaje: {e}")
        
        # Ejecutar eliminación en segundo plano
        asyncio.create_task(delete_message())
        return

    if len(context.args) != 1 or not context.args[0].strip():
        mensaje = "📝 **Uso correcto del comando /vip:**\n\n"
        mensaje += "`/vip @usuario` o `/vip usuario`\n\n"
        mensaje += "📋 **Ejemplos:**\n"
        mensaje += "• `/vip @frankosmel`\n"
        mensaje += "• `/vip frankosmel` (sin @)"
        
        # Enviar mensaje y programar eliminación automática
        sent_message = await update.message.reply_text(mensaje, parse_mode='Markdown')
        
        # Programar eliminación del mensaje después de 25 segundos
        async def delete_message():
            try:
                await asyncio.sleep(25)
                await sent_message.delete()
            except Exception as e:
                print(f"No se pudo eliminar el mensaje: {e}")
        
        # Ejecutar eliminación en segundo plano
        asyncio.create_task(delete_message())
        return

    # Normalizar el username (agregar @ si no lo tiene)
    username_input = context.args[0]
    if username_input.startswith('@'):
        username = username_input.lstrip('@')
        username_search = username_input
    else:
        username = username_input
        username_search = f"@{username}"

    print(f"DEBUG /vip: Input='{username_input}', username='{username}', search='{username_search}'")

    # Verificar primero en blacklist
    blacklist_user = buscar_blacklist_por_username(username_search)
    if blacklist_user:
        mensaje = f"🚫 **@{username} está en la BLACKLIST**\n\n"
        mensaje += f"⚠️ **USUARIO BANEADO** ⚠️\n\n"
        mensaje += f"🆔 ID: {blacklist_user['user_id']}\n"
        mensaje += f"⚠️ Motivo: {blacklist_user.get('motivo', 'N/A')}\n"
        mensaje += f"📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n\n"
        mensaje += f"🔴 **NO interactúes con este usuario**\n"
        mensaje += f"⚠️ **RIESGO DE ESTAFA**"
        return await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Buscar en VIP
    vip_user = buscar_vip_por_username(username_search)

    if not vip_user:
        mensaje = f"❌ **{username_search} no está registrado como VIP.**\n\n"
        mensaje += "🔍 **Alternativas:**\n"
        mensaje += "• Usuario no verificado\n"
        mensaje += "• Revisar ortografía del username\n\n"
        mensaje += "💡 Para obtener verificación VIP contacta: @frankosmel"

        return await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Usuario VIP encontrado - mostrar información con botones de verificación
    mensaje = f"✅ **Usuario VIP confirmado**\n\n"
    mensaje += f"📋 **Información básica:**\n"
    mensaje += f"🆔 ID Telegram: `{vip_user['user_id']}`\n"
    mensaje += f"👤 Usuario: {vip_user['username']}\n"
    mensaje += f"🔐 KYC: Verificado ✅\n"
    mensaje += f"📅 Registrado: {vip_user.get('fecha_agregado', 'N/A')}\n\n"
    mensaje += f"💎 **Usuario de confianza verificado**\n"
    mensaje += f"🛡️ **Respaldo administrativo completo**\n\n"
    mensaje += f"👤 Verificación solicitada por: @{update.effective_user.username or 'Usuario'}\n\n"
    mensaje += f"⚠️ **Solo {vip_user['username']} puede confirmar esta verificación**"

    # Crear botones de verificación
    keyboard = [
        [InlineKeyboardButton("✅ Aceptar", callback_data=f"aceptar_{vip_user['user_id']}")],
        [InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{vip_user['user_id']}")]
    ]

    await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Función para manejar submenús de administración (solo VIP)
async def admin_submenu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # Verificar permisos de administrador
    if user_id not in cargar_admins():
        await query.edit_message_text("❌ No tienes permisos de administrador.")
        return

    # Handlers para administradores
    if data == "admin_add_stepbystep":
        # Iniciar proceso paso a paso de agregar admin
        user_states[user_id] = {
            'adding_admin': True,
            'step': 'username',
            'data': {}
        }

        mensaje = "🔧 Proceso de Agregar Administrador - Paso 1/2\n\n"
        mensaje += "👤 Ingresa el username del usuario:\n"
        mensaje += "• Ejemplo: @frankosmel\n"
        mensaje += "• No olvides incluir el @\n\n"
        mensaje += "📝 Escribe el username a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_admin_creation")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_list":
        admins = cargar_admins()
        mensaje = "📋 Lista de Administradores\n\n"

        if not admins:
            mensaje += "❌ No hay administradores registrados."
        else:
            mensaje += f"👑 Total de administradores: {len(admins)}\n\n"
            for i, admin_id in enumerate(admins, 1):
                try:
                    # Intentar obtener información del administrador
                    chat = await context.bot.get_chat(admin_id)
                    username = f"@{chat.username}" if chat.username else "Sin username"
                    nombre = chat.full_name if chat.full_name else "Sin nombre"

                    mensaje += f"{i}. {nombre}\n"
                    mensaje += f"   👤 {username}\n"
                    mensaje += f"   🆔 ID: {admin_id}\n\n"
                except Exception:
                    mensaje += f"{i}. Admin ID: {admin_id}\n"
                    mensaje += f"   ⚠️ No se pudo obtener información\n\n"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="admin_panel")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_remove":
        mensaje = "🗑️ Eliminar Administrador\n\n"
        mensaje += "📝 Instrucciones:\n"
        mensaje += "Para eliminar un administrador tienes 2 opciones:\n\n"
        mensaje += "1️⃣ **Por username:** Envía solo el username\n"
        mensaje += "   • Ejemplo: @frankosmel\n\n"
        mensaje += "2️⃣ **Por comando:** Usa el comando completo\n"
        mensaje += "   • Ejemplo: `/deladmin 1383931339`\n\n"
        mensaje += "⚠️ **Advertencias:**\n"
        mensaje += "• Esta acción es irreversible\n"
        mensaje += "• No puedes eliminarte a ti mismo\n"
        mensaje += "• El usuario será notificado del cambio\n\n"
        mensaje += "💡 **Tip:** Usa la lista de administradores para ver los IDs disponibles"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="admin_panel")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))



    elif data == "vip_list":
        vip_users = cargar_vip_users()
        mensaje = "📋 Lista de Usuarios VIP\n\n"

        if not vip_users:
            mensaje += "❌ No hay usuarios VIP registrados."
        else:
            mensaje += f"💎 Total de usuarios VIP: {len(vip_users)}\n\n"
            for i, vip in enumerate(vip_users, 1):
                nombre = vip.get('nombre_completo', 'Sin nombre')
                username = vip.get('username', 'Sin username')
                user_id = vip.get('user_id', 'Sin ID')
                telefono = vip.get('telefono', 'N/A')
                fecha = vip.get('fecha_agregado', 'N/A')

                mensaje += f"{i}. {nombre}\n"
                mensaje += f"   👤 {username}\n"
                mensaje += f"   🆔 ID: {user_id}\n"
                mensaje += f"   📞 Tel: {telefono}\n"
                mensaje += f"   📅 Agregado: {fecha}\n\n"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="vip_panel")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "vip_add_stepbystep":
        mensaje = "🔧 **Agregar VIP Paso a Paso**\n\n"
        mensaje += "📝 **Este modo te guiará paso a paso para agregar un usuario VIP:**\n\n"
        mensaje += "✅ **Ventajas:**\n"
        mensaje += "• Interfaz guiada y fácil de usar\n"
        mensaje += "• Validación automática de datos\n"
        mensaje += "• Menos posibilidad de errores\n"
        mensaje += "• Confirmación antes de guardar\n\n"
        mensaje += "🔽 **Para continuar, presiona 'Iniciar Proceso'**"

        keyboard = [
            [InlineKeyboardButton("🚀 Iniciar Proceso", callback_data="start_vip_creation")],
            [InlineKeyboardButton("🔙 Volver", callback_data="vip_panel")]
        ]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "vip_remove":
        mensaje = "🗑️ **Eliminar Usuario VIP**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "Para eliminar un usuario VIP usa el comando:\n"
        mensaje += "`/delvip ID_telegram`\n\n"
        mensaje += "📋 **Ejemplo:**\n"
        mensaje += "`/delvip 1383931339`\n\n"
        mensaje += "⚠️ **Advertencias:**\n"
        mensaje += "• Esta acción es irreversible\n"
        mensaje += "• El usuario perderá su estatus VIP\n"
        mensaje += "• Se eliminará toda su información del sistema\n"
        mensaje += "• El usuario será notificado del cambio\n\n"
        mensaje += "💡 **Tip:** Usa la lista de VIPs para ver los IDs disponibles"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="vip_panel")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "admin_panel":
        # Volver al panel de administradores
        keyboard = [
            [InlineKeyboardButton("🔧 Agregar ADM Paso a Paso", callback_data="admin_add_stepbystep")],
            [InlineKeyboardButton("📋 Ver Admins", callback_data="admin_list")],
            [InlineKeyboardButton("🗑️ Eliminar Admin", callback_data="admin_remove")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
        ]

        mensaje = "👑 *Panel de Administradores*\n\n"
        mensaje += "🔧 *Funciones disponibles:*\n"
        mensaje += "• 🔧 Agregar administradores paso a paso\n"
        mensaje += "• 📋 Ver lista de administradores\n"
        mensaje += "• 🗑️ Eliminar administradores\n\n"
        mensaje += "🔽 *Selecciona una opción:*"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "vip_panel":
        # Volver al panel de VIPs
        keyboard = [
            [InlineKeyboardButton("🔧 Agregar VIP Paso a Paso", callback_data="vip_add_stepbystep")],
            [InlineKeyboardButton("📋 Ver VIPs", callback_data="vip_list")],
            [InlineKeyboardButton("🗑️ Eliminar VIP", callback_data="vip_remove")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
        ]

        mensaje = "💎 Panel de Usuarios VIP\n\n"
        mensaje += "🔧 Funciones disponibles:\n"
        mensaje += "• 🔧 Agregar usuarios VIP paso a paso\n"
        mensaje += "• 📋 Ver lista de usuarios VIP\n"
        mensaje += "• 🗑️ Eliminar usuarios VIP\n\n"
        mensaje += "🔽 Selecciona una opción:"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "menu_principal":
        # Volver al menú principal con teclado
        keyboard = obtener_teclado_principal(user_id, "private")
        mensaje = "🔙 **Menú Principal**\n\n"
        mensaje += "👑 Administrador: Panel principal restaurado\n"
        mensaje += "🔽 Utiliza los botones para gestionar el sistema:"

        await query.edit_message_text(mensaje, parse_mode='Markdown')
        # Enviar un nuevo mensaje con el teclado del menú principal
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="🏠 **Panel de Administración**\n\nUsa los botones para gestionar:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    # Handlers para mensajes masivos
    elif data == "mass_message_vips":
        mensaje = "📨 Enviar Mensaje a Todos los VIPs\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "1. Escribe tu mensaje a continuación\n"
        mensaje += "2. El mensaje se enviará a todos los usuarios VIP registrados\n"
        mensaje += "3. Incluye emojis y formato si deseas\n\n"
        mensaje += "⚠️ **Importante:**\n"
        mensaje += "• El mensaje no se puede cancelar una vez enviado\n"
        mensaje += "• Sé claro y profesional\n"
        mensaje += "• Evita spam o mensajes innecesarios\n\n"
        mensaje += "✏️ **Escribe tu mensaje ahora:**"

        # Iniciar estado para mensaje masivo
        user_states[user_id] = {'mass_message': True, 'type': 'vips'}

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mass_message")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "mass_message_admins":
        mensaje = "📧 Enviar Mensaje a Todos los Administradores\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "1. Escribe tu mensaje a continuación\n"
        mensaje += "2. El mensaje se enviará a todos los administradores\n"
        mensaje += "3. Ideal para notificaciones importantes\n\n"
        mensaje += "⚠️ **Importante:**\n"
        mensaje += "• Solo para asuntos administrativos\n"
        mensaje += "• El mensaje no se puede cancelar una vez enviado\n\n"
        mensaje += "✏️ **Escribe tu mensaje ahora:**"

        user_states[user_id] = {'mass_message': True, 'type': 'admins'}

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mass_message")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "mass_message_all":
        mensaje = "🌐 Enviar Mensaje a TODOS los Usuarios\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "1. Escribe tu mensaje a continuación\n"
        mensaje += "2. El mensaje se enviará a TODOS los usuarios:\n"
        mensaje += "   • 👑 Administradores\n"
        mensaje += "   • 💎 Usuarios VIP\n"
        mensaje += "   • 👤 Usuarios normales registrados\n\n"
        mensaje += "⚠️ **ADVERTENCIA:**\n"
        mensaje += "• Este es el mensaje más masivo posible\n"
        mensaje += "• Se enviará a TODA la base de usuarios\n"
        mensaje += "• Úsalo solo para anuncios muy importantes\n"
        mensaje += "• El mensaje NO se puede cancelar una vez enviado\n\n"
        mensaje += "✏️ **Escribe tu mensaje ahora:**"

        user_states[user_id] = {'mass_message': True, 'type': 'all_users'}

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mass_message")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "cancel_mass_message":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Mensaje masivo cancelado**\n\nNo se envió ningún mensaje.", parse_mode='Markdown')

    # Handlers para menús de búsqueda VIP
    elif data == "vip_search_menu":
        keyboard = [
            [InlineKeyboardButton("👤 Buscar VIP por @usuario", callback_data="vip_search_by_username")],
            [InlineKeyboardButton("🆔 Buscar VIP por ID", callback_data="vip_search_by_id")],
            [InlineKeyboardButton("📊 Estadísticas VIP", callback_data="vip_search_stats")],
            [InlineKeyboardButton("🔙 Volver", callback_data="main_search_menu")]
        ]

        mensaje = "💎 **Búsqueda en Base de Datos VIP**\n\n"
        mensaje += "🎯 **Buscar solo en usuarios VIP verificados:**\n"
        mensaje += "• 👤 **Por @usuario:** Buscar username específico en VIPs\n"
        mensaje += "• 🆔 **Por ID:** Buscar ID de Telegram en VIPs\n"
        mensaje += "• 📊 **Estadísticas:** Ver información de usuarios VIP\n\n"
        mensaje += f"💎 **Total de usuarios VIP registrados:** {len(cargar_vip_users())}\n\n"
        mensaje += "🔽 **Selecciona el tipo de búsqueda VIP:**"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_main_menu":
        keyboard = [
            [InlineKeyboardButton("🆔 Buscar Blacklist por ID", callback_data="blacklist_search_by_id")],
            [InlineKeyboardButton("👤 Buscar Blacklist por @usuario", callback_data="blacklist_search_by_username")],
            [InlineKeyboardButton("📞 Buscar Blacklist por Teléfono", callback_data="blacklist_search_by_phone")],
            [InlineKeyboardButton("💳 Buscar Blacklist por Tarjeta", callback_data="blacklist_search_by_card")],
            [InlineKeyboardButton("📊 Estadísticas Blacklist", callback_data="blacklist_search_stats")],
            [InlineKeyboardButton("🔙 Volver", callback_data="main_search_menu")]
        ]

        mensaje = "🚫 **Búsqueda en Base de Datos Blacklist**\n\n"
        mensaje += "⚠️ **Buscar solo en usuarios baneados:**\n"
        mensaje += "• 🆔 **Por ID:** Buscar ID de Telegram en blacklist\n"
        mensaje += "• 👤 **Por @usuario:** Buscar username en blacklist\n"
        mensaje += "• 📞 **Por Teléfono:** Buscar número telefónico en blacklist\n"
        mensaje += "• 💳 **Por Tarjeta:** Buscar número de tarjeta en blacklist\n"
        mensaje += "• 📊 **Estadísticas:** Ver información de usuarios baneados\n\n"
        mensaje += f"🚫 **Total de usuarios baneados:** {len(cargar_blacklist())}\n\n"
        mensaje += "🔽 **Selecciona el tipo de búsqueda en Blacklist:**"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "main_search_menu":
        # Volver al menú principal de búsqueda simplificado
        if user_id in cargar_admins():
            keyboard = [
                [InlineKeyboardButton("🌐 Búsqueda Universal", callback_data="universal_search_start")],
                [InlineKeyboardButton("📊 Estadísticas Generales", callback_data="search_stats")]
            ]
            mensaje = "🔍 Sistema de Búsqueda - Modo Administrador\n\n"
            mensaje += "👑 Acceso completo a todas las bases de datos\n\n"
            mensaje += "🔽 Selecciona una opción:"
        else:
            keyboard = [
                [InlineKeyboardButton("🌐 Búsqueda Universal", callback_data="universal_search_start")],
                [InlineKeyboardButton("📊 Estadísticas", callback_data="search_stats")]
            ]
            mensaje = "🔍 Sistema de Búsqueda de Usuarios\n\n"
            mensaje += "👤 Búsqueda en el sistema VIP\n\n"
            mensaje += "🔽 Selecciona una opción:"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    # Handlers específicos para búsqueda VIP
    elif data == "vip_search_by_username":
        mensaje = "👤 **Buscar VIP por Username**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el username a buscar\n"
        mensaje += "• Ejemplo: @frankosmel\n"
        mensaje += "• No olvides incluir el @\n\n"
        mensaje += "🔍 **Se buscará solo en la base de datos VIP**\n\n"
        mensaje += "📝 **Escribe el username:**"

        user_states[user_id] = {'searching_vip': True, 'search_type': 'username'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "vip_search_by_id":
        mensaje = "🆔 **Buscar VIP por ID**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el ID de Telegram\n"
        mensaje += "• Ejemplo: 1383931339\n"
        mensaje += "• Solo números\n\n"
        mensaje += "🔍 **Se buscará solo en la base de datos VIP**\n\n"
        mensaje += "📝 **Escribe el ID:**"

        user_states[user_id] = {'searching_vip': True, 'search_type': 'id'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "vip_search_stats":
        vip_users = cargar_vip_users()
        mensaje = "📊 **Estadísticas de Base de Datos VIP**\n\n"
        mensaje += f"💎 **Total de usuarios VIP:** {len(vip_users)}\n\n"

        if vip_users:
            # Estadísticas por fecha
            fechas = {}
            for vip in vip_users:
                fecha = vip.get('fecha_agregado', 'N/A')
                if fecha != 'N/A':
                    fecha_solo = fecha.split(' ')[0]
                    fechas[fecha_solo] = fechas.get(fecha_solo, 0) + 1

            mensaje += f"📅 **Registros VIP por fecha (últimos 5):**\n"
            for fecha, cantidad in list(fechas.items())[-5:]:
                mensaje += f"• {fecha}: {cantidad} usuarios\n"

            # Mostrar algunos VIPs
            mensaje += f"\n👥 **Últimos VIPs registrados:**\n"
            for i, vip in enumerate(vip_users[-3:], 1):
                mensaje += f"{i}. {vip.get('username', 'N/A')} - {vip.get('fecha_agregado', 'N/A')}\n"

        mensaje += f"\n🕐 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="vip_search_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "cancel_vip_search":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Búsqueda VIP cancelada**", parse_mode='Markdown')

    # Handlers específicos para búsqueda Blacklist (actualizados)
    elif data == "blacklist_search_by_id":
        mensaje = "🆔 **Buscar en Blacklist por ID**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el ID de Telegram\n"
        mensaje += "• Ejemplo: 1383931339\n"
        mensaje += "• Solo números\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el ID:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'id'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_by_username":
        mensaje = "👤 **Buscar en Blacklist por Username**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el username a buscar\n"
        mensaje += "• Ejemplo: @usuario_problematico\n"
        mensaje += "• No olvides incluir el @\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el username:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'username'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_by_phone":
        mensaje = "📱 **Buscar en Blacklist por Teléfono**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el número de teléfono\n"
        mensaje += "• Ejemplo: 56246700 o +5356246700\n"
        mensaje += "• Con o sin código de país\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el teléfono:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'phone'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_by_card":
        mensaje = "💳 **Buscar en Blacklist por Tarjeta**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el número de tarjeta\n"
        mensaje += "• Ejemplo: 9235129976578315\n"
        mensaje += "• Puede ser parcial (últimos 4 dígitos)\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el número de tarjeta:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'card'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_stats":
        blacklist = cargar_blacklist()
        mensaje = "📊 **Estadísticas de Base de Datos Blacklist**\n\n"
        mensaje += f"🚫 **Total de usuarios baneados:** {len(blacklist)}\n\n"

        if blacklist:
            # Estadísticas por motivo
            motivos = {}
            for user in blacklist:
                motivo = user.get('motivo', 'Sin motivo')
                motivos[motivo] = motivos.get(motivo, 0) + 1

            mensaje += f"📋 **Motivos de baneo (top 3):**\n"
            for motivo, cantidad in list(motivos.items())[:3]:
                mensaje += f"• {motivo}: {cantidad} usuarios\n"

            # Estadísticas por fecha
            fechas = {}
            for user in blacklist:
                fecha = user.get('fecha_agregado', 'N/A')
                if fecha != 'N/A':
                    fecha_solo = fecha.split(' ')[0]
                    fechas[fecha_solo] = fechas.get(fecha_solo, 0) + 1

            mensaje += f"\n📅 **Baneos por fecha (últimos 3):**\n"
            for fecha, cantidad in list(fechas.items())[-3:]:
                mensaje += f"• {fecha}: {cantidad} usuarios\n"

        mensaje += f"\n🕐 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="blacklist_search_main_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "search_stats":
        vip_users = cargar_vip_users()
        admins = cargar_admins()

        mensaje = "📊 Estadísticas del Sistema\n\n"
        mensaje += f"👥 **Usuarios Registrados:**\n"
        mensaje += f"• 💎 Usuarios VIP: {len(vip_users)}\n"
        mensaje += f"• 👑 Administradores: {len(admins)}\n"
        mensaje += f"• 📊 Total usuarios: {len(vip_users) + len(admins)}\n\n"

        if vip_users:
            # Estadísticas por fecha
            fechas = {}
            for vip in vip_users:
                fecha = vip.get('fecha_agregado', 'N/A')
                if fecha != 'N/A':
                    fecha_solo = fecha.split(' ')[0]  # Solo la fecha, sin hora
                    fechas[fecha_solo] = fechas.get(fecha_solo, 0) + 1

            mensaje += f"📅 **Registros por fecha (últimos 5):**\n"
            for fecha, cantidad in list(fechas.items())[-5:]:
                mensaje += f"• {fecha}: {cantidad} usuarios\n"

        mensaje += f"\n🕐 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="search_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "cancel_search":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Búsqueda cancelada**", parse_mode='Markdown')

    # Handlers para configuraciones
    elif data == "config_security":
        mensaje = "🛡️ Configuraciones de Seguridad\n\n"
        mensaje += "🔒 **Estado actual del sistema:**\n"
        mensaje += "• ✅ Verificación de administradores activa\n"
        mensaje += "• ✅ Validación de usuarios VIP activa\n"
        mensaje += "• ✅ Control de acceso por permisos\n"
        mensaje += "• ✅ Logs de actividad habilitados\n\n"
        mensaje += "⚙️ **Configuraciones disponibles:**\n"
        mensaje += "• Todas las configuraciones de seguridad están optimizadas\n"
        mensaje += "• Solo administradores pueden acceder a funciones críticas\n"
        mensaje += "• Sistema de verificación en múltiples capas\n\n"
        mensaje += "🔧 **Para cambios de seguridad contacta:** @frankosmel"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="config_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "config_logs":
        mensaje = "📊 Logs del Sistema\n\n"
        mensaje += "📝 **Registros disponibles:**\n"
        mensaje += f"• Usuarios VIP registrados: {len(cargar_vip_users())}\n"
        mensaje += f"• Administradores activos: {len(cargar_admins())}\n"
        mensaje += f"• Última actividad: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        mensaje += "🔍 **Actividad reciente:**\n"
        mensaje += "• Sistema funcionando correctamente\n"
        mensaje += "• Base de datos actualizada\n"
        mensaje += "• Verificaciones VIP operativas\n\n"
        mensaje += "💾 **Los logs se guardan automáticamente**"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="config_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    # Navegación de menús
    elif data == "search_menu":
        keyboard = [
            [InlineKeyboardButton("👤 Buscar por Username", callback_data="search_by_username")],
            [InlineKeyboardButton("🆔 Buscar por ID", callback_data="search_by_id")],
            [InlineKeyboardButton("📞 Buscar por Teléfono", callback_data="search_by_phone")],
            [InlineKeyboardButton("💳 Buscar por Tarjeta", callback_data="search_by_card")],
            [InlineKeyboardButton("📊 Estadísticas Generales", callback_data="search_stats")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
        ]

        mensaje = "🔍 Sistema de Búsqueda de Usuarios\n\n"
        mensaje += "🎯 Opciones de búsqueda disponibles:\n"
        mensaje += "• 👤 Buscar por username (@usuario)\n"
        mensaje += "• 🆔 Buscar por ID de Telegram\n"
        mensaje += "• 📞 Buscar por número de teléfono\n"
        mensaje += "• 💳 Buscar por número de tarjeta\n"
        mensaje += "• 📊 Ver estadísticas del sistema\n\n"
        mensaje += "🔽 Selecciona el tipo de búsqueda:"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "config_menu":
        keyboard = [
            [InlineKeyboardButton("🛡️ Seguridad del Sistema", callback_data="config_security")],
            [InlineKeyboardButton("📝 Mensajes Automáticos", callback_data="config_messages")],
            [InlineKeyboardButton("⏰ Configurar Timeouts", callback_data="config_timeouts")],
            [InlineKeyboardButton("📊 Logs del Sistema", callback_data="config_logs")],
            [InlineKeyboardButton("🔄 Backup y Restauración", callback_data="config_backup")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
        ]

        mensaje = "⚙️ Configuraciones del Sistema\n\n"
        mensaje += "🔧 Opciones de configuración disponibles:\n"
        mensaje += "• 🛡️ Ajustes de seguridad y permisos\n"
        mensaje += "• 📝 Personalizar mensajes automáticos\n"
        mensaje += "• ⏰ Configurar tiempos de espera\n"
        mensaje += "• 📊 Gestionar logs y registros\n"
        mensaje += "• 🔄 Opciones de respaldo de datos\n\n"
        mensaje += "🔽 Selecciona una opción:"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    # Agregar handlers faltantes para configuraciones
    elif data == "config_messages":
        mensaje = "📝 Configuración de Mensajes Automáticos\n\n"
        mensaje += "💬 **Mensajes del sistema configurados:**\n"
        mensaje += "• ✅ Bienvenida para nuevos VIPs\n"
        mensaje += "• ✅ Notificaciones de cambios de estatus\n"
        mensaje += "• ✅ Confirmaciones de verificación\n"
        mensaje += "• ✅ Mensajes de error personalizados\n\n"
        mensaje += "⚙️ **Estado:** Todos los mensajes funcionando correctamente\n"
        mensaje += "🔧 **Para personalizar mensajes contacta:** @frankosmel"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="config_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "config_timeouts":
        mensaje = "⏰ Configuración de Timeouts\n\n"
        mensaje += "🕐 **Timeouts actuales:**\n"
        mensaje += "• Procesos paso a paso: Sin límite\n"
        mensaje += "• Búsquedas: Sin límite\n"
        mensaje += "• Mensajes masivos: Sin límite\n"
        mensaje += "• Verificaciones VIP: Instantáneo\n\n"
        mensaje += "✅ **Estado:** Configuración óptima\n"
        mensaje += "💡 **Nota:** Los timeouts están optimizados para mejor experiencia"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="config_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "config_backup":
        mensaje = "🔄 Backup y Restauración\n\n"
        mensaje += "💾 **Estado de respaldos:**\n"
        mensaje += f"• Usuarios VIP: {len(cargar_vip_users())} registros\n"
        mensaje += f"• Administradores: {len(cargar_admins())} registros\n"
        mensaje += f"• Blacklist: {len(cargar_blacklist())} registros\n"
        mensaje += f"• Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        mensaje += "✅ **Archivos de datos:**\n"
        mensaje += "• vip_users.json - Activo\n"
        mensaje += "• admins.json - Activo\n"
        mensaje += "• blacklist.json - Activo\n\n"
        mensaje += "🛡️ **Los datos se guardan automáticamente**"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="config_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    # Handlers para Blacklist
    elif data == "blacklist_add_stepbystep":
        mensaje = "🚫 Agregar Usuario a Blacklist - Paso a Paso\n\n"
        mensaje += "⚠️ Este proceso te guiará para banear un usuario:\n\n"
        mensaje += "📝 Datos que se recopilarán:\n"
        mensaje += "• 👤 Username de Telegram\n"
        mensaje += "• 🆔 ID de Telegram\n"
        mensaje += "• 💳 Números de tarjetas problemáticas\n"
        mensaje += "• 📱 Teléfono (opcional)\n"
        mensaje += "• 📝 Motivo del baneo\n"
        mensaje += "• 📊 Información adicional\n\n"
        mensaje += "🔽 Para continuar, presiona 'Iniciar Proceso'"

        keyboard = [
            [InlineKeyboardButton("🚀 Iniciar Proceso", callback_data="start_blacklist_creation")],
            [InlineKeyboardButton("🔙 Volver", callback_data="blacklist_menu")]
        ]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "blacklist_list":
        blacklist = cargar_blacklist()
        mensaje = "📋 **Lista de Usuarios en Blacklist**\n\n"

        if not blacklist:
            mensaje += "✅ No hay usuarios en la blacklist actualmente."
        else:
            mensaje += f"🚫 **Total de usuarios baneados:** {len(blacklist)}\n\n"
            for i, user in enumerate(blacklist, 1):
                username = user.get('username', 'Sin username')
                user_id = user.get('user_id', 'Sin ID')
                motivo = user.get('motivo', 'Sin motivo')
                fecha = user.get('fecha_agregado', 'N/A')
                
                mensaje += f"**{i}.** {username}\n"
                mensaje += f"   🆔 ID: {user_id}\n"
                mensaje += f"   ⚠️ Motivo: {motivo}\n"
                mensaje += f"   📅 Baneado: {fecha}\n\n"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="blacklist_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_menu":
        keyboard = [
            [InlineKeyboardButton("👤 Buscar por Username", callback_data="blacklist_search_username")],
            [InlineKeyboardButton("🆔 Buscar por ID", callback_data="blacklist_search_id")],
            [InlineKeyboardButton("💳 Buscar por Tarjeta", callback_data="blacklist_search_card")],
            [InlineKeyboardButton("📱 Buscar por Teléfono", callback_data="blacklist_search_phone")],
            [InlineKeyboardButton("📊 Estadísticas Blacklist", callback_data="blacklist_stats")],
            [InlineKeyboardButton("🔙 Volver", callback_data="blacklist_menu")]
        ]

        mensaje = "🔍 **Búsqueda en Blacklist**\n\n"
        mensaje += "🎯 **Opciones de búsqueda disponibles:**\n"
        mensaje += "• 👤 Buscar por username (@usuario)\n"
        mensaje += "• 🆔 Buscar por ID de Telegram\n"
        mensaje += "• 💳 Buscar por número de tarjeta\n"
        mensaje += "• 📱 Buscar por número de teléfono\n"
        mensaje += "• 📊 Ver estadísticas de blacklist\n\n"
        mensaje += "🔽 **Selecciona el tipo de búsqueda:**"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_remove":
        mensaje = "🗑️ **Eliminar Usuario de Blacklist**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "Para eliminar un usuario de la blacklist usa el comando:\n"
        mensaje += "`/delblacklist ID_telegram`\n\n"
        mensaje += "📋 **Ejemplo:**\n"
        mensaje += "`/delblacklist 1383931339`\n\n"
        mensaje += "✅ **Efectos:**\n"
        mensaje += "• El usuario será removido de la blacklist\n"
        mensaje += "• Podrá volver a usar el sistema\n"
        mensaje += "• Se eliminará su historial de baneo\n\n"
        mensaje += "💡 **Tip:** Usa la lista de blacklist para ver los IDs disponibles"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="blacklist_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_menu":
        blacklist_count = len(cargar_blacklist())
        keyboard = [
            [InlineKeyboardButton("🚫 Agregar a Blacklist", callback_data="blacklist_add_stepbystep")],
            [InlineKeyboardButton("📋 Ver Blacklist", callback_data="blacklist_list")],
            [InlineKeyboardButton("🔍 Buscar en Blacklist", callback_data="blacklist_search_menu")],
            [InlineKeyboardButton("🗑️ Eliminar de Blacklist", callback_data="blacklist_remove")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_principal")]
        ]

        mensaje = "🚫 **Panel de Blacklist (Lista Negra)**\n\n"
        mensaje += "⚠️ **Gestión de usuarios baneados:**\n"
        mensaje += "• 🚫 Agregar usuarios problemáticos\n"
        mensaje += "• 📋 Ver lista completa\n"
        mensaje += "• 🔍 Buscar usuarios baneados\n"
        mensaje += "• 🗑️ Eliminar de blacklist\n\n"
        mensaje += f"📊 **Usuarios baneados actualmente:** {blacklist_count}\n\n"
        mensaje += "🔽 **Selecciona una opción:**"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    

    elif data == "blacklist_search_username":
        mensaje = "👤 **Buscar en Blacklist por Username**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el username a buscar\n"
        mensaje += "• Ejemplo: @usuario_problematico\n"
        mensaje += "• No olvides incluir el @\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el username:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'username'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_id":
        mensaje = "🆔 **Buscar en Blacklist por ID**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el ID de Telegram\n"
        mensaje += "• Ejemplo: 1383931339\n"
        mensaje += "• Solo números\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el ID:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'id'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_card":
        mensaje = "💳 **Buscar en Blacklist por Tarjeta**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el número de tarjeta\n"
        mensaje += "• Ejemplo: 9235129976578315\n"
        mensaje += "• Puede ser parcial (últimos 4 dígitos)\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el número de tarjeta:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'card'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_search_phone":
        mensaje = "📱 **Buscar en Blacklist por Teléfono**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el número de teléfono\n"
        mensaje += "• Ejemplo: 56246700 o +5356246700\n"
        mensaje += "• Con o sin código de país\n\n"
        mensaje += "🚫 **Se buscará solo en la base de datos Blacklist**\n\n"
        mensaje += "📝 **Escribe el teléfono:**"

        user_states[user_id] = {'searching_blacklist': True, 'search_type': 'phone'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "blacklist_stats":
        blacklist = cargar_blacklist()
        mensaje = "📊 **Estadísticas de Base de Datos Blacklist**\n\n"
        mensaje += f"🚫 **Total de usuarios baneados:** {len(blacklist)}\n\n"

        if blacklist:
            # Estadísticas por motivo
            motivos = {}
            for user in blacklist:
                motivo = user.get('motivo', 'Sin motivo')
                motivos[motivo] = motivos.get(motivo, 0) + 1

            mensaje += f"📋 **Motivos de baneo (top 3):**\n"
            for motivo, cantidad in list(motivos.items())[:3]:
                mensaje += f"• {motivo}: {cantidad} usuarios\n"

            # Estadísticas por fecha
            fechas = {}
            for user in blacklist:
                fecha = user.get('fecha_agregado', 'N/A')
                if fecha != 'N/A':
                    fecha_solo = fecha.split(' ')[0]
                    fechas[fecha_solo] = fechas.get(fecha_solo, 0) + 1

            mensaje += f"\n📅 **Baneos por fecha (últimos 3):**\n"
            for fecha, cantidad in list(fechas.items())[-3:]:
                mensaje += f"• {fecha}: {cantidad} usuarios\n"

        mensaje += f"\n🕐 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="blacklist_search_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "cancel_blacklist_search":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Búsqueda en blacklist cancelada**", parse_mode='Markdown')
    
    elif data == "universal_search_start":
        # Búsqueda universal disponible para todos los usuarios
        keyboard = [
            [InlineKeyboardButton("🆔 Buscar por ID", callback_data="global_search_by_id")],
            [InlineKeyboardButton("👤 Buscar por @Usuario", callback_data="global_search_by_username")],
            [InlineKeyboardButton("📱 Buscar por Teléfono", callback_data="global_search_by_phone")],
            [InlineKeyboardButton("🧠 Búsqueda Inteligente", callback_data="global_search_smart")],
            [InlineKeyboardButton("🔙 Volver", callback_data="main_search_menu")]
        ]

        mensaje = "🌐 **Búsqueda Universal - Disponible para Todos**\n\n"
        
        if user_id in cargar_admins():
            mensaje += "👑 **Modo Administrador:** Acceso completo a todas las bases\n\n"
            mensaje += "🎯 **Opciones de búsqueda disponibles:**\n"
            mensaje += "• 🆔 **Por ID:** Buscar ID específico en todas las bases\n"
            mensaje += "• 👤 **Por @Usuario:** Buscar username en todas las bases\n"
            mensaje += "• 📱 **Por Teléfono:** Buscar número telefónico en todas las bases\n"
            mensaje += "• 🧠 **Inteligente:** Detección automática del tipo de dato\n\n"
            mensaje += f"📊 **Bases de datos incluidas:**\n"
            mensaje += f"• 💎 Usuarios VIP: {len(cargar_vip_users())} registros\n"
            mensaje += f"• 🚫 Lista Negra: {len(cargar_blacklist())} registros\n"
            mensaje += f"• 👑 Administradores: {len(cargar_admins())} registros\n"
        else:
            mensaje += "👤 **Búsqueda Pública:** Verificación de seguridad\n\n"
            mensaje += "🎯 **Opciones de búsqueda disponibles:**\n"
            mensaje += "• 🆔 **Por ID:** Verificar ID de Telegram\n"
            mensaje += "• 👤 **Por @Usuario:** Verificar username\n"
            mensaje += "• 📱 **Por Teléfono:** Verificar número telefónico\n"
            mensaje += "• 🧠 **Inteligente:** Detección automática del tipo de dato\n\n"
            mensaje += f"📊 **Verificación en bases:**\n"
            mensaje += f"• 💎 Usuarios VIP: {len(cargar_vip_users())} registros\n"
            mensaje += f"• 🚫 Lista Negra: {len(cargar_blacklist())} registros (datos básicos)\n"
            mensaje += f"\n✅ **Función:** Verificar confiabilidad y seguridad de usuarios\n"
            mensaje += f"⚠️ **Nota:** Datos sensibles solo visibles para administradores\n"
            
        mensaje += f"\n🔽 **Selecciona el tipo de búsqueda:**"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "cancel_universal_search":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Búsqueda universal cancelada**", parse_mode='Markdown')

    elif data == "global_search_by_id":
        mensaje = "🆔 **Búsqueda Universal por ID**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el ID de Telegram a buscar\n"
        mensaje += "• Ejemplo: 1383931339\n"
        mensaje += "• Solo números, sin espacios ni símbolos\n\n"
        mensaje += "🔍 **Se verificará en las bases de datos:**\n"
        mensaje += "• 💎 Base de datos VIP (usuarios verificados)\n"
        mensaje += "• 🚫 Lista Negra (usuarios reportados)\n"
        if user_id in cargar_admins():
            mensaje += "• 👑 Lista de Administradores\n"
            mensaje += "\n👑 **Modo Admin:** Datos completos disponibles\n"
        else:
            mensaje += "\n✅ **Verificación de seguridad:** Información básica\n"
            mensaje += "⚠️ **Importante:** Te ayuda a verificar la confiabilidad\n"
        mensaje += "\n📝 **Escribe el ID a verificar:**"

        user_states[user_id] = {'global_search': True, 'search_type': 'id'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_global_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "global_search_by_username":
        mensaje = "👤 **Búsqueda Universal por @Usuario**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el username a verificar\n"
        mensaje += "• Ejemplo: @frankosmel o frankosmel\n"
        mensaje += "• Con o sin el símbolo @\n\n"
        mensaje += "🔍 **Se verificará en las bases de datos:**\n"
        mensaje += "• 💎 Base de datos VIP (usuarios verificados)\n"
        mensaje += "• 🚫 Lista Negra (usuarios reportados)\n"
        if user_id in cargar_admins():
            mensaje += "• 👑 Lista de Administradores\n"
            mensaje += "\n👑 **Modo Admin:** Datos completos disponibles\n"
        else:
            mensaje += "\n✅ **Verificación de confiabilidad:** Información de seguridad\n"
            mensaje += "💡 **Útil para:** Verificar antes de intercambios o transacciones\n"
        mensaje += "\n📝 **Escribe el @usuario a verificar:**"

        user_states[user_id] = {'global_search': True, 'search_type': 'username'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_global_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "global_search_by_card":
        mensaje = "💳 **Búsqueda Global por Tarjeta**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el número de tarjeta a buscar\n"
        mensaje += "• Ejemplo: 9235129976578315\n"
        mensaje += "• Puede ser número completo o parcial\n"
        mensaje += "• También puedes usar los últimos 4 dígitos\n\n"
        mensaje += "🔍 **Se buscará en todas las bases de datos:**\n"
        mensaje += "• 💎 Base de datos VIP (MLC y CUP)\n"
        mensaje += "• 🚫 Lista Negra (Tarjetas reportadas)\n\n"
        mensaje += "📝 **Escribe el número de tarjeta:**"

        user_states[user_id] = {'global_search': True, 'search_type': 'card'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_global_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "global_search_by_phone":
        mensaje = "📱 **Búsqueda Universal por Teléfono**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el número de teléfono a verificar\n"
        mensaje += "• Ejemplo: +5356246700 o 56246700\n"
        mensaje += "• Con o sin código de país\n"
        mensaje += "• Se buscarán coincidencias parciales\n\n"
        mensaje += "🔍 **Se verificará en las bases de datos:**\n"
        mensaje += "• 💎 Base de datos VIP (teléfonos verificados)\n"
        mensaje += "• 🚫 Lista Negra (teléfonos reportados)\n"
        if user_id in cargar_admins():
            mensaje += "\n👑 **Modo Admin:** Datos completos disponibles\n"
        else:
            mensaje += "\n✅ **Verificación de seguridad:** Información básica\n"
            mensaje += "💡 **Útil para:** Verificar confiabilidad de números\n"
        mensaje += "\n📝 **Escribe el número de teléfono:**"

        user_states[user_id] = {'global_search': True, 'search_type': 'phone'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_global_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "global_search_smart":
        mensaje = "🧠 **Búsqueda Universal Inteligente**\n\n"
        mensaje += "🤖 **Detección automática del tipo de dato:**\n"
        mensaje += "• El sistema detectará automáticamente qué tipo de dato escribes\n"
        mensaje += "• Verificación simultánea en todas las bases de datos\n"
        if user_id in cargar_admins():
            mensaje += "• Resultados completos y detallados\n\n"
        else:
            mensaje += "• Resultados con información de seguridad\n\n"
        mensaje += "📝 **Ejemplos de verificación:**\n"
        mensaje += "• @usuario o usuario - Verificar username\n"
        mensaje += "• 1234567890 - Verificar ID de Telegram\n"
        mensaje += "• +5356246700 - Verificar número de teléfono\n"
        if user_id in cargar_admins():
            mensaje += "• 9235*** - Buscar número de tarjeta\n\n"
        else:
            mensaje += "\n✅ **Función:** Verificar confiabilidad y seguridad\n"
            mensaje += "💡 **Recomendado:** Usar antes de intercambios importantes\n\n"
        mensaje += "🔍 **Escribe lo que quieres verificar:**"

        user_states[user_id] = {'global_search': True, 'search_type': 'smart'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_global_search")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "cancel_global_search":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Búsqueda global cancelada**", parse_mode='Markdown')

    # Handlers para confirmación de eliminación de administradores
    elif data.startswith("confirm_delete_admin_"):
        admin_id_to_delete = int(data.split("_")[3])
        
        try:
            admins = cargar_admins()
            
            if admin_id_to_delete not in admins:
                return await query.edit_message_text("ℹ️ Este usuario ya no es administrador.")
            
            if admin_id_to_delete == user_id:
                return await query.edit_message_text("❌ No puedes eliminarte a ti mismo como administrador.")
            
            # Obtener info del admin antes de eliminar
            try:
                chat = await context.bot.get_chat(admin_id_to_delete)
                admin_username = f"@{chat.username}" if chat.username else "Sin username"
                admin_name = chat.full_name or "Sin nombre"
            except:
                admin_username = "Sin username"
                admin_name = "Sin nombre"
            
            # Eliminar admin
            admins.remove(admin_id_to_delete)
            guardar_admins(admins)

            mensaje = f"✅ **Administrador Eliminado Exitosamente**\n\n"
            mensaje += f"👤 Usuario: {admin_username}\n"
            mensaje += f"👨‍💼 Nombre: {admin_name}\n"
            mensaje += f"🆔 ID: {admin_id_to_delete}\n"
            mensaje += f"📅 Eliminado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            mensaje += f"👤 Eliminado por: @{user.username or 'admin'}"

            await query.edit_message_text(mensaje, parse_mode='Markdown')

            # Notificar al usuario eliminado
            try:
                mensaje_notificacion = f"⚠️ **Cambio en tu Estatus Administrativo**\n\n"
                mensaje_notificacion += f"🚫 Tu acceso como administrador ha sido revocado\n"
                mensaje_notificacion += f"📅 Revocado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                mensaje_notificacion += f"❓ Si tienes dudas, contacta: @frankosmel"

                await context.bot.send_message(
                    chat_id=admin_id_to_delete,
                    text=mensaje_notificacion,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"No se pudo notificar al usuario {admin_id_to_delete}: {e}")

        except Exception as e:
            print(f"❌ Error eliminando administrador: {e}")
            await query.edit_message_text("❌ Error al eliminar el administrador.")

    elif data == "cancel_delete_admin":
        await query.edit_message_text("❌ **Eliminación de administrador cancelada**", parse_mode='Markdown')

    # Handlers para verificación VIP rápida
    elif data == "quick_vip_verify_username":
        mensaje = "👤 **Verificación VIP por Username**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el username a verificar\n"
        mensaje += "• Ejemplo: @frankosmel\n"
        mensaje += "• Incluye el símbolo @ al inicio\n\n"
        mensaje += "✅ **Verificación rápida:**\n"
        mensaje += "• Confirma si el usuario es VIP\n"
        mensaje += "• Muestra información básica de verificación\n"
        mensaje += "• Disponible para todos los usuarios\n\n"
        mensaje += "📝 **Escribe el @usuario a verificar:**"

        user_states[user_id] = {'quick_vip_verify': True, 'verify_type': 'username'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_verify")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "quick_vip_verify_id":
        mensaje = "🆔 **Verificación VIP por ID**\n\n"
        mensaje += "📝 **Instrucciones:**\n"
        mensaje += "• Escribe el ID de Telegram\n"
        mensaje += "• Ejemplo: 1383931339\n"
        mensaje += "• Solo números, sin espacios\n\n"
        mensaje += "✅ **Verificación rápida:**\n"
        mensaje += "• Confirma si el ID es VIP\n"
        mensaje += "• Muestra información básica de verificación\n"
        mensaje += "• Disponible para todos los usuarios\n\n"
        mensaje += "📝 **Escribe el ID a verificar:**"

        user_states[user_id] = {'quick_vip_verify': True, 'verify_type': 'id'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_verify")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "public_vip_list":
        vip_users = cargar_vip_users()
        mensaje = "📋 **Lista Pública de Usuarios VIP**\n\n"

        if not vip_users:
            mensaje += "❌ No hay usuarios VIP registrados actualmente."
        else:
            mensaje += f"💎 **Total de usuarios VIP verificados:** {len(vip_users)}\n\n"
            mensaje += "👥 **Usuarios VIP públicos:**\n"
            
            # Mostrar solo información básica pública
            for i, vip in enumerate(vip_users[:10], 1):  # Máximo 10 para no saturar
                username = vip.get('username', 'N/A')
                fecha = vip.get('fecha_agregado', 'N/A')
                mensaje += f"{i}. {username} - Verificado: {fecha.split(' ')[0] if fecha != 'N/A' else 'N/A'}\n"
            
            if len(vip_users) > 10:
                mensaje += f"\n... y {len(vip_users) - 10} usuarios VIP más\n"
            
            mensaje += f"\n✅ **Todos los usuarios VIP mostrados han sido verificados**\n"
            mensaje += f"🛡️ **Respaldo administrativo completo**"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="back_to_vip_verify")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "cancel_vip_verify":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ **Verificación VIP cancelada**", parse_mode='Markdown')

    elif data == "back_to_vip_verify":
        # Volver al menú de verificación VIP
        keyboard = [
            [InlineKeyboardButton("👤 Verificar por @Usuario", callback_data="quick_vip_verify_username")],
            [InlineKeyboardButton("🆔 Verificar por ID", callback_data="quick_vip_verify_id")],
            [InlineKeyboardButton("📋 Lista VIP Pública", callback_data="public_vip_list")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="back_to_main")]
        ]

        mensaje = "✅ **Verificación Rápida de Usuarios VIP**\n\n"
        mensaje += "🎯 **Opciones de verificación disponibles:**\n"
        mensaje += "• 👤 **Por @Usuario:** Verificar username específico\n"
        mensaje += "• 🆔 **Por ID:** Verificar ID de Telegram\n"
        mensaje += "• 📋 **Lista Pública:** Ver usuarios VIP públicos\n\n"
        mensaje += "🔽 **Selecciona el tipo de verificación:**"

        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == "back_to_main":
        # Volver al menú principal con teclado
        keyboard = obtener_teclado_principal(user_id, "private")
        mensaje = "🔙 **Menú Principal**\n\n"
        if user_id in cargar_admins():
            mensaje += "👑 Administrador: Panel principal restaurado\n"
        else:
            mensaje += "👤 Usuario: Menú principal restaurado\n"
        mensaje += "🔽 Utiliza los botones para las funciones disponibles:"

        await query.edit_message_text(mensaje, parse_mode='Markdown')
        # Enviar un nuevo mensaje con el teclado del menú principal
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="🏠 **Menú Principal Activo**\n\nUsa los botones para acceder a las funciones:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    elif data == "mass_message_custom":
        mensaje = "📤 Mensaje Personalizado\n\n"
        mensaje += "🎯 **Crear mensaje personalizado:**\n"
        mensaje += "• Escribe tu mensaje personalizado\n"
        mensaje += "• Se enviará a todos los usuarios VIP\n"
        mensaje += "• Puedes usar emojis y formato\n\n"
        mensaje += "📝 **Función:** Similar a mensajes masivos pero con más personalización\n\n"
        mensaje += "✏️ **Escribe tu mensaje personalizado:**"

        user_states[user_id] = {'mass_message': True, 'type': 'custom'}
        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mass_message")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "search_stats":
        vip_users = cargar_vip_users()
        admins = cargar_admins()
        blacklist = cargar_blacklist()

        mensaje = "📊 **Estadísticas Generales del Sistema**\n\n"
        mensaje += f"👥 **Usuarios Registrados:**\n"
        mensaje += f"• 💎 Usuarios VIP: {len(vip_users)}\n"
        mensaje += f"• 👑 Administradores: {len(admins)}\n"
        mensaje += f"• 🚫 Usuarios en Blacklist: {len(blacklist)}\n"
        mensaje += f"• 📊 Total usuarios: {len(vip_users) + len(admins) + len(blacklist)}\n\n"

        if vip_users:
            # Estadísticas por fecha de VIPs
            fechas_vip = {}
            for vip in vip_users:
                fecha = vip.get('fecha_agregado', 'N/A')
                if fecha != 'N/A':
                    fecha_solo = fecha.split(' ')[0]
                    fechas_vip[fecha_solo] = fechas_vip.get(fecha_solo, 0) + 1

            mensaje += f"📅 **Registros VIP por fecha (últimos 5):**\n"
            for fecha, cantidad in list(fechas_vip.items())[-5:]:
                mensaje += f"• {fecha}: {cantidad} usuarios VIP\n"

        if blacklist:
            # Estadísticas de blacklist
            mensaje += f"\n🚫 **Estadísticas Blacklist:**\n"
            mensaje += f"• Total baneados: {len(blacklist)}\n"
            
            # Motivos más comunes
            motivos = {}
            for user in blacklist:
                motivo = user.get('motivo', 'Sin motivo')
                motivos[motivo] = motivos.get(motivo, 0) + 1
            
            mensaje += f"• Motivos principales:\n"
            for motivo, cantidad in list(motivos.items())[:3]:
                mensaje += f"  - {motivo}: {cantidad} usuarios\n"

        mensaje += f"\n🕐 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        mensaje += f"👤 **Consultado por:** @{query.from_user.username or 'admin'}"

        keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="main_search_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_step_by_step_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if user_id not in cargar_admins():
        await query.edit_message_text("❌ No tienes permisos de administrador.")
        return

    if data == "start_blacklist_creation":
        user_states[user_id] = {
            'adding_blacklist': True,
            'step': 'username',
            'data': {}
        }

        mensaje = "🚫 Proceso de Agregar a Blacklist - Paso 1/6\n\n"
        mensaje += "👤 Ingresa el username del usuario a banear:\n"
        mensaje += "• Ejemplo: @usuario_problematico\n"
        mensaje += "• No olvides incluir el @\n\n"
        mensaje += "📝 Escribe el username a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "start_vip_creation":
        user_states[user_id] = {
            'adding_vip': True,
            'step': 'username',
            'data': {}
        }

        mensaje = "🔧 Proceso de Agregar VIP - Paso 1/6\n\n"
        mensaje += "👤 Ingresa el username del usuario:\n"
        mensaje += "• Ejemplo: @frankosmel\n"
        mensaje += "• No olvides incluir el @\n\n"
        mensaje += "📝 Escribe el username a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_admin_creation_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_states or not user_states[user_id].get('adding_admin'):
        return

    state = user_states[user_id]
    step = state['step']

    if step == 'username':
        if not text.startswith('@'):
            return await update.message.reply_text("❌ El username debe comenzar con @. Inténtalo de nuevo:")

        username = text.strip()
        state['data']['username'] = username
        state['step'] = 'user_id'

        mensaje = "🔧 Proceso de Agregar Administrador - Paso 2/2\n\n"
        mensaje += f"✅ Username: {username}\n\n"
        mensaje += "🆔 Ingresa el ID de Telegram del usuario:\n"
        mensaje += "• Debe ser un número\n"
        mensaje += "• Ejemplo: 1383931339\n\n"
        mensaje += "📝 Escribe el ID a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_admin_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'user_id':
        try:
            telegram_id = int(text.strip())
        except ValueError:
            return await update.message.reply_text("❌ El ID debe ser un número válido. Inténtalo de nuevo:")

        admins = cargar_admins()
        if telegram_id in admins:
            return await update.message.reply_text("❌ Ya existe un administrador con este ID. Inténtalo con otro ID:")

        state['data']['user_id'] = telegram_id

        # Mostrar resumen y confirmación
        data = state['data']
        mensaje = "🔧 Resumen de Administrador\n\n"
        mensaje += f"👤 Username: {data['username']}\n"
        mensaje += f"🆔 ID: {telegram_id}\n\n"
        mensaje += "⚠️ ¿Confirmas que todos los datos son correctos?"

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar y Crear Admin", callback_data="confirm_admin_creation")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_admin_creation")]
        ]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_blacklist_creation_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_states or not user_states[user_id].get('adding_blacklist'):
        return

    state = user_states[user_id]
    step = state['step']

    if step == 'username':
        username = text.strip()
        if not username.startswith('@'):
            return await update.message.reply_text("❌ El username debe comenzar con @. Inténtalo de nuevo:")

        state['data']['username'] = username
        state['step'] = 'user_id'

        mensaje = "🚫 Proceso de Agregar a Blacklist - Paso 2/6\n\n"
        mensaje += f"✅ Username: {username}\n\n"
        mensaje += "🆔 Ingresa el ID de Telegram del usuario:\n"
        mensaje += "• Debe ser un número\n"
        mensaje += "• Ejemplo: 1383931339\n\n"
        mensaje += "📝 Escribe el ID a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'user_id':
        text_clean = text.strip()
        if not text_clean.isdigit():
            return await update.message.reply_text("❌ El ID debe ser solo números. Inténtalo de nuevo:")

        telegram_id = int(text_clean)

        # Verificar si ya está en blacklist
        if buscar_blacklist_por_id(telegram_id):
            return await update.message.reply_text("⚠️ Este usuario ya está en la blacklist. Inténtalo con otro ID:")

        state['data']['user_id'] = telegram_id
        state['step'] = 'tarjetas'

        mensaje = "🚫 Proceso de Agregar a Blacklist - Paso 3/6\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {telegram_id}\n\n"
        mensaje += "💳 Ingresa los números de tarjetas problemáticas:\n"
        mensaje += "• Separa múltiples tarjetas con comas\n"
        mensaje += "• Ejemplo: 9235129976578315, 9204129976918161\n"
        mensaje += "• O escribe 'ninguna' si no hay tarjetas\n\n"
        mensaje += "📝 Escribe las tarjetas a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'tarjetas':
        tarjetas_text = text.strip()
        if tarjetas_text.lower() == 'ninguna':
            tarjetas = []
        else:
            tarjetas = [t.strip() for t in tarjetas_text.split(',')]
        
        state['data']['tarjetas'] = tarjetas
        state['step'] = 'telefono'

        mensaje = "🚫 Proceso de Agregar a Blacklist - Paso 4/6\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {state['data']['user_id']}\n"
        mensaje += f"✅ Tarjetas: {len(tarjetas)} registradas\n\n"
        mensaje += "📱 Ingresa el número de teléfono (opcional):\n"
        mensaje += "• Ejemplo: +5356246700 o 56246700\n"
        mensaje += "• O escribe 'ninguno' si no hay teléfono\n\n"
        mensaje += "📝 Escribe el teléfono a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'telefono':
        telefono = text.strip()
        if telefono.lower() == 'ninguno':
            telefono = 'N/A'
        
        state['data']['telefono'] = telefono
        state['step'] = 'motivo'

        mensaje = "🚫 **Proceso de Agregar a Blacklist - Paso 5/6**\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {state['data']['user_id']}\n"
        mensaje += f"✅ Tarjetas: {len(state['data']['tarjetas'])} registradas\n"
        mensaje += f"✅ Teléfono: {telefono}\n\n"
        mensaje += "⚠️ **Ingresa el motivo del baneo:**\n"
        mensaje += "• Sé específico y detallado\n"
        mensaje += "• Ejemplos: 'usuario con deudas', 'tarjetas fraudulentas', 'estafador conocido'\n\n"
        mensaje += "📝 Escribe el motivo a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif step == 'motivo':
        motivo = text.strip()
        state['data']['motivo'] = motivo
        state['step'] = 'info_adicional'

        mensaje = "🚫 **Proceso de Agregar a Blacklist - Paso 6/6**\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {state['data']['user_id']}\n"
        mensaje += f"✅ Tarjetas: {len(state['data']['tarjetas'])} registradas\n"
        mensaje += f"✅ Teléfono: {state['data']['telefono']}\n"
        mensaje += f"✅ Motivo: {motivo}\n\n"
        mensaje += "📊 **Información adicional (opcional):**\n"
        mensaje += "• Detalles extra, reportes, evidencias, etc.\n"
        mensaje += "• O escribe 'ninguna' si no hay información adicional\n\n"
        mensaje += "📝 Escribe la información adicional:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif step == 'info_adicional':
        info_adicional = text.strip()
        if info_adicional.lower() == 'ninguna':
            info_adicional = 'N/A'
        
        state['data']['info_adicional'] = info_adicional

        # Mostrar resumen y confirmación
        data = state['data']
        mensaje = "🚫 **Resumen de Usuario para Blacklist**\n\n"
        mensaje += f"👤 Username: {data['username']}\n"
        mensaje += f"🆔 ID: {data['user_id']}\n"
        mensaje += f"💳 Tarjetas: {len(data['tarjetas'])} registradas\n"
        if data['tarjetas']:
            mensaje += f"   └─ {', '.join(data['tarjetas'][:2])}{'...' if len(data['tarjetas']) > 2 else ''}\n"
        mensaje += f"📱 Teléfono: {data['telefono']}\n"
        mensaje += f"⚠️ Motivo: {data['motivo']}\n"
        mensaje += f"📊 Info adicional: {info_adicional}\n\n"
        mensaje += "🔴 **¿Confirmas agregar este usuario a la blacklist?**\n"
        mensaje += "⚠️ Esta acción baneará permanentemente al usuario."

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar y Banear", callback_data="confirm_blacklist_creation")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_blacklist_creation")]
        ]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_vip_creation_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text

        if user_id not in user_states or not user_states[user_id].get('adding_vip'):
            return

        state = user_states[user_id]
        step = state['step']
        
        print(f"DEBUG VIP creation: Usuario {user_id}, paso '{step}', texto '{text}'")
    except Exception as e:
        print(f"❌ Error en handle_vip_creation_step: {e}")
        await update.message.reply_text(f"❌ Error procesando '{text}'. Reinicia el proceso con /start")
        if user_id in user_states:
            del user_states[user_id]
        return

    if step == 'username':
        username_raw = text.strip()
        
        # Validar que comience con @
        if not username_raw.startswith('@'):
            return await update.message.reply_text("❌ El username debe comenzar con @. Inténtalo de nuevo:")
        
        # Limpiar y validar el username
        username_clean = username_raw.lower().strip()
        
        # Validar formato básico del username
        if len(username_clean) < 2:
            return await update.message.reply_text("❌ El username es demasiado corto. Inténtalo de nuevo:")
        
        # Verificar si ya existe como VIP
        existing_vip = buscar_vip_por_username(username_clean)
        if existing_vip:
            return await update.message.reply_text(f"❌ {username_clean} ya es VIP. Inténtalo con otro username:")

        state['data']['username'] = username_clean
        state['step'] = 'user_id'

        mensaje = "🔧 Proceso de Agregar VIP - Paso 2/6\n\n"
        mensaje += f"✅ Username: {username_clean}\n\n"
        mensaje += "🆔 Ingresa el ID de Telegram del usuario:\n"
        mensaje += "• Debe ser un número\n"
        mensaje += "• Ejemplo: 1383931339\n\n"
        mensaje += "📝 Escribe el ID a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'user_id':
        try:
            telegram_id = int(text.strip())
        except ValueError:
            return await update.message.reply_text("❌ El ID debe ser un número válido. Inténtalo de nuevo:")

        if buscar_vip_por_id(telegram_id):
            return await update.message.reply_text("❌ Ya existe un VIP con este ID. Inténtalo con otro ID:")

        state['data']['user_id'] = telegram_id
        state['step'] = 'nombre'

        mensaje = "🔧 Proceso de Agregar VIP - Paso 3/6\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {telegram_id}\n\n"
        mensaje += "👨‍💼 Ingresa el nombre completo:\n"
        mensaje += "• Usa guiones bajos en lugar de espacios\n"
        mensaje += "• Ejemplo: Frank_Del_Rio_Cambra\n\n"
        mensaje += "📝 Escribe el nombre a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'nombre':
        nombre = text.strip().replace(' ', '_')
        state['data']['nombre_completo'] = nombre
        state['step'] = 'telefono'

        mensaje = "🔧 Proceso de Agregar VIP - Paso 4/6\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {state['data']['user_id']}\n"
        mensaje += f"✅ Nombre: {nombre}\n\n"
        mensaje += "📞 Ingresa el número de teléfono:\n"
        mensaje += "• Ejemplo: +5356246700 o 56246700\n\n"
        mensaje += "📝 Escribe el teléfono a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'telefono':
        telefono = text.strip()
        state['data']['telefono'] = telefono
        state['step'] = 'tarjeta_mlc'

        mensaje = "🔧 Proceso de Agregar VIP - Paso 5/6\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {state['data']['user_id']}\n"
        mensaje += f"✅ Nombre: {state['data']['nombre_completo']}\n"
        mensaje += f"✅ Teléfono: {telefono}\n\n"
        mensaje += "💳 Ingresa el número de tarjeta MLC:\n"
        mensaje += "• Ejemplo: 9235129976578315\n\n"
        mensaje += "📝 Escribe la tarjeta MLC a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'tarjeta_mlc':
        tarjeta_mlc = text.strip()
        state['data']['tarjeta_mlc'] = tarjeta_mlc
        state['step'] = 'tarjeta_cup'

        mensaje = "🔧 Proceso de Agregar VIP - Paso 6/6\n\n"
        mensaje += f"✅ Username: {state['data']['username']}\n"
        mensaje += f"✅ ID: {state['data']['user_id']}\n"
        mensaje += f"✅ Nombre: {state['data']['nombre_completo']}\n"
        mensaje += f"✅ Teléfono: {state['data']['telefono']}\n"
        mensaje += f"✅ Tarjeta MLC: {tarjeta_mlc}\n\n"
        mensaje += "💳 Ingresa el número de tarjeta CUP:\n"
        mensaje += "• Ejemplo: 9204129976918161\n\n"
        mensaje += "📝 Escribe la tarjeta CUP a continuación:"

        keyboard = [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'tarjeta_cup':
        tarjeta_cup = text.strip()
        state['data']['tarjeta_cup'] = tarjeta_cup

        # Mostrar resumen y confirmación
        data = state['data']
        mensaje = "🔧 Resumen de Usuario VIP\n\n"
        mensaje += f"👤 Username: {data['username']}\n"
        mensaje += f"🆔 ID: {data['user_id']}\n"
        mensaje += f"👨‍💼 Nombre: {data['nombre_completo']}\n"
        mensaje += f"📞 Teléfono: {data['telefono']}\n"
        mensaje += f"💳 Tarjeta MLC: {data['tarjeta_mlc']}\n"
        mensaje += f"💳 Tarjeta CUP: {tarjeta_cup}\n\n"
        mensaje += "⚠️ ¿Confirmas que todos los datos son correctos?"

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar y Crear VIP", callback_data="confirm_vip_creation")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_vip_creation")]
        ]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_blacklist_creation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if user_id not in user_states or not user_states[user_id].get('adding_blacklist'):
        return await query.edit_message_text("❌ Sesión expirada.")

    if data == "cancel_blacklist_creation":
        del user_states[user_id]
        await query.edit_message_text("❌ **Proceso cancelado**\n\nNo se agregó ningún usuario a la blacklist.", parse_mode='Markdown')
        return

    if data == "confirm_blacklist_creation":
        state = user_states[user_id]
        blacklist_data = state['data']

        # Crear el usuario en blacklist
        blacklist = cargar_blacklist()
        nuevo_baneado = {
            "user_id": blacklist_data['user_id'],
            "username": blacklist_data['username'],
            "tarjetas": blacklist_data['tarjetas'],
            "telefono": blacklist_data['telefono'],
            "motivo": blacklist_data['motivo'],
            "info_adicional": blacklist_data['info_adicional'],
            "agregado_por": f"@{query.from_user.username or 'admin'}",
            "fecha_agregado": datetime.now().strftime('%d/%m/%Y %H:%M'),
            "estado": "baneado",
            "tipo_baneo": "manual_admin"
        }

        blacklist.append(nuevo_baneado)
        guardar_blacklist(blacklist)

        # Limpiar estado
        del user_states[user_id]

        mensaje = "🚫 **Usuario Agregado a Blacklist Exitosamente**\n\n"
        mensaje += f"👤 Usuario: {blacklist_data['username']}\n"
        mensaje += f"🆔 ID: {blacklist_data['user_id']}\n"
        mensaje += f"💳 Tarjetas: {len(blacklist_data['tarjetas'])} registradas\n"
        mensaje += f"📱 Teléfono: {blacklist_data['telefono']}\n"
        mensaje += f"⚠️ Motivo: {blacklist_data['motivo']}\n"
        mensaje += f"📅 Baneado: {nuevo_baneado['fecha_agregado']}\n"
        mensaje += f"👑 Baneado por: {nuevo_baneado['agregado_por']}\n\n"
        mensaje += "🔴 **El usuario ha sido baneado permanentemente del sistema**"

        await query.edit_message_text(mensaje, parse_mode='Markdown')

        # Notificar al usuario baneado (opcional)
        try:
            mensaje_notificacion = f"🚫 **Notificación de Baneo**\n\n"
            mensaje_notificacion += f"⚠️ Tu cuenta ha sido agregada a la lista negra del sistema\n"
            mensaje_notificacion += f"📅 Fecha: {nuevo_baneado['fecha_agregado']}\n"
            mensaje_notificacion += f"⚠️ Motivo: {blacklist_data['motivo']}\n\n"
            mensaje_notificacion += f"🚫 Ya no puedes usar los servicios del sistema\n"
            mensaje_notificacion += f"📞 Para apelaciones contacta: @frankosmel"

            await context.bot.send_message(
                chat_id=blacklist_data['user_id'],
                text=mensaje_notificacion,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"No se pudo notificar al usuario baneado {blacklist_data['user_id']}: {e}")

async def handle_admin_creation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if user_id not in user_states or not user_states[user_id].get('adding_admin'):
        return await query.edit_message_text("❌ Sesión expirada.")

    if data == "cancel_admin_creation":
        del user_states[user_id]
        await query.edit_message_text("❌ Proceso cancelado\n\nNo se agregó ningún administrador.")
        return

    if data == "confirm_admin_creation":
        state = user_states[user_id]
        admin_data = state['data']

        # Crear el administrador
        admins = cargar_admins()
        admins.append(admin_data['user_id'])
        guardar_admins(admins)

        # Limpiar estado
        del user_states[user_id]

        mensaje = "✅ Administrador Creado Exitosamente\n\n"
        mensaje += f"👤 Usuario: {admin_data['username']}\n"
        mensaje += f"🆔 ID: {admin_data['user_id']}\n"
        mensaje += f"📅 Agregado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        mensaje += f"👑 Agregado por: @{query.from_user.username or 'admin'}\n\n"
        mensaje += "🎉 El usuario ha sido notificado de su estatus de administrador"

        await query.edit_message_text(mensaje)

        # Notificar al usuario
        try:
            mensaje_notificacion = f"🎉 ¡Felicidades! Has sido agregado como Administrador\n\n"
            mensaje_notificacion += f"✅ Tu cuenta ha sido promovida por otro administrador\n"
            mensaje_notificacion += f"👑 Ahora tienes acceso completo al panel administrativo\n\n"
            mensaje_notificacion += f"🔧 Puedes gestionar usuarios VIP y otros administradores\n"
            mensaje_notificacion += f"🛡️ Tienes control total del sistema\n\n"
            mensaje_notificacion += f"📞 Soporte: @frankosmel"

            await context.bot.send_message(
                chat_id=admin_data['user_id'],
                text=mensaje_notificacion
            )
        except Exception as e:
            print(f"No se pudo notificar al usuario {admin_data['user_id']}: {e}")

async def handle_vip_creation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if user_id not in user_states or not user_states[user_id].get('adding_vip'):
        return await query.edit_message_text("❌ Sesión expirada.")

    if data == "cancel_vip_creation":
        del user_states[user_id]
        await query.edit_message_text("❌ **Proceso cancelado**\n\nNo se agregó ningún usuario VIP.", parse_mode='Markdown')
        return

    if data == "confirm_vip_creation":
        state = user_states[user_id]
        vip_data = state['data']

        # Crear el usuario VIP
        users = cargar_vip_users()
        nuevo_vip = {
            "user_id": vip_data['user_id'],
            "username": vip_data['username'],
            "kyc": "sí",
            "telegram_id": vip_data['user_id'],
            "telefono": vip_data['telefono'],
            "tarjeta_mlc": vip_data['tarjeta_mlc'],
            "tarjeta_cup": vip_data['tarjeta_cup'],
            "nombre_completo": vip_data['nombre_completo'].replace('_', ' '),
            "agregado_por": f"@{query.from_user.username or 'admin'}",
            "fecha_agregado": datetime.now().strftime('%d/%m/%Y %H:%M'),
            "estado": "activo",
            "tipo_registro": "manual_stepbystep"
        }

        users.append(nuevo_vip)
        guardar_vip_users(users)

        # Limpiar estado
        del user_states[user_id]

        mensaje = "✅ **Usuario VIP Creado Exitosamente**\n\n"
        mensaje += f"👤 Usuario: {vip_data['username']}\n"
        mensaje += f"🆔 ID: {vip_data['user_id']}\n"
        mensaje += f"👨‍💼 Nombre: {nuevo_vip['nombre_completo']}\n"
        mensaje += f"📞 Teléfono: {vip_data['telefono']}\n"
        mensaje += f"💳 Tarjeta MLC: {vip_data['tarjeta_mlc']}\n"
        mensaje += f"💳 Tarjeta CUP: {vip_data['tarjeta_cup']}\n"
        mensaje += f"📅 Agregado: {nuevo_vip['fecha_agregado']}\n"
        mensaje += f"👑 Agregado por: {nuevo_vip['agregado_por']}\n\n"
        mensaje += "🎉 **El usuario ha sido notificado de su estatus VIP**"

        await query.edit_message_text(mensaje, parse_mode='Markdown')

        # Notificar al usuario
        try:
            mensaje_notificacion = f"🎉 **¡Felicidades! Has sido agregado como Usuario VIP**\n\n"
            mensaje_notificacion += f"✅ Tu cuenta ha sido verificada por un administrador\n"
            mensaje_notificacion += f"💎 Ahora eres parte del sistema VIP de confianza\n\n"
            mensaje_notificacion += f"🔍 Los usuarios pueden verificar tu estatus usando `/vip {vip_data['username']}`\n"
            mensaje_notificacion += f"🛡️ Tienes respaldo administrativo completo\n\n"
            mensaje_notificacion += f"📞 **Soporte:** @frankosmel"

            await context.bot.send_message(
                chat_id=vip_data['user_id'],
                text=mensaje_notificacion,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"No se pudo notificar al usuario {vip_data['user_id']}: {e}")

# Función para manejar búsquedas de usuarios
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_states or not user_states[user_id].get('searching'):
        return
    
    search_type = user_states[user_id]['search_type']
    
    if search_type == 'username':
        username = text.strip()
        if not username.startswith('@'):
            return await update.message.reply_text("❌ El username debe comenzar con @. Inténtalo de nuevo:")
        
        vip_user = buscar_vip_por_username(username)
        if vip_user:
            mensaje = f"✅ Usuario VIP Encontrado\n\n"
            mensaje += f"👤 Username: {vip_user['username']}\n"
            mensaje += f"🆔 ID: {vip_user['user_id']}\n"
            mensaje += f"👨‍💼 Nombre: {vip_user.get('nombre_completo', 'N/A')}\n"
            mensaje += f"📞 Teléfono: {vip_user.get('telefono', 'N/A')}\n"
            mensaje += f"💳 MLC: {vip_user.get('tarjeta_mlc', 'N/A')}\n"
            mensaje += f"💳 CUP: {vip_user.get('tarjeta_cup', 'N/A')}\n"
            mensaje += f"📅 Agregado: {vip_user.get('fecha_agregado', 'N/A')}"
        else:
            mensaje = f"❌ No se encontró ningún usuario VIP con username {username}"
    
    elif search_type == 'id':
        try:
            search_id = int(text.strip())
        except ValueError:
            return await update.message.reply_text("❌ El ID debe ser un número válido. Inténtalo de nuevo:")
        
        vip_user = buscar_vip_por_id(search_id)
        if vip_user:
            mensaje = f"✅ Usuario VIP Encontrado\n\n"
            mensaje += f"👤 Username: {vip_user['username']}\n"
            mensaje += f"🆔 ID: {vip_user['user_id']}\n"
            mensaje += f"👨‍💼 Nombre: {vip_user.get('nombre_completo', 'N/A')}\n"
            mensaje += f"📞 Teléfono: {vip_user.get('telefono', 'N/A')}\n"
            mensaje += f"💳 MLC: {vip_user.get('tarjeta_mlc', 'N/A')}\n"
            mensaje += f"💳 CUP: {vip_user.get('tarjeta_cup', 'N/A')}\n"
            mensaje += f"📅 Agregado: {vip_user.get('fecha_agregado', 'N/A')}"
        else:
            mensaje = f"❌ No se encontró ningún usuario VIP con ID {search_id}"

    elif search_type == 'phone':
        phone = text.strip().replace('+', '').replace(' ', '')
        vip_users = cargar_vip_users()
        found_users = []
        
        for vip in vip_users:
            vip_phone = vip.get('telefono', '').replace('+', '').replace(' ', '')
            if phone in vip_phone or vip_phone in phone:
                found_users.append(vip)
        
        if found_users:
            mensaje = f"✅ Encontrados {len(found_users)} usuario(s) VIP\n\n"
            for i, vip in enumerate(found_users, 1):
                mensaje += f"**{i}.** {vip['username']}\n"
                mensaje += f"   🆔 ID: {vip['user_id']}\n"
                mensaje += f"   👨‍💼 Nombre: {vip.get('nombre_completo', 'N/A')}\n"
                mensaje += f"   📞 Teléfono: {vip.get('telefono', 'N/A')}\n\n"
        else:
            mensaje = f"❌ No se encontró ningún usuario VIP con teléfono {phone}"

    elif search_type == 'card':
        card = text.strip().replace(' ', '')
        vip_users = cargar_vip_users()
        found_users = []
        
        for vip in vip_users:
            mlc = vip.get('tarjeta_mlc', '').replace(' ', '')
            cup = vip.get('tarjeta_cup', '').replace(' ', '')
            if card in mlc or card in cup or mlc.endswith(card[-4:]) or cup.endswith(card[-4:]):
                found_users.append(vip)
        
        if found_users:
            mensaje = f"✅ Encontrados {len(found_users)} usuario(s) VIP\n\n"
            for i, vip in enumerate(found_users, 1):
                mensaje += f"**{i}.** {vip['username']}\n"
                mensaje += f"   🆔 ID: {vip['user_id']}\n"
                mensaje += f"   👨‍💼 Nombre: {vip.get('nombre_completo', 'N/A')}\n"
                mensaje += f"   💳 MLC: {vip.get('tarjeta_mlc', 'N/A')}\n"
                mensaje += f"   💳 CUP: {vip.get('tarjeta_cup', 'N/A')}\n\n"
        else:
            mensaje = f"❌ No se encontró ningún usuario VIP con tarjeta {card}"
    
    # Limpiar estado
    del user_states[user_id]
    await update.message.reply_text(mensaje)

# Handler para búsquedas específicas de VIP
async def handle_vip_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_states or not user_states[user_id].get('searching_vip'):
        return
    
    search_type = user_states[user_id]['search_type']
    
    if search_type == 'username':
        username = text.strip()
        if not username.startswith('@'):
            return await update.message.reply_text("❌ El username debe comenzar con @. Inténtalo de nuevo:")
        
        vip_user = buscar_vip_por_username(username)
        if vip_user:
            mensaje = f"✅ **Usuario VIP Encontrado**\n\n"
            mensaje += f"👤 Username: {vip_user['username']}\n"
            mensaje += f"🆔 ID: {vip_user['user_id']}\n"
            mensaje += f"👨‍💼 Nombre: {vip_user.get('nombre_completo', 'N/A')}\n"
            mensaje += f"📞 Teléfono: {vip_user.get('telefono', 'N/A')}\n"
            mensaje += f"💳 MLC: {vip_user.get('tarjeta_mlc', 'N/A')}\n"
            mensaje += f"💳 CUP: {vip_user.get('tarjeta_cup', 'N/A')}\n"
            mensaje += f"📅 Agregado: {vip_user.get('fecha_agregado', 'N/A')}\n"
            mensaje += f"👑 Agregado por: {vip_user.get('agregado_por', 'N/A')}\n\n"
            mensaje += f"💎 **Usuario VIP confirmado y verificado**"
        else:
            mensaje = f"❌ **{username} no está registrado como VIP**\n\n"
            mensaje += f"🔍 **Resultado de búsqueda en base de datos VIP:**\n"
            mensaje += f"• No se encontró el usuario en la base VIP\n"
            mensaje += f"• El usuario no tiene estatus de verificación\n\n"
            mensaje += f"💡 **Para registrar como VIP contacta:** @frankosmel"
    
    elif search_type == 'id':
        try:
            search_id = int(text.strip())
        except ValueError:
            return await update.message.reply_text("❌ El ID debe ser un número válido. Inténtalo de nuevo:")
        
        vip_user = buscar_vip_por_id(search_id)
        if vip_user:
            mensaje = f"✅ **Usuario VIP Encontrado**\n\n"
            mensaje += f"👤 Username: {vip_user['username']}\n"
            mensaje += f"🆔 ID: {vip_user['user_id']}\n"
            mensaje += f"👨‍💼 Nombre: {vip_user.get('nombre_completo', 'N/A')}\n"
            mensaje += f"📞 Teléfono: {vip_user.get('telefono', 'N/A')}\n"
            mensaje += f"💳 MLC: {vip_user.get('tarjeta_mlc', 'N/A')}\n"
            mensaje += f"💳 CUP: {vip_user.get('tarjeta_cup', 'N/A')}\n"
            mensaje += f"📅 Agregado: {vip_user.get('fecha_agregado', 'N/A')}\n"
            mensaje += f"👑 Agregado por: {vip_user.get('agregado_por', 'N/A')}\n\n"
            mensaje += f"💎 **Usuario VIP confirmado y verificado**"
        else:
            mensaje = f"❌ **ID {search_id} no está registrado como VIP**\n\n"
            mensaje += f"🔍 **Resultado de búsqueda en base de datos VIP:**\n"
            mensaje += f"• No se encontró el ID en la base VIP\n"
            mensaje += f"• El usuario no tiene estatus de verificación\n\n"
            mensaje += f"💡 **Para registrar como VIP contacta:** @frankosmel"
    
    # Limpiar estado
    del user_states[user_id]
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# Handler para búsquedas en blacklist
async def handle_blacklist_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_states or not user_states[user_id].get('searching_blacklist'):
        return
    
    search_type = user_states[user_id]['search_type']
    
    if search_type == 'username':
        username = text.strip()
        if not username.startswith('@'):
            return await update.message.reply_text("❌ El username debe comenzar con @. Inténtalo de nuevo:")
        
        # Verificar si el usuario es administrador
        user_id = update.effective_user.id
        es_admin = user_id in cargar_admins()
        
        blacklist_user = buscar_blacklist_por_username(username)
        if blacklist_user:
            if es_admin:
                mensaje = f"🚫 **Usuario Encontrado en Blacklist**\n\n"
                mensaje += f"👤 Username: {blacklist_user['username']}\n"
                mensaje += f"🆔 ID: {blacklist_user['user_id']}\n"
                mensaje += f"⚠️ Motivo: {blacklist_user.get('motivo', 'N/A')}\n"
                mensaje += f"💳 Tarjetas: {len(blacklist_user.get('tarjetas', []))} registradas\n"
                mensaje += f"📱 Teléfono: {blacklist_user.get('telefono', 'N/A')}\n"
                mensaje += f"📊 Info adicional: {blacklist_user.get('info_adicional', 'N/A')}\n"
                mensaje += f"📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n"
                mensaje += f"👑 Baneado por: {blacklist_user.get('agregado_por', 'N/A')}"
            else:
                # Mostrar datos limitados para usuarios normales
                mensaje = mostrar_datos_limitados_blacklist(blacklist_user)
        else:
            mensaje = f"✅ **{username} no está en la blacklist.**\n\nEste usuario no ha sido baneado."
    
    elif search_type == 'id':
        try:
            search_id = int(text.strip())
        except ValueError:
            return await update.message.reply_text("❌ El ID debe ser un número válido. Inténtalo de nuevo:")
        
        # Verificar si el usuario es administrador
        user_id = update.effective_user.id
        es_admin = user_id in cargar_admins()
        
        blacklist_user = buscar_blacklist_por_id(search_id)
        if blacklist_user:
            if es_admin:
                mensaje = f"🚫 **Usuario Encontrado en Blacklist**\n\n"
                mensaje += f"👤 Username: {blacklist_user['username']}\n"
                mensaje += f"🆔 ID: {blacklist_user['user_id']}\n"
                mensaje += f"⚠️ Motivo: {blacklist_user.get('motivo', 'N/A')}\n"
                mensaje += f"💳 Tarjetas: {len(blacklist_user.get('tarjetas', []))} registradas\n"
                mensaje += f"📱 Teléfono: {blacklist_user.get('telefono', 'N/A')}\n"
                mensaje += f"📊 Info adicional: {blacklist_user.get('info_adicional', 'N/A')}\n"
                mensaje += f"📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n"
                mensaje += f"👑 Baneado por: {blacklist_user.get('agregado_por', 'N/A')}"
            else:
                # Mostrar datos limitados para usuarios normales
                mensaje = mostrar_datos_limitados_blacklist(blacklist_user)
        else:
            mensaje = f"✅ **ID {search_id} no está en la blacklist.**\n\nEste usuario no ha sido baneado."

    elif search_type == 'card':
        card = text.strip().replace(' ', '')
        found_users = buscar_blacklist_por_tarjeta(card)
        
        if found_users:
            mensaje = f"🚫 **Encontrados {len(found_users)} usuario(s) baneado(s)**\n\n"
            for i, user in enumerate(found_users, 1):
                mensaje += f"**{i}.** {user['username']}\n"
                mensaje += f"   🆔 ID: {user['user_id']}\n"
                mensaje += f"   ⚠️ Motivo: {user.get('motivo', 'N/A')}\n"
                mensaje += f"   💳 Tarjetas: {len(user.get('tarjetas', []))}\n"
                mensaje += f"   📅 Baneado: {user.get('fecha_agregado', 'N/A')}\n\n"
        else:
            mensaje = f"✅ **No se encontraron usuarios baneados con tarjeta {card}**"

    elif search_type == 'phone':
        phone = text.strip().replace('+', '').replace(' ', '')
        blacklist = cargar_blacklist()
        found_users = []
        
        for user in blacklist:
            user_phone = user.get('telefono', '').replace('+', '').replace(' ', '')
            if phone in user_phone or user_phone in phone:
                found_users.append(user)
        
        if found_users:
            mensaje = f"🚫 **Encontrados {len(found_users)} usuario(s) baneado(s)**\n\n"
            for i, user in enumerate(found_users, 1):
                mensaje += f"**{i}.** {user['username']}\n"
                mensaje += f"   🆔 ID: {user['user_id']}\n"
                mensaje += f"   ⚠️ Motivo: {user.get('motivo', 'N/A')}\n"
                mensaje += f"   📱 Teléfono: {user.get('telefono', 'N/A')}\n"
                mensaje += f"   📅 Baneado: {user.get('fecha_agregado', 'N/A')}\n\n"
        else:
            mensaje = f"✅ **No se encontraron usuarios baneados con teléfono {phone}**"
    
    # Limpiar estado
    del user_states[user_id]
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# Handler para mensajes masivos
async def handle_mass_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_states or not user_states[user_id].get('mass_message'):
        return
    
    message_type = user_states[user_id]['type']
    
    if message_type == 'vips':
        vip_users = cargar_vip_users()
        if not vip_users:
            del user_states[user_id]
            return await update.message.reply_text("❌ No hay usuarios VIP registrados para enviar mensajes.")
        
        enviados = 0
        fallidos = 0
        
        for vip in vip_users:
            try:
                mensaje_final = f"📢 Mensaje de Administrador\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━\n💎 Mensaje enviado a usuarios VIP\n📞 Soporte: @frankosmel"
                await context.bot.send_message(
                    chat_id=vip['user_id'],
                    text=mensaje_final
                )
                enviados += 1
            except Exception as e:
                fallidos += 1
                print(f"Error enviando a {vip['user_id']}: {e}")
        
        resumen = f"📨 Mensaje Masivo Enviado\n\n"
        resumen += f"✅ Enviados exitosos: {enviados}\n"
        resumen += f"❌ Fallos: {fallidos}\n"
        resumen += f"👥 Total VIPs: {len(vip_users)}\n\n"
        resumen += f"📝 Mensaje:\n{text[:100]}{'...' if len(text) > 100 else ''}"
        
        await update.message.reply_text(resumen)
    
    elif message_type == 'admins':
        admins = cargar_admins()
        if not admins:
            del user_states[user_id]
            return await update.message.reply_text("❌ No hay administradores registrados.")
        
        enviados = 0
        fallidos = 0
        
        for admin_id in admins:
            if admin_id == user_id:  # No enviarse a sí mismo
                continue
            try:
                mensaje_final = f"👑 Mensaje Administrativo\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━\n📢 Mensaje para administradores\n👤 Enviado por: @{update.effective_user.username or 'admin'}"
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=mensaje_final
                )
                enviados += 1
            except Exception as e:
                fallidos += 1
                print(f"Error enviando a admin {admin_id}: {e}")
        
        resumen = f"📧 Mensaje Administrativo Enviado\n\n"
        resumen += f"✅ Enviados exitosos: {enviados}\n"
        resumen += f"❌ Fallos: {fallidos}\n"
        resumen += f"👑 Total admins: {len(admins) - 1}\n\n"  # -1 porque no se cuenta a sí mismo
        resumen += f"📝 Mensaje:\n{text[:100]}{'...' if len(text) > 100 else ''}"
        
        await update.message.reply_text(resumen)
    
    elif message_type == 'custom':
        vip_users = cargar_vip_users()
        if not vip_users:
            del user_states[user_id]
            return await update.message.reply_text("❌ No hay usuarios VIP registrados para enviar mensajes.")
        
        enviados = 0
        fallidos = 0
        
        for vip in vip_users:
            try:
                mensaje_final = f"📤 Mensaje Personalizado\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━\n💎 Enviado por administrador\n📞 Soporte: @frankosmel"
                await context.bot.send_message(
                    chat_id=vip['user_id'],
                    text=mensaje_final
                )
                enviados += 1
            except Exception as e:
                fallidos += 1
                print(f"Error enviando a {vip['user_id']}: {e}")
        
        resumen = f"📤 Mensaje Personalizado Enviado\n\n"
        resumen += f"✅ Enviados exitosos: {enviados}\n"
        resumen += f"❌ Fallos: {fallidos}\n"
        resumen += f"👥 Total VIPs: {len(vip_users)}\n\n"
        resumen += f"📝 Mensaje:\n{text[:100]}{'...' if len(text) > 100 else ''}"
        
        await update.message.reply_text(resumen)
    
    elif message_type == 'all_users':
        # Obtener todas las listas de usuarios
        vip_users = cargar_vip_users()
        admins = cargar_admins()
        
        # Crear set de todos los IDs únicos
        all_user_ids = set()
        
        # Agregar VIPs
        for vip in vip_users:
            all_user_ids.add(vip['user_id'])
        
        # Agregar admins
        for admin_id in admins:
            all_user_ids.add(admin_id)
        
        # Remover al usuario que envía el mensaje para no auto-enviarse
        all_user_ids.discard(user_id)
        
        if not all_user_ids:
            del user_states[user_id]
            return await update.message.reply_text("❌ No hay usuarios registrados para enviar mensajes.")
        
        enviados = 0
        fallidos = 0
        
        for target_user_id in all_user_ids:
            try:
                # Determinar tipo de usuario para personalizar mensaje
                es_admin = target_user_id in admins
                es_vip = any(vip['user_id'] == target_user_id for vip in vip_users)
                
                if es_admin:
                    tipo_usuario = "👑 Administrador"
                elif es_vip:
                    tipo_usuario = "💎 Usuario VIP"
                else:
                    tipo_usuario = "👤 Usuario"
                
                mensaje_final = f"🌐 Mensaje para Todos los Usuarios\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━\n{tipo_usuario}\n📢 Mensaje masivo oficial\n📞 Soporte: @frankosmel"
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=mensaje_final
                )
                enviados += 1
            except Exception as e:
                fallidos += 1
                print(f"Error enviando a {target_user_id}: {e}")
        
        resumen = f"🌐 Mensaje Masivo Global Enviado\n\n"
        resumen += f"✅ Enviados exitosos: {enviados}\n"
        resumen += f"❌ Fallos: {fallidos}\n"
        resumen += f"👥 Total usuarios únicos: {len(all_user_ids)}\n"
        resumen += f"👑 Administradores: {len(admins)}\n"
        resumen += f"💎 Usuarios VIP: {len(vip_users)}\n\n"
        resumen += f"📝 Mensaje:\n{text[:100]}{'...' if len(text) > 100 else ''}"
        
        await update.message.reply_text(resumen)
    
    # Limpiar estado
    del user_states[user_id]

# Handler para botones inline simples
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("aceptar_") or data.startswith("rechazar_"):
        user_id_str = data.split("_")[1]
        accion = data.split("_")[0]
        
        try:
            vip_user_id = int(user_id_str)
        except ValueError:
            return await query.edit_message_text("❌ ID de usuario inválido.")
        
        vip_user = buscar_vip_por_id(vip_user_id)
        if not vip_user:
            return await query.edit_message_text("⚠️ Usuario no registrado en el sistema VIP.")
        
        # Verificar que solo el usuario verificado pueda presionar el botón
        usuario_que_presiona = query.from_user.id
        
        if usuario_que_presiona != vip_user_id:
            # Enviar mensaje nuevo explicando que no debe tocar el botón
            try:
                username_quien_presiona = query.from_user.username or query.from_user.first_name or "Usuario"
                mensaje_advertencia = f"🚫 **@{username_quien_presiona}**, no debes presionar este botón.\n\n"
                mensaje_advertencia += f"⚠️ **Solo el usuario que está siendo verificado puede aceptar o rechazar la verificación.**\n\n"
                mensaje_advertencia += f"✅ **Para completar la verificación:**\n"
                mensaje_advertencia += f"• El usuario **{vip_user['username']}** debe presionar el botón correspondiente\n"
                mensaje_advertencia += f"• Solo así se puede confirmar la verificación VIP\n\n"
                mensaje_advertencia += f"💡 **Respeta el proceso de verificación del sistema.**"
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=mensaje_advertencia,
                    parse_mode='Markdown',
                    reply_to_message_id=query.message.message_id
                )
            except Exception as e:
                print(f"Error enviando mensaje de advertencia: {e}")
            return
        
        # Si es el usuario correcto, proceder con la verificación
        if accion == "aceptar":
            # Obtener información del usuario que solicitó la verificación desde el mensaje original
            mensaje_original = query.message.text or ""
            usuario_solicitante = "Usuario"
            
            # Extraer el usuario que solicitó la verificación del mensaje original
            if "Verificación solicitada por: @" in mensaje_original:
                try:
                    inicio = mensaje_original.find("Verificación solicitada por: @") + len("Verificación solicitada por: @")
                    fin = mensaje_original.find("\n", inicio)
                    if fin == -1:
                        fin = len(mensaje_original)
                    usuario_solicitante = "@" + mensaje_original[inicio:fin].strip()
                except:
                    usuario_solicitante = "Usuario"
            
            # Mensaje de verificación completada con botones útiles
            mensaje_completado = f"✅ **Verificación Completada**\n\n"
            mensaje_completado += f"💎 **{vip_user['username']} ha confirmado su identidad VIP**\n\n"
            mensaje_completado += f"🛡️ **Usuario de confianza verificado**\n"
            mensaje_completado += f"🔐 **KYC validado por administración**\n"
            mensaje_completado += f"✅ **Seguro para intercambios y transacciones**\n\n"
            mensaje_completado += f"👤 **Verificación solicitada por:** {usuario_solicitante}\n"
            mensaje_completado += f"📞 **Contacto directo disponible**"
            
            keyboard = [
                [InlineKeyboardButton("📩 Contactar", url=f"https://t.me/{vip_user['username'].lstrip('@')}")]
            ]
            
            await query.edit_message_text(
                mensaje_completado,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif accion == "rechazar":
            mensaje_rechazado = f"❌ **Verificación Rechazada**\n\n"
            mensaje_rechazado += f"⚠️ **{vip_user['username']} ha rechazado la verificación**\n\n"
            mensaje_rechazado += f"💡 **Posibles razones:**\n"
            mensaje_rechazado += f"• El usuario no autorizó la verificación\n"
            mensaje_rechazado += f"• Verificación solicitada por error\n"
            mensaje_rechazado += f"• El usuario prefiere mantener privacidad\n\n"
            mensaje_rechazado += f"📞 **Para consultas contacta:** @frankosmel"
            
            await query.edit_message_text(mensaje_rechazado, parse_mode='Markdown')

# Función para ejecutar Flask en hilo separado
def run_flask():
    try:
        print("🌐 Iniciando servidor Flask en puerto 80...")
        flask_app.run(
            host='0.0.0.0', 
            port=80, 
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"❌ Error en Flask: {e}")

# Iniciar Flask en un hilo separado
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print("✅ Servidor Flask iniciado en hilo separado")

# Iniciar aplicación
app = ApplicationBuilder().token("7533600198:AAEeBFnArsntb2Ahjq8Rw20e77nw0nLZ9zI").build()

# Comandos básicos
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("vip", vip_command))
app.add_handler(CommandHandler("addadmin", add_admin))
app.add_handler(CommandHandler("addvip", agregar_vip))
app.add_handler(CommandHandler("deladmin", eliminar_admin))
app.add_handler(CommandHandler("delvip", eliminar_vip))
app.add_handler(CommandHandler("editvip", editar_vip))
app.add_handler(CommandHandler("diagnostico", diagnostico))

# Comandos para blacklist
async def agregar_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) < 3:
        mensaje = "📝 **Para agregar a blacklist manual usa:**\n"
        mensaje += "`/addblacklist @usuario ID_telegram motivo [tarjetas] [telefono]`\n\n"
        mensaje += "📋 **Ejemplo:**\n"
        mensaje += "`/addblacklist @estafador123 987654321 \"usuario con deudas\" 9235129976578315,9204129976918161 56246700`\n\n"
        mensaje += "⚠️ Username, ID y motivo son obligatorios"
        return await update.message.reply_text(mensaje, parse_mode='Markdown')

    username = context.args[0].lstrip('@')
    try:
        user_id = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ El ID de Telegram debe ser un número válido.")

    motivo = context.args[2]
    tarjetas = context.args[3].split(',') if len(context.args) > 3 else []
    telefono = context.args[4] if len(context.args) > 4 else 'N/A'

    blacklist = cargar_blacklist()

    if buscar_blacklist_por_id(user_id):
        return await update.message.reply_text("❗Este usuario ya está en la blacklist.")

    nuevo_baneado = {
        "user_id": user_id,
        "username": f"@{username}",
        "tarjetas": tarjetas,
        "telefono": telefono,
        "motivo": motivo,
        "info_adicional": "N/A",
        "agregado_por": f"@{update.effective_user.username or 'admin'}",
        "fecha_agregado": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "estado": "baneado",
        "tipo_baneo": "manual_command"
    }

    blacklist.append(nuevo_baneado)
    guardar_blacklist(blacklist)

    mensaje = f"🚫 **Usuario Agregado a Blacklist**\n\n"
    mensaje += f"👤 Usuario: @{username}\n"
    mensaje += f"🆔 ID: {user_id}\n"
    mensaje += f"⚠️ Motivo: {motivo}\n"
    mensaje += f"💳 Tarjetas: {len(tarjetas)} registradas\n"
    mensaje += f"📱 Teléfono: {telefono}\n"
    mensaje += f"📅 Baneado: {nuevo_baneado['fecha_agregado']}\n"
    mensaje += f"👑 Baneado por: {nuevo_baneado['agregado_por']}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def eliminar_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ No tienes permisos para usar este comando.")

    if len(context.args) != 1:
        return await update.message.reply_text("📝 Uso: /delblacklist ID_telegram\n\nEjemplo: /delblacklist 987654321")

    try:
        user_id_to_remove = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ El ID debe ser un número válido.")

    blacklist = cargar_blacklist()
    user_to_remove = buscar_blacklist_por_id(user_id_to_remove)

    if not user_to_remove:
        return await update.message.reply_text("ℹ️ Este usuario no está en la blacklist.")

    # Eliminar el usuario de blacklist
    blacklist = [user for user in blacklist if user['user_id'] != user_id_to_remove]
    guardar_blacklist(blacklist)

    mensaje = f"✅ **Usuario Eliminado de Blacklist**\n\n"
    mensaje += f"👤 Usuario: {user_to_remove['username']}\n"
    mensaje += f"🆔 ID: {user_id_to_remove}\n"
    mensaje += f"⚠️ Motivo original: {user_to_remove.get('motivo', 'N/A')}\n"
    mensaje += f"📅 Eliminado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    mensaje += f"👤 Eliminado por: @{update.effective_user.username or 'admin'}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def verificar_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        mensaje = "📝 **Uso del comando /checkblacklist:**\n\n"
        mensaje += "`/checkblacklist @usuario`\n\n"
        mensaje += "📋 **Ejemplos:**\n"
        mensaje += "• `/checkblacklist @VentasChris`\n"
        mensaje += "• `/checkblacklist VentasChris` (sin @)\n\n"
        mensaje += "🔍 **Función:**\n"
        mensaje += "• Muestra TODOS los datos del usuario baneado\n"
        mensaje += "• Incluye tarjetas, teléfonos, motivos, etc.\n"
        mensaje += "• Disponible para todos los usuarios"
        return await update.message.reply_text(mensaje, parse_mode='Markdown')

    # Obtener el username y normalizarlo
    username_input = context.args[0]
    if not username_input.startswith('@'):
        username_search = f"@{username_input}"
    else:
        username_search = username_input

    print(f"DEBUG /checkblacklist: Buscando '{username_search}' (input original: '{username_input}')")
    
    blacklist_user = buscar_blacklist_por_username(username_search)

    if blacklist_user:
        print(f"DEBUG /checkblacklist: Usuario encontrado: {blacklist_user.get('username', 'N/A')}")
        # Usar la nueva función para mostrar datos completos
        mensaje = mostrar_datos_completos_blacklist(blacklist_user)
    else:
        print(f"DEBUG /checkblacklist: Usuario NO encontrado en blacklist")
        mensaje = f"✅ **{username_search} NO está en la blacklist**\n\n"
        mensaje += f"🔍 **Resultado de búsqueda:**\n"
        mensaje += f"• El usuario no ha sido reportado como problemático\n"
        mensaje += f"• No aparece en la base de datos de usuarios baneados\n"
        mensaje += f"• Puede interactuar con precaución normal\n\n"
        mensaje += f"💡 **Recomendaciones:**\n"
        mensaje += f"• Siempre mantén precaución en transacciones\n"
        mensaje += f"• Verifica identidad antes de intercambios\n"
        mensaje += f"• Si detectas actividad sospechosa, reporta a @frankosmel\n\n"
        mensaje += f"📊 **Búsqueda realizada por:** @{update.effective_user.username or 'usuario'}\n"
        mensaje += f"🕐 **Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

app.add_handler(CommandHandler("addblacklist", agregar_blacklist))
app.add_handler(CommandHandler("delblacklist", eliminar_blacklist))
app.add_handler(CommandHandler("checkblacklist", verificar_blacklist))

# Comando de emergencia para resetear estados
async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Limpiar cualquier estado activo
    clear_user_state(user_id)
    
    # Obtener teclado principal
    keyboard = obtener_teclado_principal(user_id, "private")
    
    mensaje = "🔄 Estado Reseteado\n\n"
    mensaje += "✅ Se ha limpiado cualquier proceso en curso\n"
    mensaje += "🏠 Menú principal restaurado\n\n"
    mensaje += "💡 Ahora puedes usar todos los botones normalmente"
    
    await update.message.reply_text(mensaje, reply_markup=keyboard)

# Comando para verificar estatus de administrador específico
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admins = cargar_admins()
    
    mensaje = f"🔍 **Verificación de Administrador**\n\n"
    mensaje += f"👤 **Tu información:**\n"
    mensaje += f"• ID: {user_id}\n"
    mensaje += f"• Username: @{update.effective_user.username or 'Sin username'}\n"
    mensaje += f"• Nombre: {update.effective_user.full_name or 'Sin nombre'}\n\n"
    
    if user_id == 1383931339:
        mensaje += f"👑 **ADMIN PRINCIPAL CONFIRMADO** ✅\n"
        mensaje += f"• Eres el administrador principal del sistema\n"
        mensaje += f"• Tienes acceso completo a todas las funciones\n\n"
    elif user_id in admins:
        mensaje += f"👑 **ADMINISTRADOR CONFIRMADO** ✅\n"
        mensaje += f"• Tienes permisos de administrador\n"
        mensaje += f"• Acceso a panel administrativo\n\n"
    else:
        mensaje += f"❌ **NO ERES ADMINISTRADOR**\n"
        mensaje += f"• No tienes permisos administrativos\n"
        mensaje += f"• Contacta a @frankosmel para obtener acceso\n\n"
    
    mensaje += f"📋 **Administradores registrados:** {len(admins)}\n"
    mensaje += f"💎 **Usuarios VIP registrados:** {len(cargar_vip_users())}\n"
    mensaje += f"🕐 **Verificación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

app.add_handler(CommandHandler("checkadmin", check_admin))
app.add_handler(CommandHandler("reset", reset_user))

# Comando de prueba para debug de blacklist
async def test_blacklist_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de prueba para verificar la búsqueda en blacklist"""
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ Solo para administradores.")
    
    blacklist = cargar_blacklist()
    mensaje = f"🧪 **Test de Búsqueda en Blacklist**\n\n"
    mensaje += f"📊 **Total usuarios baneados:** {len(blacklist)}\n\n"
    
    if blacklist:
        mensaje += f"📋 **Usuarios en blacklist:**\n"
        for i, user in enumerate(blacklist, 1):
            username = user.get('username', 'Sin username')
            user_id = user.get('user_id', 'Sin ID')
            mensaje += f"{i}. {username} (ID: {user_id})\n"
        
        mensaje += f"\n🔍 **Prueba de búsqueda:**\n"
        # Probar búsqueda con el primer usuario
        test_user = blacklist[0]
        test_username = test_user.get('username', '')
        mensaje += f"• Buscando: '{test_username}'\n"
        
        # Realizar búsqueda
        result = buscar_blacklist_por_username(test_username)
        if result:
            mensaje += f"• ✅ Encontrado: {result.get('username')}\n"
        else:
            mensaje += f"• ❌ NO encontrado\n"
    else:
        mensaje += f"❌ No hay usuarios en blacklist\n"
    
    mensaje += f"\n🔧 **Para probar manualmente:**\n"
    mensaje += f"`/checkblacklist @VentasChris`\n"
    mensaje += f"`/checkblacklist VentasChris`"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

app.add_handler(CommandHandler("testblacklist", test_blacklist_search))

# Comando de prueba específico para el ID problemático
async def test_specific_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de prueba para verificar el ID específico 6851550322"""
    if update.effective_user.id not in cargar_admins():
        return await update.message.reply_text("❌ Solo para administradores.")
    
    test_id = 6851550322
    mensaje = f"🧪 **Test Específico para ID {test_id}**\n\n"
    
    # Test directo de la función
    blacklist_result = buscar_blacklist_por_id(test_id)
    mensaje += f"📋 **Resultado de buscar_blacklist_por_id({test_id}):**\n"
    if blacklist_result:
        mensaje += f"✅ ENCONTRADO: {blacklist_result['username']}\n"
        mensaje += f"   🆔 ID: {blacklist_result['user_id']}\n"
        mensaje += f"   ⚠️ Motivo: {blacklist_result.get('motivo', 'N/A')}\n"
        mensaje += f"   💳 Tarjetas: {len(blacklist_result.get('tarjetas', []))}\n"
    else:
        mensaje += f"❌ NO ENCONTRADO\n"
    
    # Test de búsqueda universal
    mensaje += f"\n🔍 **Test de búsqueda universal:**\n"
    mensaje += f"Simula buscar '{test_id}' en búsqueda global\n"
    
    # Verificar datos del archivo directamente
    blacklist = cargar_blacklist()
    mensaje += f"\n📊 **Verificación directa del archivo:**\n"
    mensaje += f"Total usuarios en blacklist: {len(blacklist)}\n"
    
    for i, user in enumerate(blacklist):
        if user.get('user_id') == test_id:
            mensaje += f"✅ Usuario {i+1} COINCIDE:\n"
            mensaje += f"   Username: {user.get('username', 'N/A')}\n"
            mensaje += f"   ID: {user.get('user_id', 'N/A')} (tipo: {type(user.get('user_id'))})\n"
            mensaje += f"   Tarjetas: {user.get('tarjetas', [])}\n"
            break
    else:
        mensaje += f"❌ No encontrado en verificación directa\n"
    
    mensaje += f"\n🔧 **Para probar manualmente:**\n"
    mensaje += f"• `/checkblacklist @VentasChris`\n"
    mensaje += f"• Búsqueda universal por ID: {test_id}\n"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

app.add_handler(CommandHandler("testid", test_specific_id))

# Función para manejar verificación VIP rápida
async def handle_quick_vip_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_states or not user_states[user_id].get('quick_vip_verify'):
        return
    
    verify_type = user_states[user_id].get('verify_type', 'username')
    
    # Limpiar estado
    del user_states[user_id]
    
    if verify_type == 'username':
        username_input = text.strip()
        
        # Normalizar el username (agregar @ si no lo tiene)
        if username_input.startswith('@'):
            username_search = username_input
        else:
            username_search = f"@{username_input}"
        
        print(f"DEBUG Quick VIP verify: Input='{username_input}', search='{username_search}'")
        
        # Primero verificar en blacklist
        blacklist_user = buscar_blacklist_por_username(username_search)
        if blacklist_user:
            mensaje = f"🚫 **@{username.lstrip('@')} está en la BLACKLIST**\n\n"
            mensaje += f"⚠️ **USUARIO BANEADO** ⚠️\n\n"
            mensaje += f"🆔 ID: {blacklist_user['user_id']}\n"
            mensaje += f"⚠️ Motivo: {blacklist_user.get('motivo', 'N/A')}\n"
            mensaje += f"📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n\n"
            mensaje += f"🔴 **NO interactúes con este usuario**\n"
            mensaje += f"⚠️ **RIESGO DE ESTAFA CONFIRMADO**\n\n"
            mensaje += f"📞 **Reporte:** @frankosmel"
            await update.message.reply_text(mensaje, parse_mode='Markdown')
            return
        
        # Verificar en VIP
        vip_user = buscar_vip_por_username(username_search)
        if vip_user:
            mensaje = f"✅ **{username_search} ES USUARIO VIP VERIFICADO**\n\n"
            mensaje += f"💎 **USUARIO DE CONFIANZA CONFIRMADO**\n\n"
            mensaje += f"📋 **Información de verificación:**\n"
            mensaje += f"• 🆔 ID: {vip_user['user_id']}\n"
            mensaje += f"• 👤 Username: {vip_user['username']}\n"
            mensaje += f"• 🔐 KYC: Verificado ✅\n"
            mensaje += f"• 📅 Registrado: {vip_user.get('fecha_agregado', 'N/A')}\n"
            mensaje += f"• 👑 Verificado por: {vip_user.get('agregado_por', 'Administrador')}\n\n"
            mensaje += f"🛡️ **Usuario con respaldo administrativo completo**\n"
            mensaje += f"💎 **Seguro para intercambios y transacciones**\n\n"
            mensaje += f"✅ **Verificación realizada por:** @{update.effective_user.username or 'usuario'}"
        else:
            mensaje = f"❌ **{username_search} NO está registrado como VIP**\n\n"
            mensaje += f"🔍 **Resultado de verificación:**\n"
            mensaje += f"• El usuario no tiene estatus VIP\n"
            mensaje += f"• No ha sido verificado por administradores\n"
            mensaje += f"• No tiene respaldo KYC\n\n"
            mensaje += f"💡 **Recomendaciones:**\n"
            mensaje += f"• Mantén precaución en transacciones\n"
            mensaje += f"• Verifica identidad antes de intercambios\n"
            mensaje += f"• Para obtener estatus VIP contacta: @frankosmel\n\n"
            mensaje += f"🔍 **Verificación realizada por:** @{update.effective_user.username or 'usuario'}"
    
    elif verify_type == 'id':
        try:
            search_id = int(text)
        except ValueError:
            return await update.message.reply_text("❌ El ID debe ser un número válido. Inténtalo de nuevo:")
        
        # Primero verificar en blacklist
        blacklist_user = buscar_blacklist_por_id(search_id)
        if blacklist_user:
            mensaje = f"🚫 **ID {search_id} está en la BLACKLIST**\n\n"
            mensaje += f"⚠️ **USUARIO BANEADO** ⚠️\n\n"
            mensaje += f"👤 Username: {blacklist_user.get('username', 'N/A')}\n"
            mensaje += f"⚠️ Motivo: {blacklist_user.get('motivo', 'N/A')}\n"
            mensaje += f"📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n\n"
            mensaje += f"🔴 **NO interactúes con este usuario**\n"
            mensaje += f"⚠️ **RIESGO DE ESTAFA CONFIRMADO**\n\n"
            mensaje += f"📞 **Reporte:** @frankosmel"
            await update.message.reply_text(mensaje, parse_mode='Markdown')
            return
        
        # Verificar en VIP
        vip_user = buscar_vip_por_id(search_id)
        if vip_user:
            mensaje = f"✅ **ID {search_id} ES USUARIO VIP VERIFICADO**\n\n"
            mensaje += f"💎 **USUARIO DE CONFIANZA CONFIRMADO**\n\n"
            mensaje += f"📋 **Información de verificación:**\n"
            mensaje += f"• 👤 Username: {vip_user['username']}\n"
            mensaje += f"• 🆔 ID: {vip_user['user_id']}\n"
            mensaje += f"• 🔐 KYC: Verificado ✅\n"
            mensaje += f"• 📅 Registrado: {vip_user.get('fecha_agregado', 'N/A')}\n"
            mensaje += f"• 👑 Verificado por: {vip_user.get('agregado_por', 'Administrador')}\n\n"
            mensaje += f"🛡️ **Usuario con respaldo administrativo completo**\n"
            mensaje += f"💎 **Seguro para intercambios y transacciones**\n\n"
            mensaje += f"✅ **Verificación realizada por:** @{update.effective_user.username or 'usuario'}"
        else:
            mensaje = f"❌ **ID {search_id} NO está registrado como VIP**\n\n"
            mensaje += f"🔍 **Resultado de verificación:**\n"
            mensaje += f"• El ID no tiene estatus VIP\n"
            mensaje += f"• No ha sido verificado por administradores\n"
            mensaje += f"• No tiene respaldo KYC\n\n"
            mensaje += f"💡 **Recomendaciones:**\n"
            mensaje += f"• Mantén precaución en transacciones\n"
            mensaje += f"• Verifica identidad antes de intercambios\n"
            mensaje += f"• Para obtener estatus VIP contacta: @frankosmel\n\n"
            mensaje += f"🔍 **Verificación realizada por:** @{update.effective_user.username or 'usuario'}"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# Función para manejar búsqueda universal
async def handle_universal_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    es_admin = user_id in cargar_admins()
    
    # Obtener el tipo de búsqueda específico del estado
    search_mode = user_states[user_id].get('search_type', 'smart') if user_id in user_states else 'smart'
    
    # Limpiar estado
    if user_id in user_states:
        del user_states[user_id]
    
    # Inicializar resultados
    search_results = {
        'vip_found': None,
        'blacklist_found': None,
        'blacklist_multiple': [],
        'vip_multiple': [],
        'admin_found': None,
        'search_type': search_mode,
        'search_value': text
    }
    
    print(f"🔍 Búsqueda global iniciada: '{text}' (modo: {search_mode})")
    
    # Ejecutar búsqueda según el modo seleccionado
    if search_mode == 'username' or (search_mode == 'smart' and text.startswith('@')):
        search_results['search_type'] = 'username'
        
        # Normalizar el username para búsqueda
        if text.startswith('@'):
            username_search = text
        else:
            username_search = f"@{text}"
        
        print(f"DEBUG Universal search username: '{text}' -> '{username_search}'")
        
        search_results['vip_found'] = buscar_vip_por_username(username_search)
        search_results['blacklist_found'] = buscar_blacklist_por_username(username_search)
        
        # Buscar en administradores si es admin
        if es_admin:
            admins = cargar_admins()
            username_clean = username_search.lstrip('@').lower()
            for admin_id in admins:
                try:
                    chat = await context.bot.get_chat(admin_id)
                    if chat.username and chat.username.lower() == username_clean:
                        search_results['admin_found'] = {
                            'user_id': admin_id,
                            'username': f"@{chat.username}",
                            'nombre': chat.full_name or 'Sin nombre'
                        }
                        break
                except:
                    continue
        
        # También buscar en blacklist_multiple para consistencia
        blacklist = cargar_blacklist()
        search_text_clean = username_search.strip().lower()
        
        for user in blacklist:
            user_username = user.get("username", "").strip().lower()
            if user_username == search_text_clean:
                search_results['blacklist_multiple'].append(user)
                if not search_results['blacklist_found']:
                    search_results['blacklist_found'] = user
        
        print(f"   Búsqueda por username '{text}': VIP={bool(search_results['vip_found'])}, Blacklist={len(search_results['blacklist_multiple'])} encontrados")
    
    elif search_mode == 'id' or (search_mode == 'smart' and text.isdigit() and len(text) >= 6):
        search_results['search_type'] = 'id'
        
        try:
            search_id = int(text)
            if search_id <= 0:
                raise ValueError("ID debe ser positivo")
        except ValueError as ve:
            print(f"ERROR: ID inválido '{text}': {ve}")
            mensaje = f"❌ **ID inválido: '{text}'**\n\n"
            mensaje += f"El ID debe ser un número entero positivo.\n"
            mensaje += f"Ejemplo: 1383931339"
            await update.message.reply_text(mensaje, parse_mode='Markdown')
            return
        
        # Buscar en todas las bases
        print(f"DEBUG: Buscando ID {search_id} en todas las bases...")
        
        # Buscar VIP
        vip_found = buscar_vip_por_id(search_id)
        if vip_found:
            search_results['vip_found'] = vip_found
            search_results['vip_multiple'].append(vip_found)
            print(f"DEBUG: VIP encontrado: {vip_found['username']}")
        
        # Buscar en blacklist - CRÍTICO para mostrar datos completos
        try:
            blacklist_found = buscar_blacklist_por_id(search_id)
            if blacklist_found:
                search_results['blacklist_found'] = blacklist_found
                search_results['blacklist_multiple'].append(blacklist_found)
                print(f"DEBUG: BLACKLIST encontrado: {blacklist_found['username']} - ID: {blacklist_found['user_id']}")
            else:
                print(f"DEBUG: No se encontró ID {search_id} en blacklist")
        except Exception as e:
            print(f"DEBUG ERROR búsqueda blacklist: {e}")
            search_results['blacklist_found'] = None
        
        # Buscar en administradores si es admin
        if es_admin:
            admins = cargar_admins()
            if search_id in admins:
                try:
                    chat = await context.bot.get_chat(search_id)
                    search_results['admin_found'] = {
                        'user_id': search_id,
                        'username': f"@{chat.username}" if chat.username else 'Sin username',
                        'nombre': chat.full_name or 'Sin nombre'
                    }
                    print(f"DEBUG: Admin encontrado: {search_results['admin_found']}")
                except:
                    search_results['admin_found'] = {
                        'user_id': search_id,
                        'username': 'Sin username',
                        'nombre': 'Admin (info no disponible)'
                    }
                    print(f"DEBUG: Admin encontrado (sin info): ID {search_id}")
        
        print(f"   Búsqueda por ID {search_id}: VIP={bool(search_results['vip_found'])}, Blacklist={bool(search_results['blacklist_found'])}, Admin={bool(search_results['admin_found'])}")
    
    elif search_mode == 'phone' or (search_mode == 'smart' and any(char.isdigit() for char in text)):
        # Limpiar el número para comparación
        clean_search = ''.join(filter(str.isdigit, text))
        
        # Para búsqueda específica de teléfono o detección automática
        if search_mode == 'phone' or (search_mode == 'smart' and len(clean_search) >= 7 and len(clean_search) <= 15):
            search_results['search_type'] = 'phone'
            print(f"   Detectado como teléfono: '{clean_search}'")
            
            # Buscar en VIPs
            vip_users = cargar_vip_users()
            for vip in vip_users:
                vip_phone_raw = vip.get('telefono', '')
                # Ignorar campos vacíos o no especificados
                if not vip_phone_raw or vip_phone_raw in ['N/A', 'No especificado', 'ninguno', '']:
                    continue
                    
                vip_phone = ''.join(filter(str.isdigit, vip_phone_raw))
                # Solo buscar si hay dígitos válidos y suficientes
                if len(vip_phone) >= 7 and (clean_search in vip_phone or vip_phone in clean_search or clean_search == vip_phone):
                    search_results['vip_multiple'].append(vip)
                    print(f"     VIP encontrado: {vip['username']} con teléfono {vip.get('telefono', '')}")
            
            # Buscar en blacklist
            blacklist = cargar_blacklist()
            for user in blacklist:
                # El teléfono puede tener múltiples números separados por \n
                user_phones = user.get('telefono', '')
                if user_phones and user_phones != 'N/A':
                    # Dividir por saltos de línea para teléfonos múltiples
                    phone_numbers = user_phones.split('\n')
                    for phone_num in phone_numbers:
                        clean_user_phone = ''.join(filter(str.isdigit, phone_num.strip()))
                        if clean_user_phone and (clean_search in clean_user_phone or clean_user_phone in clean_search or clean_search == clean_user_phone):
                            search_results['blacklist_multiple'].append(user)
                            print(f"     Blacklist encontrado: {user['username']} con teléfono {phone_num.strip()}")
                            break  # Solo agregar una vez por usuario
            
            # Tomar el primer resultado para compatibilidad
            if search_results['vip_multiple']:
                search_results['vip_found'] = search_results['vip_multiple'][0]
            if search_results['blacklist_multiple']:
                search_results['blacklist_found'] = search_results['blacklist_multiple'][0]
        
        elif search_mode == 'card' or (search_mode == 'smart' and len(clean_search) >= 10):
            search_results['search_type'] = 'card'
            print(f"   Detectado como tarjeta: '{clean_search}'")
            
            # Buscar en VIPs con múltiples formatos
            vip_users = cargar_vip_users()
            for vip in vip_users:
                mlc_raw = vip.get('tarjeta_mlc', '')
                cup_raw = vip.get('tarjeta_cup', '')
                
                # Ignorar campos vacíos o no especificados
                if mlc_raw in ['N/A', 'No especificado', 'ninguna', ''] and cup_raw in ['N/A', 'No especificado', 'ninguna', '']:
                    continue
                
                mlc = ''.join(filter(str.isdigit, mlc_raw)) if mlc_raw not in ['N/A', 'No especificado', 'ninguna', ''] else ''
                cup = ''.join(filter(str.isdigit, cup_raw)) if cup_raw not in ['N/A', 'No especificado', 'ninguna', ''] else ''
                
                match_found = False
                
                # Buscar en MLC
                if mlc and len(mlc) >= 10:
                    # Coincidencia exacta o parcial
                    if clean_search in mlc or mlc in clean_search:
                        match_found = True
                    # Últimos 4 dígitos
                    elif len(clean_search) >= 4 and mlc.endswith(clean_search[-4:]):
                        match_found = True
                    # Primeros 4 dígitos
                    elif len(clean_search) >= 4 and mlc.startswith(clean_search[:4]):
                        match_found = True
                    # Formato original con espacios o guiones
                    elif text.replace(' ', '').replace('-', '') in mlc_raw or mlc_raw.replace(' ', '').replace('-', '') in text.replace(' ', '').replace('-', ''):
                        match_found = True
                
                # Buscar en CUP si no se encontró en MLC
                if not match_found and cup and len(cup) >= 10:
                    # Coincidencia exacta o parcial
                    if clean_search in cup or cup in clean_search:
                        match_found = True
                    # Últimos 4 dígitos
                    elif len(clean_search) >= 4 and cup.endswith(clean_search[-4:]):
                        match_found = True
                    # Primeros 4 dígitos
                    elif len(clean_search) >= 4 and cup.startswith(clean_search[:4]):
                        match_found = True
                    # Formato original con espacios o guiones
                    elif text.replace(' ', '').replace('-', '') in cup_raw or cup_raw.replace(' ', '').replace('-', '') in text.replace(' ', '').replace('-', ''):
                        match_found = True
                
                if match_found:
                    search_results['vip_multiple'].append(vip)
                    print(f"     VIP encontrado: {vip['username']} con tarjeta coincidente")
            
            # Buscar en blacklist usando la función existente
            found_users = buscar_blacklist_por_tarjeta(text)
            search_results['blacklist_multiple'] = found_users
            if found_users:
                search_results['blacklist_found'] = found_users[0]
                print(f"     Total blacklist encontrados: {len(found_users)} usuarios")
            
            # Tomar el primer resultado para compatibilidad
            if search_results['vip_multiple']:
                search_results['vip_found'] = search_results['vip_multiple'][0]
    
    # Generar mensaje de respuesta sin formato Markdown para evitar errores de parsing
    mensaje = f"🔍 RESULTADOS DE BÚSQUEDA UNIVERSAL\n\n"
    mensaje += f"🎯 Búsqueda: {text}\n"
    mensaje += f"📊 Tipo detectado: {search_results['search_type'].title()}\n\n"
    
    # Mostrar resultados de blacklist (prioridad máxima)
    if search_results['blacklist_multiple']:
        mensaje += f"🚫 ¡{len(search_results['blacklist_multiple'])} USUARIO(S) EN BLACKLIST!\n"
        mensaje += f"⚠️ ALERTA DE SEGURIDAD ⚠️\n\n"
        
        for i, blacklist_user in enumerate(search_results['blacklist_multiple'], 1):
            mensaje += f"{i}. {blacklist_user.get('username', 'N/A')}\n"
            mensaje += f"   🆔 ID: {blacklist_user.get('user_id', 'N/A')}\n"
            
            # Escapar caracteres especiales en el motivo
            motivo = blacklist_user.get('motivo', 'N/A')
            motivo_escaped = motivo.replace('_', ' ').replace('*', '').replace('`', '')
            mensaje += f"   ⚠️ Motivo: {motivo_escaped}\n"
            
            # Para usuarios normales, mostrar solo hasta la fecha de baneo
            if not es_admin:
                mensaje += f"   📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n\n"
            else:
                # Mostrar datos completos solo para administradores
                # Mostrar teléfonos completos
                telefono_blacklist = blacklist_user.get('telefono', 'N/A')
                if telefono_blacklist and telefono_blacklist != 'N/A':
                    telefonos = telefono_blacklist.split('\n')
                    if len(telefonos) == 1:
                        mensaje += f"   📱 Teléfono: {telefonos[0].strip()}\n"
                    else:
                        mensaje += f"   📱 Teléfonos ({len(telefonos)}):\n"
                        for j, tel in enumerate(telefonos, 1):
                            tel_clean = tel.strip()
                            if tel_clean:
                                mensaje += f"      {j}. {tel_clean}\n"
                
                # Mostrar todas las tarjetas
                tarjetas = blacklist_user.get('tarjetas', [])
                if tarjetas:
                    mensaje += f"   💳 Tarjetas ({len(tarjetas)}):\n"
                    for j, tarjeta in enumerate(tarjetas, 1):
                        tarjeta_display = str(tarjeta).strip()
                        if tarjeta_display:
                            if len(tarjeta_display) >= 16 and tarjeta_display.isdigit():
                                tarjeta_formatted = ' '.join([tarjeta_display[k:k+4] for k in range(0, len(tarjeta_display), 4)])
                                mensaje += f"      {j}. {tarjeta_formatted}\n"
                            else:
                                mensaje += f"      {j}. {tarjeta_display}\n"
                else:
                    mensaje += f"   💳 Tarjetas: Sin tarjetas registradas\n"
                
                # Información adicional
                info_adicional = blacklist_user.get('info_adicional', 'N/A')
                if info_adicional and info_adicional != 'N/A':
                    info_escaped = info_adicional.replace('_', ' ').replace('*', '').replace('`', '')
                    mensaje += f"   📝 Info adicional: {info_escaped}\n"
                
                # Datos administrativos
                mensaje += f"   📅 Baneado: {blacklist_user.get('fecha_agregado', 'N/A')}\n"
                mensaje += f"   👑 Baneado por: {blacklist_user.get('agregado_por', 'N/A')}\n"
                mensaje += f"   🔴 Estado: {blacklist_user.get('estado', 'baneado')}\n"
                mensaje += f"   📝 Tipo: {blacklist_user.get('tipo_baneo', 'manual')}\n\n"
        
        mensaje += f"🔴 NO interactúes con este(os) usuario(s)\n"
        mensaje += f"⚠️ RIESGO DE ESTAFA CONFIRMADO\n"
        if es_admin:
            mensaje += f"🚨 DATOS COMPLETOS MOSTRADOS PARA VERIFICACIÓN\n\n"
        else:
            mensaje += f"📞 Para más información contacta: @frankosmel\n\n"
        
        if search_results['vip_multiple']:
            mensaje += f"⚠️ CONFLICTO DETECTADO: {len(search_results['vip_multiple'])} usuario(s) también aparece(n) como VIP\n"
            mensaje += f"🚨 Reporta urgentemente esta inconsistencia a @frankosmel\n\n"
    
    # Mostrar resultados de administradores (solo para admins)
    elif search_results['admin_found'] and es_admin:
        mensaje += f"👑 ADMINISTRADOR ENCONTRADO\n\n"
        admin = search_results['admin_found']
        mensaje += f"👤 Username: {admin['username']}\n"
        mensaje += f"🆔 ID: {admin['user_id']}\n"
        mensaje += f"👨‍💼 Nombre: {admin['nombre']}\n"
        mensaje += f"🔐 Rol: Administrador del sistema\n\n"
        mensaje += f"👑 Usuario con privilegios administrativos\n"
        mensaje += f"🛡️ Acceso completo al sistema\n\n"
    
    # Mostrar resultados VIP si no hay blacklist ni admin
    elif search_results['vip_multiple']:
        mensaje += f"✅ {len(search_results['vip_multiple'])} USUARIO(S) VIP VERIFICADO(S)\n\n"
        
        for i, vip_user in enumerate(search_results['vip_multiple'], 1):
            mensaje += f"{i}. {vip_user.get('username', 'N/A')}\n"
            mensaje += f"   🆔 ID: {vip_user.get('user_id', 'N/A')}\n"
            
            if es_admin:
                mensaje += f"   👨‍💼 Nombre: {vip_user.get('nombre_completo', 'N/A')}\n"
                if search_results['search_type'] == 'phone':
                    mensaje += f"   📞 Teléfono: {vip_user.get('telefono', 'N/A')}\n"
                elif search_results['search_type'] == 'card':
                    mensaje += f"   💳 MLC: {vip_user.get('tarjeta_mlc', 'N/A')}\n"
                    mensaje += f"   💳 CUP: {vip_user.get('tarjeta_cup', 'N/A')}\n"
            
            mensaje += f"   📅 Registrado: {vip_user.get('fecha_agregado', 'N/A')}\n\n"
        
        mensaje += f"💎 Usuario(s) de confianza verificado(s)\n"
        mensaje += f"🛡️ Respaldo administrativo completo\n\n"
    
    else:
        mensaje += f"❌ No se encontraron coincidencias\n\n"
        mensaje += f"🔍 El dato buscado no está registrado en:\n"
        mensaje += f"• ❌ Base de datos VIP\n"
        mensaje += f"• ❌ Lista de usuarios baneados\n\n"
        mensaje += f"💡 Recomendaciones:\n"
        mensaje += f"• Verifica la ortografía/formato del dato\n"
        mensaje += f"• Para teléfonos, prueba con/sin código de país\n"
        mensaje += f"• El usuario podría no estar registrado\n"
        mensaje += f"• Para registros VIP contacta: @frankosmel\n\n"
    
    # Información de debug para admin
    if es_admin:
        mensaje += f"🔧 Debug (Admin):\n"
        mensaje += f"• Texto original: '{text}'\n"
        mensaje += f"• Texto limpio: '{''.join(filter(str.isdigit, text))}'\n"
        mensaje += f"• VIPs encontrados: {len(search_results['vip_multiple'])}\n"
        mensaje += f"• Blacklist encontrados: {len(search_results['blacklist_multiple'])}\n\n"
    
    mensaje += f"👤 Búsqueda realizada por: @{update.effective_user.username or 'usuario'}\n"
    mensaje += f"🕐 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    # Enviar sin formato Markdown para evitar errores de parsing
    await update.message.reply_text(mensaje)

# Función para limpiar estados de usuario
def clear_user_state(user_id):
    """Limpiar el estado de un usuario específico"""
    if user_id in user_states:
        del user_states[user_id]
        print(f"🔄 Estado limpiado para usuario {user_id}")

# Función para manejar todos los tipos de mensajes de texto
async def handle_all_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        # Verificar si el usuario está en algún proceso
        if user_id in user_states:
            state = user_states[user_id]
            
            if state.get('adding_vip'):
                await handle_vip_creation_step(update, context)
                return
            elif state.get('adding_admin'):
                await handle_admin_creation_step(update, context)
                return
            elif state.get('adding_blacklist'):
                await handle_blacklist_creation_step(update, context)
                return
            elif state.get('searching'):
                await handle_search(update, context)
                return
            elif state.get('searching_vip'):
                await handle_vip_search(update, context)
                return
            elif state.get('searching_blacklist'):
                await handle_blacklist_search(update, context)
                return
            elif state.get('mass_message'):
                await handle_mass_message(update, context)
                return
            elif state.get('universal_search') or state.get('global_search'):
                await handle_universal_search(update, context)
                return
            elif state.get('quick_vip_verify'):
                await handle_quick_vip_verify(update, context)
                return
        
        # Si no está en ningún proceso, manejar mensaje normal
        await manejar_mensaje_texto(update, context)
        
    except Exception as e:
        print(f"❌ Error manejando mensaje: {e}")
        import traceback
        traceback.print_exc()
        # Limpiar estado problemático
        clear_user_state(user_id)
        
        # Mensaje de error más informativo
        texto = update.message.text if update.message else "mensaje desconocido"
        await update.message.reply_text(
            f"❌ Error procesando '{texto[:50]}...'\n\n" + 
            "🔄 Intenta de nuevo o usa /start para reiniciar.\n" +
            f"📞 Si persiste el error, contacta: @frankosmel"
        )

# Handlers de mensajes
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text_messages))

# Handlers para botones inline - orden importante para evitar conflictos
app.add_handler(CallbackQueryHandler(handle_step_by_step_callback, pattern="^(start_vip_creation|start_admin_creation|start_blacklist_creation)"))
app.add_handler(CallbackQueryHandler(handle_vip_creation_confirmation, pattern="^(confirm_vip_creation|cancel_vip_creation)"))
app.add_handler(CallbackQueryHandler(handle_admin_creation_confirmation, pattern="^(confirm_admin_creation|cancel_admin_creation)"))
app.add_handler(CallbackQueryHandler(handle_blacklist_creation_confirmation, pattern="^(confirm_blacklist_creation|cancel_blacklist_creation)"))
app.add_handler(CallbackQueryHandler(button_handler, pattern="^(aceptar_|rechazar_)"))
app.add_handler(CallbackQueryHandler(admin_submenu_handler, pattern="^(admin_|vip_|menu_principal|search_menu|config_menu|mass_message|search_|config_|cancel_|blacklist_|universal_search|global_search|confirm_delete_admin_|cancel_delete_admin)"))

print("=" * 50)
print("✅ BOT VIP INICIADO CORRECTAMENTE")
print("=" * 50)
# Comentario de prueba para verificar Git
print("🌐 Servidor web iniciado en puerto 80")
print("🔄 Ejecutando en modo polling")
print("💎 Funciones activas:")
print("   • Verificación VIP: /vip @usuario")
print("   • Panel de administración completo")
print("   • Mensajes masivos y búsquedas")
print("🎯 Comandos principales:")
print("   • /start - Menú completo")
print("   • /vip @usuario - Verificar usuario")
print("   • /addvip - Agregar VIP (solo admins)")
print("   • /addadmin - Agregar admin (solo admins)")
print("🔍 Token configurado correctamente")

# Skip connection test to avoid async issues
print("📡 Configuración lista, iniciando bot directamente...")

# Verificar handlers detalladamente
command_handlers = [h for h in app.handlers[0] if isinstance(h, CommandHandler)]
callback_handlers = [h for h in app.handlers[0] if isinstance(h, CallbackQueryHandler)]
message_handlers = [h for h in app.handlers[0] if isinstance(h, MessageHandler)]

print("📋 Handlers registrados:")
print(f"   • Comandos: {len(command_handlers)}")
for cmd_handler in command_handlers:
    if hasattr(cmd_handler, 'commands'):
        commands_list = list(cmd_handler.commands)
        print(f"     - /{commands_list[0] if commands_list else 'unknown'}")

print(f"   • CallbackQuery: {len(callback_handlers)}")
print(f"   • Mensajes: {len(message_handlers)}")

print("\n🔧 CONFIGURACIÓN DEL BOT:")
print(f"   • Token: {'✅ Configurado' if app.bot.token else '❌ Falta'}")
print(f"   • Admins file: {'✅ Existe' if os.path.exists('admins.json') else '❌ No existe'}")
print(f"   • VIPs file: {'✅ Existe' if os.path.exists('vip_users.json') else '❌ No existe'}")

# Test de funciones básicas
try:
    admins_test = cargar_admins()
    vips_test = cargar_vip_users()
    print(f"   • Carga de datos: ✅ Funcional ({len(admins_test)} admins, {len(vips_test)} VIPs)")
except Exception as e:
    print(f"   • Carga de datos: ❌ Error - {e}")

print("\n🚀 EL BOT ESTÁ LISTO PARA RECIBIR COMANDOS")
print("💬 Envía /start para probar la funcionalidad")
print("=" * 50)

# Función de diagnóstico mejorada
async def verificar_admin_status(user_id):
    """Verificar si un usuario es administrador"""
    admins = cargar_admins()
    return user_id in admins

# Ejecutar bot con manejo robusto de errores
if __name__ == "__main__":
    import time
    import signal
    import sys
    import os
    
    def signal_handler(sig, frame):
        print("\n🛑 Bot detenido por el usuario")
        # Limpiar conflictos antes de salir
        resolver_conflicto_bot()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    max_retries = 3
    retry_count = 0
    base_wait_time = 10
    
    # Limpiar conflictos antes de empezar
    print("🧹 Limpiando posibles conflictos previos...")
    resolver_conflicto_bot()
    time.sleep(3)
    
    while retry_count < max_retries:
        try:
            print("🔄 Iniciando @Menuering_bot...")
            print(f"👑 Administradores registrados: {len(cargar_admins())}")
            print(f"💎 Usuarios VIP registrados: {len(cargar_vip_users())}")
            print("✅ Token configurado para @Menuering_bot")
            
            if retry_count > 0:
                print("🔧 Resolviendo conflicto antes de reintentar...")
                resolver_conflicto_bot()
                wait_time = base_wait_time + (retry_count * 5)
                print(f"⏰ Esperando {wait_time} segundos...")
                time.sleep(wait_time)
            
            print("📡 Iniciando polling con configuración anti-conflicto...")
            
            # Configuración más agresiva para evitar conflictos
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                timeout=10,
                stop_signals=None  # Desactivar señales automáticas
            )
            
            print("✅ Bot iniciado exitosamente")
            break  # Si llega aquí, el bot se ejecutó exitosamente
            
        except KeyboardInterrupt:
            print("🛑 Bot detenido por el usuario")
            resolver_conflicto_bot()
            break
        except Exception as e:
            error_msg = str(e)
            retry_count += 1
            print(f"❌ Error en el bot (intento {retry_count}/{max_retries}): {error_msg}")
            
            if "Conflict" in error_msg:
                print("🔴 CONFLICTO DETECTADO: Resolviendo automáticamente...")
                resolver_conflicto_bot()
                
                if retry_count < max_retries:
                    print(f"🔄 Reintentando en 5 segundos (intento {retry_count + 1}/{max_retries})...")
                    time.sleep(5)
                    continue
                else:
                    print("❌ Conflicto persistente después de múltiples intentos")
                    print("💡 SOLUCIÓN MANUAL REQUERIDA:")
                    print("   1. Detén el Repl completamente (Stop)")
                    print("   2. Espera 30 segundos")
                    print("   3. Inicia de nuevo (Run)")
                    break
            elif "Unauthorized" in error_msg:
                print("🔴 TOKEN INVÁLIDO: Verifica el token en BotFather")
                break
            elif "TimedOut" in error_msg or "TimeoutError" in error_msg:
                print("🔴 TIMEOUT: Problemas de conexión")
                if retry_count < max_retries:
                    print(f"🔄 Reintentando en 3 segundos...")
                    time.sleep(3)
                    continue
                else:
                    break
            else:
                print(f"🔄 Error desconocido, reintentando...")
                if retry_count >= max_retries:
                    print("❌ Máximo de reintentos alcanzado")
                    break
                time.sleep(2)
                continue
    
    print("✅ Proceso finalizado")