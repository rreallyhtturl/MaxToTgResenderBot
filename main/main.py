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
<b>{time_str}</b>
{file_url_str}
{file_type_str}"""
                elif message.status == "EDITED":
                    caption = f"""
<b>📜 Чат: \"{escape_html(message.chatname)}\"
👤 {name}</b>
<b>❯ Операция:</b> <U>✏️Изменил(а) сообщение:</U>

<b>💬 Сообщение: 
❯ {msg_text}</b>
<b>{time_str}</b>
{file_url_str}
{file_type_str}"""
                else:
                    caption = f"""
<b>📜 Чат: \"{escape_html(message.chatname)}\"; 
👤 {name}</b>
{forward if link else '<b>❯ Операция:</b> <U>📨Отправил(а) сообщение</U>'}

<b>💬 Сообщение:</b> 
❯ {msg_text}
<b>{time_str}</b>
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

<U>Версия: 1.4.1 beta от 19.02.26</U>

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