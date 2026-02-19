import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения (если ещё не загружены)
load_dotenv()

# Получаем путь из .env или используем папку по умолчанию (рядом с этим файлом)
base_path = os.getenv("PERSONAL_CHATS_PATH")
if base_path:
    PERSONAL_CHATS_FILE = Path(base_path) / "personal_chats.json"
else:
    PERSONAL_CHATS_FILE = Path(__file__).parent / "personal_chats.json"

# Убедимся, что папка существует
PERSONAL_CHATS_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_personal_chats():
    if not PERSONAL_CHATS_FILE.exists():
        return {}
    with open(PERSONAL_CHATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_personal_chats(chats):
    with open(PERSONAL_CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=4)

def get_admin_chats(admin_id):
    chats = load_personal_chats()
    return chats.get(str(admin_id), {})

def add_personal_chat(admin_id, chat_id, name):
    chats = load_personal_chats()
    admin_key = str(admin_id)
    if admin_key not in chats:
        chats[admin_key] = {}
    chats[admin_key][str(chat_id)] = name
    save_personal_chats(chats)

def remove_personal_chat(admin_id, chat_id):
    chats = load_personal_chats()
    admin_key = str(admin_id)
    if admin_key in chats and str(chat_id) in chats[admin_key]:
        del chats[admin_key][str(chat_id)]
        save_personal_chats(chats)
        return True
    return False

def get_admin_chat_list(admin_id):
    chats = load_personal_chats()
    return chats.get(str(admin_id), {})

def is_personal_chat_for_admin(admin_id, chat_id):
    chats = load_personal_chats()
    admin_chats = chats.get(str(admin_id), {})
    return str(chat_id) in admin_chats