import json
from pathlib import Path

PERSONAL_CHATS_FILE = Path(__file__).parent / "personal_chats.json"

def load_personal_chats():
    if not PERSONAL_CHATS_FILE.exists():
        return {}
    with open(PERSONAL_CHATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_personal_chats(chats):
    with open(PERSONAL_CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=4)

def add_personal_chat(chat_id, name):
    chats = load_personal_chats()
    chats[str(chat_id)] = name
    save_personal_chats(chats)

def remove_personal_chat(chat_id):
    chats = load_personal_chats()
    if str(chat_id) in chats:
        del chats[str(chat_id)]
        save_personal_chats(chats)
        return True
    return False

def get_personal_chats():
    return load_personal_chats()

def is_personal_chat(chat_id):
    return str(chat_id) in load_personal_chats()