from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
from session_manager import save_user_session, get_session

user_steps = {}
MAX_BUTTONS = 8
BOT_USERNAME = "kontaktuserbot"  # Укажи username своего бота без @


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0].startswith("share_"):
        msg_id = int(args[0].split("_")[1])
        session = get_session(msg_id)
        if session:
            buttons = [
                InlineKeyboardButton(text=btn, callback_data=f"{msg_id}:{i}")
                for i, btn in enumerate(session["buttons"])
            ]
            buttons.append(
                InlineKeyboardButton("📋 Скопировать ссылку", callback_data=f"share:{msg_id}")
            )

            keyboard = InlineKeyboardMarkup.from_column(buttons)
            await update.message.reply_photo(
                photo=session["photo"],
                caption=session["caption"],
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text("Инструкция не найдена ❌")
        return

    user_id = update.effective_user.id
    user_steps[user_id] = {
        "step": "photo",
        "photo": None,
        "caption": "",
        "buttons": [],
        "alerts": []
    }
    await update.message.reply_text("Шаг 1: Отправь фото.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_steps.get(user_id)
    if user and user["step"] == "photo":
        user["photo"] = update.message.photo[-1].file_id
        user["step"] = "caption"
        await update.message.reply_text("Шаг 2: Отправь подпись или /skip")
    else:
        await update.message.reply_text("Сначала напиши /start")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_steps.get(user_id)
    if not user:
        await update.message.reply_text("Сначала напиши /start")
        return

    text = update.message.text.strip()

    if user["step"] == "caption":
        user["caption"] = text
        user["step"] = "button_1"
        await update.message.reply_text("Вариант 1 (Текст | Alert) или /skip")
        return

    for i in range(1, MAX_BUTTONS + 1):
        if user["step"] == f"button_{i}":
            try:
                label, alert = text.split("|", 1)
                user["buttons"].append(label.strip())
                user["alerts"].append(alert.strip())
            except ValueError:
                await update.message.reply_text("Неверный формат. Используй: Текст | Alert")
                return

            if i < MAX_BUTTONS:
                user["step"] = f"button_{i + 1}"
                await update.message.reply_text(f"Вариант {i+1} (Текст | Alert) или /skip")
            else:
                await send_final(update, context, user_id)
            return


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_steps.get(user_id)
    if not user:
        await update.message.reply_text("Сначала напиши /start")
        return

    if user["step"] == "caption":
        user["caption"] = ""
        user["step"] = "button_1"
        await update.message.reply_text("Вариант 1 (Текст | Alert) или /skip")
        return

    if user["step"].startswith("button_"):
        await send_final(update, context, user_id)
        return


async def send_final(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    user = user_steps[user_id]
    photo = user["photo"]
    caption = user["caption"]
    buttons = user["buttons"]

    sent = await update.message.reply_photo(photo=photo, caption=caption)
    msg_id = sent.message_id

    keyboard_buttons = [
        InlineKeyboardButton(text=btn, callback_data=f"{msg_id}:{i}")
        for i, btn in enumerate(buttons)
    ]
    keyboard_buttons.append(
        InlineKeyboardButton("📋 Скопировать ссылку", callback_data=f"share:{msg_id}")
    )
    keyboard = InlineKeyboardMarkup.from_column(keyboard_buttons)

    await context.bot.edit_message_reply_markup(
        chat_id=sent.chat_id,
        message_id=sent.message_id,
        reply_markup=keyboard
    )

    save_user_session(msg_id, user)

    link = f"https://t.me/{BOT_USERNAME}?start=share_{msg_id}"
    await update.message.reply_text(f"Готово ✅\n\n🔗 Вот ссылка на инструкцию:\n{link}")

    user_steps.pop(user_id, None)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("share:"):
        msg_id = int(data.split(":")[1])
        link = f"https://t.me/{BOT_USERNAME}?start=share_{msg_id}"
        await query.answer()
        await query.message.reply_text(f"🔗 Вот ссылка на инструкцию:\n{link}")
        return

    try:
        msg_id_str, idx_str = data.split(":")
        msg_id = int(msg_id_str)
        idx = int(idx_str)
        session = get_session(msg_id)
        alert_text = session["alerts"][idx] if session and idx < len(session["alerts"]) else "Нет данных"
    except Exception:
        alert_text = "Ошибка при обработке кнопки"

    await query.answer(text=alert_text, show_alert=True)


def main():
    import os
    token = os.environ.get("8497829532:AAFkxyu-k4HxiY2K1hsRMcSS6JaQ9iZb1MA")  # безопасный способ
    if not token:
        raise ValueError("Переменная окружения BOT_TOKEN не установлена")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
