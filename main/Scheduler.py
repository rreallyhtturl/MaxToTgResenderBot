# scheduler.py
import threading
import time
from datetime import datetime
from telegram import send_to_telegram
import os
from dotenv import load_dotenv

load_dotenv()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = int(os.getenv("TG_CHAT_ID"))

# Список задач: каждая задача — это словарь с ключами 'hour', 'minute', 'text'
TASKS = [
    {"hour": 9, "minute": 0, "text": "Доброе утро! ☀️"},
    {"hour": 13, "minute": 0, "text": "Пора обедать! 🍲"},
    {"hour": 21, "minute": 3, "text": "Спокойной ночи! 🌙"},
]

def send_message(text: str):
    """Отправляет текст в Telegram через существующую функцию."""
    send_to_telegram(TG_BOT_TOKEN, TG_CHAT_ID, text)

def check_and_send():
    """Проверяет текущее время и отправляет сообщения, если совпадает с задачей."""
    now = datetime.now()
    current_time = (now.hour, now.minute)
    for task in TASKS:
        if (task["hour"], task["minute"]) == current_time:
            # Отправляем в отдельном потоке, чтобы не задерживать цикл
            threading.Thread(target=send_message, args=(task["text"],), daemon=True).start()

def scheduler_loop():
    """
    Бесконечный цикл, который каждые 60 секунд проверяет время и запускает задачи.
    Работает в фоновом потоке.
    """
    while True:
        check_and_send()
        # Спим до следующей минуты (60 секунд), но можно сделать точнее,
        # вычислив секунды до следующей минуты, чтобы минимизировать задержку.
        time.sleep(60 - datetime.now().second)  # засыпаем до начала следующей минуты

def start_scheduler():
    """Запускает планировщик в отдельном потоке-демоне."""
    print("DEBUG: start_scheduler() вызван")
    thread = threading.Thread(target=scheduler_loop, daemon=True, name="SchedulerThread")
    thread.start()
    print("[Scheduler] Планировщик запущен. Задачи:", ...)