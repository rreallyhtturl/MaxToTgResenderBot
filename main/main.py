from telebot.formatting import escape_html

from max import MaxClient as Client
from max_bot import MaxClientBot as Client_bot
from filters import filters, user
from classes import Message, get_chatlist
from telegram import send_to_telegram
import time, os
from dotenv import load_dotenv
import telebot
import threading
import os
import json
from datetime import datetime
from Scheduler import start_scheduler
import personal_chats
import json
from telebot import types  # для inline-кнопок
import config_state  # импортируем наш модуль состояния
import env_manager

load_dotenv()
MAX_TOKEN = os.getenv("MAX_TOKEN")
MAX_CHAT_IDS = [int(x) for x in os.getenv("MAX_CHAT_IDS").split(",")]

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_ADMIN_ID = [x for x in os.getenv("TG_ADMIN_ID").split(",")]
bot = telebot.TeleBot(TG_BOT_TOKEN, parse_mode="HTML")

TG_TARGET_CHAT_IDS = os.getenv("TG_TARGET_CHAT_IDS")
if TG_TARGET_CHAT_IDS:
    TG_TARGET_CHAT_IDS = [int(x.strip()) for x in TG_TARGET_CHAT_IDS.split(",")]
else:
    TG_TARGET_CHAT_IDS = []

if MAX_TOKEN == "" or MAX_CHAT_IDS == [] or TG_BOT_TOKEN == "" or TG_CHAT_ID == "":
    print("Ошибка в .env, перепроверьтье")
MONITOR_ID = os.getenv("MONITOR_ID")

client = Client(MAX_TOKEN)
client_bot = Client_bot(MAX_TOKEN)

MAX_CHAT_IDS = [int(x) for x in os.getenv("MAX_CHAT_IDS").split(",")]
TG_ADMIN_ID = os.getenv("TG_ADMIN_ID").split(",")          # список строк
TG_TARGET_CHAT_IDS = [int(x.strip()) for x in os.getenv("TG_TARGET_CHAT_IDS").split(",")] if os.getenv("TG_TARGET_CHAT_IDS") else []
TG_CHAT_ID = int(os.getenv("TG_CHAT_ID"))

def save_env():
    """Сохраняет текущие значения глобальных переменных в .env и обновляет os.environ."""
    env_dict = env_manager.read_env()
    env_dict['MAX_CHAT_IDS'] = ','.join(str(x) for x in MAX_CHAT_IDS)
    env_dict['TG_ADMIN_ID'] = ','.join(TG_ADMIN_ID)
    env_dict['TG_TARGET_CHAT_IDS'] = ','.join(str(x) for x in TG_TARGET_CHAT_IDS)
    env_dict['TG_CHAT_ID'] = str(TG_CHAT_ID)
    # Остальные переменные (например, MAX_TOKEN, PERSONAL_CHATS_PATH) остаются без изменений
    env_manager.write_env(env_dict)
    # Обновляем текущее окружение
    os.environ['MAX_CHAT_IDS'] = env_dict['MAX_CHAT_IDS']
    os.environ['TG_ADMIN_ID'] = env_dict['TG_ADMIN_ID']
    os.environ['TG_TARGET_CHAT_IDS'] = env_dict['TG_TARGET_CHAT_IDS']
    os.environ['TG_CHAT_ID'] = env_dict['TG_CHAT_ID']


MODULES_CONFIG_FILE = '../config/config.json'

def load_modules_config():
    try:
        with open(MODULES_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        modules = config.get('modules', {})
        config_state.resender_enabled = modules.get('resender', True)
        config_state.scheduler_enabled = modules.get('scheduler', True)
        config_state.tasks_enabled = config.get('tasks', {})
        config_state.tasks_list = config.get('scheduled_tasks', [])
    except FileNotFoundError:
        save_modules_config()

def save_modules_config():
    try:
        with open(MODULES_CONFIG_FILE, 'r+', encoding='utf-8') as f:
            config = json.load(f)
            config['modules'] = {
                'resender': config_state.resender_enabled,
                'scheduler': config_state.scheduler_enabled
            }
            config['tasks'] = config_state.tasks_enabled
            config['scheduled_tasks'] = config_state.tasks_list
            f.seek(0)
            json.dump(config, f, ensure_ascii=False, indent=4)
            f.truncate()
    except FileNotFoundError:
        with open(MODULES_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "pin": "False",
                "modules": {
                    "resender": True,
                    "scheduler": True
                },
                "tasks": {},
                "scheduled_tasks": []
            }, f, ensure_ascii=False, indent=4)

def check_file_type(message: Message) -> str:
    match message._type:
        case "VIDEO":
            return f'<b>🪛 Необработанные файлы:</b> Видеофайл'
        case "AUDIO":
            return f'<b>🪛 Необработанные файлы:</b> Аудиофайл'
        case _:
            return ""


def get_forward_usr_name(message: Message) -> str:
    match message.forward_type:
        case "USER":
            return client.get_user(id=message.kwargs["link"]["message"]["sender"], _f=1).contact.names[0].name
        case "CHANNEL":
            return message.kwargs["link"]["chatName"]


def get_usr_name(message: Message) -> str:
    match message.type:
        case "USER":
            return message.user.contact.names[0].name
        case "CHANNEL":
            return "Администратор канала"


def get_chatname(message: Message) -> str:
    match message.type:
        case "USER":
            return f"<b>💬 Из чата \"{message.chatname}\"</b>:"
        case "CHANNEL":
            return f"<b>💬 Из канала \"{message.chatname}\"</b>:"


def get_file_url(message: Message) -> str:
    if message.url:
        return f'<b>🔗 Файл по ссылке:</b> {message.url}'
    else:
        return ""


@client.on_connect
def onconnect():
    if client.me != None:
        print(f'[{client.current_time()}] Имя: {client.me.contact.names[0].name}, Номер: {client.me.contact.phone}'
              f' | ID: {client.me.contact.id}\n')


@client.on_message(filters.any())
def onmessage(client: Client, message: Message):
    if not config_state.resender_enabled:
        return
    try:
        # === Загружаем все персональные ID чатов (строки) ===
        all_personal_ids = set()
        chats_data = personal_chats.load_personal_chats()  # словарь {admin_id: {chat_id: name}}
        for admin_chats in chats_data.values():
            all_personal_ids.update(admin_chats.keys())   # ключи — строковые ID чатов

        # Проверяем, есть ли chat.id в глобальном списке или в персональных
        if message.chat.id in MAX_CHAT_IDS or str(message.chat.id) in all_personal_ids:
            print(f"[DEBUG] Обрабатывается chat.id {message.chat.id}")

            forward = None
            link = False
            msg_text = escape_html(message.text) if message.text else ""
            name = get_usr_name(message)
            chat_header = get_chatname(message)

            # Обработка пересланных сообщений
            if "link" in message.kwargs:
                link_info = message.kwargs["link"]
                if link_info.get("type") == "FORWARD":
                    forwarded = link_info.get("message", {})
                    msg_text = escape_html(forwarded.get("text", ""))
                    msg_attaches = forwarded.get("attaches", [])
                    forwarded_msg_author = get_forward_usr_name(message)
                    forward = f"♻️ <U>Переслал(а) сообщение от:</U> 👤 {forwarded_msg_author}"
                    link = True
                elif link_info.get("type") == "REPLY":
                    pass  # REPLY пока не обрабатывается

            # Если есть текст или вложения
            if msg_text or message.attaches or (link and msg_attaches):
                time_str = datetime.now().strftime('%H:%M:%S')
                file_url_str = get_file_url(message)
                file_type_str = check_file_type(message)

                # Формируем сообщение в зависимости от статуса
                if message.status == "REMOVED":
                    caption = f"""
{chat_header}
<b>📜 Чат: \"{escape_html(message.chatname)}\" 
👤 {name}</b>:
<b>❯ Операция:</b> <U>❌Удалил(а) сообщение:</U>
<b>💬 Сообщение:</b> 
❯ {msg_text}
<b>🕒{time_str}</b>
{file_url_str}
{file_type_str}"""

                elif message.status == "EDITED":
                    caption = f"""
<b>📜 Чат: \"{escape_html(message.chatname)}\"
👤 {name}</b>
<b>❯ Операция:</b> <U>✏️Изменил(а) сообщение:</U>
<b>💬 Сообщение: 
❯ {msg_text}</b>
<b>🕒{time_str}</b>
{file_url_str}
{file_type_str}"""

                else:
                    caption = f"""
<b>📜 Чат: \"{escape_html(message.chatname)}\"; 
👤 {name}</b>
{forward if link else '<b>❯ Операция:</b> <U>📨Отправил(а) сообщение</U>'}
<b>💬 Сообщение:</b> 
❯ {msg_text}
<b>🕒{time_str}</b>
{file_url_str}
{file_type_str}"""

                attaches_to_send = message.attaches if not link else msg_attaches
                attachments = [attach['baseUrl'] for attach in attaches_to_send if 'baseUrl' in attach]

                # Отправка
                sent_to_admin = False
                for admin_id in TG_ADMIN_ID:
                    if personal_chats.is_personal_chat_for_admin(admin_id, message.chat.id):
                        send_to_telegram(TG_BOT_TOKEN, int(admin_id), caption, attachments)
                        sent_to_admin = True
                if not sent_to_admin:
                    send_to_telegram(TG_BOT_TOKEN, TG_CHAT_ID, caption, attachments)
    except Exception as e:
        print(f"[ОШИБКА в onmessage]: {e}")
        import traceback
        traceback.print_exc()

def status_bot():
    def errorHandler(func):
        def wrapper(message):
            try:
                func(message)
            except Exception as e:
                client_bot.disconnect()
                bot.send_message(message.chat.id, f"Ошибка: {e}❌")
        return wrapper

    def isAdmin(func):
        def wrapper(message):
            global TG_ADMIN_ID
            if str(message.from_user.id) in TG_ADMIN_ID:
                func(message)
            else:
                bot.send_message(message.chat.id, "Вы не можете воспользоваться данной командой!❌")
        return wrapper

    def fstub(func):  # заглушка
        def wrapper(message):
            if 1 == 1:
                bot.send_message(message.chat.id, f"Функция на стадии разработки⏳")
        return wrapper

    @bot.callback_query_handler(func=lambda call: True)
    @errorHandler
    @isAdmin
    def modules_callback(call):
        # Обработка переключения модулей
        if call.data == "toggle_resender":
            config_state.resender_enabled = not config_state.resender_enabled
            save_modules_config()
            # Обновляем клавиатуру
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_resender = types.InlineKeyboardButton(
                f"{'✅' if config_state.resender_enabled else '❌'} Ресендер (пересылка из Max)",
                callback_data="toggle_resender"
            )
            btn_scheduler = types.InlineKeyboardButton(
                f"{'✅' if config_state.scheduler_enabled else '❌'} Планировщик (рассылка по времени)",
                callback_data="toggle_scheduler"
            )
            markup.add(btn_resender, btn_scheduler)
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, f"Ресендер {'включён' if config_state.resender_enabled else 'отключён'}")

        elif call.data == "toggle_scheduler":
            config_state.scheduler_enabled = not config_state.scheduler_enabled
            save_modules_config()
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_resender = types.InlineKeyboardButton(
                f"{'✅' if config_state.resender_enabled else '❌'} Ресендер (пересылка из Max)",
                callback_data="toggle_resender"
            )
            btn_scheduler = types.InlineKeyboardButton(
                f"{'✅' if config_state.scheduler_enabled else '❌'} Планировщик (рассылка по времени)",
                callback_data="toggle_scheduler"
            )
            markup.add(btn_resender, btn_scheduler)
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id,
                                      f"Планировщик {'включён' if config_state.scheduler_enabled else 'отключён'}")

        elif call.data.startswith("task_"):
            task_id = call.data.split("_")[1]
            current = config_state.tasks_enabled.get(task_id, True)
            config_state.tasks_enabled[task_id] = not current
            save_modules_config()
            # Обновляем клавиатуру
            markup = types.InlineKeyboardMarkup(row_width=1)
            for task in config_state.tasks_list:
                tid = str(task['id'])
                status = config_state.tasks_enabled.get(tid, True)
                btn_text = f"{'✅' if status else '❌'} #{tid} {task['text']} ({task['hour']:02d}:{task['minute']:02d})"
                btn = types.InlineKeyboardButton(btn_text, callback_data=f"task_{tid}")
                markup.add(btn)
            markup.add(
                types.InlineKeyboardButton("✅ Включить все", callback_data="tasks_enable_all"),
                types.InlineKeyboardButton("❌ Выключить все", callback_data="tasks_disable_all")
            )
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, f"Задача #{task_id} {'включена' if not current else 'отключена'}")

        elif call.data == "tasks_enable_all":
            for task in config_state.tasks_list:
                config_state.tasks_enabled[str(task['id'])] = True
            save_modules_config()
            # Обновляем клавиатуру (аналогично коду выше)
            markup = types.InlineKeyboardMarkup(row_width=1)
            for task in config_state.tasks_list:
                tid = str(task['id'])
                status = config_state.tasks_enabled.get(tid, True)
                btn_text = f"{'✅' if status else '❌'} #{tid} {task['text']} ({task['hour']:02d}:{task['minute']:02d})"
                btn = types.InlineKeyboardButton(btn_text, callback_data=f"task_{tid}")
                markup.add(btn)
            markup.add(
                types.InlineKeyboardButton("✅ Включить все", callback_data="tasks_enable_all"),
                types.InlineKeyboardButton("❌ Выключить все", callback_data="tasks_disable_all")
            )
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "Все задачи включены")

        elif call.data == "tasks_disable_all":
            for task in config_state.tasks_list:
                config_state.tasks_enabled[str(task['id'])] = False
            save_modules_config()
            # Аналогичное обновление клавиатуры
            markup = types.InlineKeyboardMarkup(row_width=1)
            for task in config_state.tasks_list:
                tid = str(task['id'])
                status = config_state.tasks_enabled.get(tid, True)
                btn_text = f"{'✅' if status else '❌'} #{tid} {task['text']} ({task['hour']:02d}:{task['minute']:02d})"
                btn = types.InlineKeyboardButton(btn_text, callback_data=f"task_{tid}")
                markup.add(btn)
            markup.add(
                types.InlineKeyboardButton("✅ Включить все", callback_data="tasks_enable_all"),
                types.InlineKeyboardButton("❌ Выключить все", callback_data="tasks_disable_all")
            )
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "Все задачи отключены")

    @bot.message_handler(commands=['getenv'])
    @errorHandler
    @isAdmin
    def get_env(message):
        text = f"<b>Текущие настройки .env:</b>\n\n"
        text += f"MAX_CHAT_IDS: {MAX_CHAT_IDS}\n"
        text += f"TG_ADMIN_ID: {TG_ADMIN_ID}\n"
        text += f"TG_TARGET_CHAT_IDS: {TG_TARGET_CHAT_IDS}\n"
        text += f"TG_CHAT_ID: {TG_CHAT_ID}\n"
        bot.send_message(message.chat.id, text, parse_mode="HTML")

    @bot.message_handler(commands=['setenv'])
    @errorHandler
    @isAdmin
    def set_env(message):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.reply_to(message,
                         "❌ Использование: /setenv <переменная> <значение>\nПример: /setenv TG_CHAT_ID -123456789")
            return
        var_name = args[1].upper()
        value = args[2]
        if var_name == 'TG_CHAT_ID':
            try:
                new_value = int(value)
            except:
                bot.reply_to(message, "❌ TG_CHAT_ID должно быть числом.")
                return
            global TG_CHAT_ID
            TG_CHAT_ID = new_value
            save_env()
            bot.reply_to(message, f"✅ TG_CHAT_ID обновлён на {new_value}")
        else:
            bot.reply_to(message,
                         f"❌ Переменная {var_name} не поддерживается для одиночного изменения. Используйте /addto или /removefrom для списков.")

    @bot.message_handler(commands=['addto'])
    @errorHandler
    @isAdmin
    def add_to_list(message):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.reply_to(message,
                         "❌ Использование: /addto <список> <значение>\nСписки: MAX_CHAT_IDS, TG_ADMIN_ID, TG_TARGET_CHAT_IDS")
            return
        list_name = args[1].upper()
        value = args[2]
        global MAX_CHAT_IDS, TG_ADMIN_ID, TG_TARGET_CHAT_IDS

        if list_name == 'MAX_CHAT_IDS':
            try:
                val = int(value)
            except:
                bot.reply_to(message, "❌ Значение должно быть числом.")
                return
            if val in MAX_CHAT_IDS:
                bot.reply_to(message, f"❌ {val} уже есть в списке.")
                return
            MAX_CHAT_IDS.append(val)
            save_env()
            bot.reply_to(message, f"✅ Добавлено {val} в MAX_CHAT_IDS. Текущий список: {MAX_CHAT_IDS}")

        elif list_name == 'TG_ADMIN_ID':
            if value in TG_ADMIN_ID:
                bot.reply_to(message, f"❌ {value} уже есть в списке.")
                return
            TG_ADMIN_ID.append(value)
            save_env()
            bot.reply_to(message, f"✅ Добавлено {value} в TG_ADMIN_ID. Текущий список: {TG_ADMIN_ID}")

        elif list_name == 'TG_TARGET_CHAT_IDS':
            try:
                val = int(value)
            except:
                bot.reply_to(message, "❌ Значение должно быть числом.")
                return
            if val in TG_TARGET_CHAT_IDS:
                bot.reply_to(message, f"❌ {val} уже есть в списке.")
                return
            TG_TARGET_CHAT_IDS.append(val)
            save_env()
            bot.reply_to(message, f"✅ Добавлено {val} в TG_TARGET_CHAT_IDS. Текущий список: {TG_TARGET_CHAT_IDS}")

        else:
            bot.reply_to(message, f"❌ Неизвестный список {list_name}")

    @bot.message_handler(commands=['removefrom'])
    @errorHandler
    @isAdmin
    def remove_from_list(message):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.reply_to(message, "❌ Использование: /removefrom <список> <значение>")
            return
        list_name = args[1].upper()
        value = args[2]
        global MAX_CHAT_IDS, TG_ADMIN_ID, TG_TARGET_CHAT_IDS

        if list_name == 'MAX_CHAT_IDS':
            try:
                val = int(value)
            except:
                bot.reply_to(message, "❌ Значение должно быть числом.")
                return
            if val not in MAX_CHAT_IDS:
                bot.reply_to(message, f"❌ {val} нет в списке.")
                return
            MAX_CHAT_IDS.remove(val)
            save_env()
            bot.reply_to(message, f"✅ Удалено {val} из MAX_CHAT_IDS. Текущий список: {MAX_CHAT_IDS}")

        elif list_name == 'TG_ADMIN_ID':
            if value not in TG_ADMIN_ID:
                bot.reply_to(message, f"❌ {value} нет в списке.")
                return
            TG_ADMIN_ID.remove(value)
            save_env()
            bot.reply_to(message, f"✅ Удалено {value} из TG_ADMIN_ID. Текущий список: {TG_ADMIN_ID}")

        elif list_name == 'TG_TARGET_CHAT_IDS':
            try:
                val = int(value)
            except:
                bot.reply_to(message, "❌ Значение должно быть числом.")
                return
            if val not in TG_TARGET_CHAT_IDS:
                bot.reply_to(message, f"❌ {val} нет в списке.")
                return
            TG_TARGET_CHAT_IDS.remove(val)
            save_env()
            bot.reply_to(message, f"✅ Удалено {val} из TG_TARGET_CHAT_IDS. Текущий список: {TG_TARGET_CHAT_IDS}")

        else:
            bot.reply_to(message, f"❌ Неизвестный список {list_name}")

    @bot.message_handler(commands=['addtask'])
    @errorHandler
    @isAdmin
    def add_task(message):
        """Добавляет новую задачу в планировщик. Формат: /addtask час минута текст"""
        args = message.text.split(maxsplit=3)
        if len(args) < 4:
            bot.reply_to(message, "❌ Использование: /addtask <час> <минута> <текст>\nПример: /addtask 9 0 Всем привет!")
            return
        try:
            hour = int(args[1])
            minute = int(args[2])
            text = args[3]
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                bot.reply_to(message, "❌ Час должен быть от 0 до 23, минута от 0 до 59.")
                return
        except ValueError:
            bot.reply_to(message, "❌ Час и минута должны быть числами.")
            return

        # Генерируем новый ID
        new_id = 1
        if config_state.tasks_list:
            new_id = max(task['id'] for task in config_state.tasks_list) + 1

        new_task = {
            "id": new_id,
            "hour": hour,
            "minute": minute,
            "text": text
        }
        config_state.tasks_list.append(new_task)
        config_state.tasks_enabled[str(new_id)] = True  # по умолчанию включена
        save_modules_config()
        bot.reply_to(message, f"✅ Задача #{new_id} добавлена: {text} в {hour:02d}:{minute:02d}")

    @bot.message_handler(commands=['deltask'])
    @errorHandler
    @isAdmin
    def delete_task(message):
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "❌ Использование: /deltask <id задачи>")
            return
        try:
            task_id = int(args[1])
        except ValueError:
            bot.reply_to(message, "❌ ID должен быть числом.")
            return
        for i, task in enumerate(config_state.tasks_list):
            if task['id'] == task_id:
                del config_state.tasks_list[i]
                config_state.tasks_enabled.pop(str(task_id), None)
                save_modules_config()
                bot.reply_to(message, f"✅ Задача #{task_id} удалена.")
                return
        bot.reply_to(message, f"❌ Задача с ID {task_id} не найдена.")

    @bot.message_handler(commands=['modules'])
    @errorHandler
    @isAdmin
    def modules_menu(message):
        """Показывает меню управления модулями с inline-кнопками"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_resender = types.InlineKeyboardButton(
            f"{'✅' if config_state.resender_enabled else '❌'} Ресендер (пересылка из Max)",
            callback_data="toggle_resender"
        )
        btn_scheduler = types.InlineKeyboardButton(
            f"{'✅' if config_state.scheduler_enabled else '❌'} Планировщик (рассылка по времени)",
            callback_data="toggle_scheduler"
        )
        markup.add(btn_resender, btn_scheduler)
        bot.send_message(
            message.chat.id,
            "⚙️ Управление модулями бота\n\nНажмите на кнопку, чтобы включить/отключить модуль:",
            reply_markup=markup
        )

    @bot.message_handler(commands=['tasks'])
    @errorHandler
    @isAdmin
    def tasks_menu(message):
        """Показывает список задач планировщика с возможностью включения/отключения"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        for task in config_state.tasks_list:
            task_id = str(task['id'])
            status = config_state.tasks_enabled.get(task_id, True)
            btn_text = f"{'✅' if status else '❌'} #{task_id} {task['text']} ({task['hour']:02d}:{task['minute']:02d})"
            btn = types.InlineKeyboardButton(btn_text, callback_data=f"task_{task_id}")
            markup.add(btn)
        markup.add(
            types.InlineKeyboardButton("✅ Включить все", callback_data="tasks_enable_all"),
            types.InlineKeyboardButton("❌ Выключить все", callback_data="tasks_disable_all")
        )
        bot.send_message(
            message.chat.id,
            "📋 Управление задачами планировщика\n\nНажмите на задачу, чтобы изменить её статус:",
            reply_markup=markup
        )

    @bot.message_handler(commands=['modulestatus'])
    @errorHandler
    @isAdmin
    def module_status(message):
        modules_text = f"⚙️ <b>Модули:</b>\n" \
                       f"• Ресендер: {'✅ включён' if config_state.resender_enabled else '❌ отключён'}\n" \
                       f"• Планировщик: {'✅ включён' if config_state.scheduler_enabled else '❌ отключён'}\n\n"
        tasks_text = "📋 <b>Задачи планировщика:</b>\n"
        for task in config_state.tasks_list:
            task_id = str(task['id'])
            status = config_state.tasks_enabled.get(task_id, True)
            tasks_text += f"{'✅' if status else '❌'} #{task_id} {task['text']} ({task['hour']:02d}:{task['minute']:02d})\n"
        bot.send_message(message.chat.id, modules_text + tasks_text, parse_mode="HTML")

    @bot.message_handler(commands=['status'])
    @errorHandler
    def status(message):
        bot.send_message(message.chat.id, 'Бот активен✅️')

    @bot.message_handler(commands=['start'])
    @errorHandler
    def start(message):
        bot.send_message(message.chat.id, '''<b>Max resender by rreallyhtturl</b>

Бот, пересылающий сообщения из мессенджера MAX в Telegram

Бот работает на базе API мессенджера MAX и отправки запросов .json файлом по WebSockets. Написан на языке Python

<b>Ведется разработка на языке Java</b>

<U>Версия: 1.5.9 beta от 26.02.26</U>

Чтобы увидеть список команд,
введите /help

Разработчик текущей версии: <i>@rrllhttrl</i>
            ''', parse_mode='HTML')

    @bot.message_handler(commands=['send'])
    @errorHandler
    @isAdmin
    def send(message):
        argument_list = message.text.split(" ")
        if len(argument_list) < 3:
            bot.send_message(message.chat.id, "Вы не ввели id или сообщение после /send❌")
        else:
            max_chat_id = argument_list[1]
            message_body = " ".join(argument_list[2::])

            match int(max_chat_id):
                case 0:
                    bot.send_message(message.chat.id, "Отправка сообщения в этот чат невозможна!❌")
                case _:
                    client_bot.run()
                    recv = client_bot.send_message(chat_id=int(max_chat_id), text=message_body)
                    if not recv:
                        name = client_bot.get_chats(id=int(max_chat_id))
                        bot.send_message(message.chat.id,
                                         f'Сообщение в чат <b>"{name.upper()}"</b> было успешно отправлено✅')
                    else:
                        bot.send_message(message.chat.id, f"При отправке сообщения произошла ошибка: {recv}❌")

                    client_bot.disconnect()

    @bot.message_handler(commands=['add'])
    @errorHandler
    @isAdmin
    def add_personal(message):
        admin_id = message.from_user.id
        args = message.text.split()
        if len(args) < 2:
            bot.send_message(message.chat.id, "❌ Использование: /add <chat_id> [название]")
            return
        try:
            chat_id = int(args[1])
        except ValueError:
            bot.send_message(message.chat.id, "❌ ID чата должен быть числом")
            return
        if len(args) >= 3:
            name = " ".join(args[2:])
        else:
            client_bot.run()
            try:
                name = client_bot.get_chats(chat_id)
                if not name:
                    bot.send_message(message.chat.id, "❌ Не удалось получить название чата")
                    client_bot.disconnect()
                    return
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
                client_bot.disconnect()
                return
            client_bot.disconnect()
        personal_chats.add_personal_chat(admin_id, chat_id, name)
        bot.send_message(message.chat.id, f"✅ Чат {chat_id} ({name}) добавлен в ваш личный список.")

    @bot.message_handler(commands=['remove'])
    @errorHandler
    @isAdmin
    def remove_personal(message):
        admin_id = message.from_user.id
        args = message.text.split()
        if len(args) != 2:
            bot.send_message(message.chat.id, "❌ Использование: /remove <chat_id>")
            return
        try:
            chat_id = int(args[1])
        except ValueError:
            bot.send_message(message.chat.id, "❌ ID чата должен быть числом")
            return
        if personal_chats.remove_personal_chat(admin_id, chat_id):
            bot.send_message(message.chat.id, f"✅ Чат {chat_id} удалён из вашего списка.")
        else:
            bot.send_message(message.chat.id, f"❌ Чат {chat_id} не найден в вашем списке.")

    @bot.message_handler(commands=['idprop', 'list', 'personal'])
    @errorHandler
    @isAdmin
    def list_personal(message):
        admin_id = message.from_user.id
        chats = personal_chats.get_admin_chat_list(admin_id)
        if not chats:
            bot.send_message(message.chat.id, "📭 Ваш список личных чатов пуст.")
            return
        lines = [f"<code>{cid}</code> — {name}" for cid, name in chats.items()]
        bot.send_message(message.chat.id, "📋 Ваши личные чаты:\n" + "\n".join(lines), parse_mode="HTML")

    @bot.message_handler(commands=['bc'])
    @errorHandler
    @isAdmin
    def broadcast(message):
        argument_list = message.text.split()
        if len(argument_list) < 3:
            bot.send_message(message.chat.id, "❌ Вы не ввели ID чата или текст сообщения после /bc")
            return

        raw_target = argument_list[1]
        text = " ".join(argument_list[2::])

        if raw_target == "0":
            if not TG_TARGET_CHAT_IDS:
                bot.send_message(message.chat.id, "❌ Список чатов для рассылки пуст (TG_TARGET_CHAT_IDS не задан).")
                return

            results = []
            for chat_id in TG_TARGET_CHAT_IDS:
                try:
                    bot.send_message(chat_id, text, parse_mode="HTML")
                    results.append(f"✅ Чат <code>{chat_id}</code>: успешно")
                except Exception as e:
                    results.append(f"❌ Чат <code>{chat_id}</code>: {e}")
            summary = "\n".join(results)
            bot.send_message(message.chat.id, f"📨 Результаты рассылки: \n{summary}")
        else:
            try:
                target_chat_id = int(raw_target)
            except ValueError:
                bot.send_message(message.chat.id, "❌ ID чата должен быть числом (или 0 для рассылки).")
                return

            try:
                bot.send_message(target_chat_id, text, parse_mode="HTML")
                bot.send_message(message.chat.id, f"✅ Сообщение отправлено в чат {target_chat_id}")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

    @bot.message_handler(commands=['tgchats'])
    @errorHandler
    @isAdmin
    def list_targets(message):
        if not TG_TARGET_CHAT_IDS:
            bot.send_message(message.chat.id, "Список целевых чатов для рассылки пуст.")
            return
        lines = []
        for chat_id in TG_TARGET_CHAT_IDS:
            try:
                chat = bot.get_chat(chat_id)
                if chat.type == 'private':
                    name = f"{chat.first_name} {chat.last_name or ''}".strip()
                else:
                    name = chat.title
                lines.append(f"<code>{chat_id}</code> - {name}")
            except Exception as e:
                lines.append(f"<code>{chat_id}</code> - (недоступен: {e})")
        bot.send_message(message.chat.id, "📋 Целевые чаты для рассылки:\n" + "\n".join(lines), parse_mode="HTML")

    @bot.message_handler(commands=['help'])
    @errorHandler
    def help(message):
        bot.send_message(message.chat.id, """
    <b><U>ОБЩЕДОСТУПНЫЕ КОМАНДЫ:</U></b>
    /start - стартовое сообщение
    /status - статус бота
    /help - список команд

    <b><U>КОМАНДЫ ДЛЯ АДМИНА:</U></b>
    /send {чат-id чата из MAX} {Сообщение (только текст)} - ДОСТУПНО ТОЛЬКО АДМИНАМ отправить сообщение в чат MAX по чат-id
    /lschat - ДОСТУПНО ТОЛЬКО АДМИНАМ список обработанных чатов
    /pin - ДОСТУПНО ТОЛЬКО АДМИНАМ включить/отключить закрепление сообщений ботом
    /max_id {номер телефона} - ДОСТУПНО ТОЛЬКО АДМИНАМ получить чат-id из MAX по номеру телефона
    /bc {ID чата Telegram (0 - всем)} {текст} - отправить сообщение от имени бота в Telegram-чаты
    /tgchats - выводит список чатов Telegram в которые доступна рассылка
    /add {chat_id} [название] – добавить чат в список личных
    /remove {chat_id} – удалить чат из списка личных
    /idprop (или /list, /personal) – показать все сохранённые личные чаты с их названиями
    /tasks - управление отдельными задачами планировщика
    /modules - управление модулями (ресендер/планировщик)
    /modulestatus - показать состояние модулей и задач
    /addtask час минута текст - добавить новую задачу в планировщик
    /deltask id - удалить задачу по ID
    /getenv - показать текущие значения переменных .env
    /setenv TG_CHAT_ID <число> - изменить TG_CHAT_ID
    /addto MAX_CHAT_IDS|TG_ADMIN_ID|TG_TARGET_CHAT_IDS <значение> - добавить элемент в список
    /removefrom MAX_CHAT_IDS|TG_ADMIN_ID|TG_TARGET_CHAT_IDS <значение> - удалить элемент из списка
            """)

    @bot.message_handler(commands=['lschat'])
    @errorHandler
    @isAdmin
    def ls(message):
        ls = get_chatlist()
        if ls:
            bot.send_message(message.chat.id, f"""<b>Список обработанных чатов:</b>

{ls}""")
        else:
            bot.send_message(message.chat.id, f"Список обработанных чатов пуст!❌")

    @bot.message_handler(commands=['pin'])
    @errorHandler
    @isAdmin
    def pin(message):
        with open('../config/config.json', encoding='UTF-8') as f:
            data = json.load(f)
        if data["pin"] == "True":
            data["pin"] = "False"
            bot.send_message(message.chat.id, f"""Закрепление сообщений отключено!❌""")
        else:
            data["pin"] = "True"
            bot.send_message(message.chat.id, f"""Закрепление сообщений включено!✅""")
        with open('../config/config.json', 'w', encoding='UTF-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @bot.message_handler(commands=['max_id'])
    @errorHandler
    @isAdmin
    def max_id(message):
        message_body = message.text.split()
        if len(message_body) == 2:
            phone = message_body[1]
            client_bot.run()
            recv = client_bot.get_user(phone=int(phone))
            if recv:
                res = f"""<b>ПОЛЬЗОВАТЕЛЬ</b> {recv.contact.names[0].name}
                <b>CHAT_ID</b> <code>{recv.chat.id}</code>"""
                bot.send_message(message.chat.id, res)
            else:
                bot.send_message(message.chat.id, "Аккаунт по номеру телефона не найден⛔")
            client_bot.disconnect()
        else:
            bot.send_message(message.chat.id, "Вы не ввели номер‼️")

    while True:
        try:
            bot.delete_webhook(drop_pending_updates=True)
            bot.polling(non_stop=True)
        except:
            print("Ошибка статус-бота")
            time.sleep(10)
            pass


if __name__ == "__main__":
    client.run()
    threading.Thread(target=status_bot, daemon=True).start()
    start_scheduler()