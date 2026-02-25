import threading
import time
from datetime import datetime
from telegram import send_to_telegram
import os
from dotenv import load_dotenv
import config_state

load_dotenv()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = int(os.getenv("TG_CHAT_ID"))

def send_message(text: str):
    send_to_telegram(TG_BOT_TOKEN, TG_CHAT_ID, text)

def check_and_send():
    now = datetime.now()
    current_time = (now.hour, now.minute)
    for task in config_state.tasks_list:
        task_id = str(task['id'])
        if not config_state.tasks_enabled.get(task_id, True):
            continue
        if (task["hour"], task["minute"]) == current_time:
            threading.Thread(target=send_message, args=(task["text"],), daemon=True).start()

def scheduler_loop():
    while True:
        if config_state.scheduler_enabled:
            check_and_send()
        time.sleep(60 - datetime.now().second)

def start_scheduler():
    thread = threading.Thread(target=scheduler_loop, daemon=True, name="SchedulerThread")
    thread.start()
    print("[Scheduler] Планировщик запущен.")