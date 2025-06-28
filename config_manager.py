import json
import os

CONFIG_FILE = "config.json"
MENSAJES_FILE = "mensajes.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        # archivo por defecto
        default_config = {
            "admin_id": 1383931339,
            "origen_chat_id": "",
            "destinos": [],
            "intervalo_segundos": 60,
            "horario": {
                "activo": False,
                "inicio": "09:00",
                "fin": "22:00"
            }
        }
        save_config(default_config)
        return default_config
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_mensajes():
    if not os.path.exists(MENSAJES_FILE):
        save_mensajes([])
        return []
    with open(MENSAJES_FILE, "r") as f:
        return json.load(f)

def save_mensajes(mensajes):
    with open(MENSAJES_FILE, "w") as f:
        json.dump(mensajes, f, indent=4)
