import os
import sys
import signal
import subprocess
import time
import datetime
from dotenv import load_dotenv
from telegram import send_to_telegram

load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

if not TG_BOT_TOKEN or not TG_CHAT_ID:
    print("Ошибка: TG_BOT_TOKEN и TG_CHAT_ID должны быть заданы в .env")
    sys.exit(1)

try:
    TG_CHAT_ID = int(TG_CHAT_ID)
except ValueError:
    print("Ошибка: TG_CHAT_ID должен быть числом")
    sys.exit(1)

def send_notification(text: str) -> None:
    try:
        send_to_telegram(TG_BOT_TOKEN, TG_CHAT_ID, text)
        print(f"Отправлено: {text}")
    except Exception as e:
        print(f"Не удалось отправить уведомление: {e}")

def run_main_loop():
    send_notification("Бот запущен✅")
    process = None

    def signal_handler(sig, frame):
        print(f"Получен сигнал {sig}, завершаем main...")
        if process:
            process.terminate()
            process.wait()
        send_notification("Бот остановлен⛔️")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            print(f"[{datetime.datetime.now()}] Запуск main.py...")
            process = subprocess.Popen([sys.executable, "main.py"])
            process.wait()
            exit_code = process.returncode
            print(f"[{datetime.datetime.now()}] main.py завершился с кодом {exit_code}. Перезапуск через 3 секунды...")
            time.sleep(3)
        except KeyboardInterrupt:
            print(f"\n[{datetime.datetime.now()}] Остановлено пользователем")
            if process:
                process.terminate()
                process.wait()
            send_notification("Бот остановлен⛔️")
            break
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Ошибка: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_main_loop()