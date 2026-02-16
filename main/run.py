import os
import sys
import signal
import subprocess
from dotenv import load_dotenv
from telegram import send_to_telegram

# Загружаем переменные окружения
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
    """Отправляет уведомление в Telegram через существующую функцию."""
    try:
        send_to_telegram(TG_BOT_TOKEN, TG_CHAT_ID, text)
        print(f"Отправлено: {text}")
    except Exception as e:
        print(f"Не удалось отправить уведомление: {e}")

def main() -> None:
    # Отправляем сообщение о запуске
    send_notification("Бот запущен✅")

    # Запускаем starter.py как дочерний процесс
    process = subprocess.Popen([sys.executable, "starter.py"])

    def signal_handler(sig, frame):
        """Обработка сигналов завершения (Ctrl+C, SIGTERM)."""
        print(f"Получен сигнал {sig}, завершаем starter...")
        process.terminate()
        process.wait()
        send_notification("Бот остановлен⛔️")
        sys.exit(0)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ожидаем завершения starter.py
    returncode = process.wait()
    print(f"Starter завершился с кодом {returncode}")

    # Если starter завершился сам (например, из-за критической ошибки), тоже уведомляем
    send_notification(f"Бот остановлен (код {returncode})")

if __name__ == "__main__":
    main()