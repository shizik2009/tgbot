
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.dispatcher.filters import Text

BOT_TOKEN = "8483128901:AAFQHcjoJ-XOGrr7c03lp5dQKs8tVDpleMA"
ADMIN_IDS = [5441886169, 1797229763]

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

admin_msg_to_user = {}             # admin message_id -> user_id
admin_reply_state = {}             # admin_id -> user_id (режим ответа)
admin_reply_context = {}           # admin_id -> (user_id, message_id, original_text)
anon_messages = {}                  # (user_id, message_id) -> текст сообщения

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "🚀 Здесь можно отправить анонимное сообщение человеку, который опубликовал эту ссылку\n"
        "🖊 Напишите сюда всё, что хотите ему передать.\n"
        "Поддерживаются: фото, видео, текст, голосовые, видеосообщения и стикеры."
    )

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def user_message_handler(message: types.Message):
    user = message.from_user

    # Обработка режима ответа админов
    if user.id in ADMIN_IDS and user.id in admin_reply_state:
        to_user_id = admin_reply_state[user.id]
        original_text = admin_reply_context.get(user.id, ("", 0, "Текст недоступен"))[2]

        try:
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✍️ Написать ещё", callback_data="send_again")
            )
            resp_text = message.text or "<не текстовое сообщение>"

            await bot.send_message(
                to_user_id,
                f"💌 Вам ответили на анонимное сообщение:\n\n"
                f"✉️ Сообщение, на которое отвечали:\n{original_text}\n\n"
                f"📝 Ответ администратора:\n{resp_text}",
                reply_markup=keyboard
            )
            await bot.send_message(user.id, "✉️ Ваш ответ отправлен.", reply_markup=keyboard)
        except Exception:
            await bot.send_message(user.id, "❗️ Ошибка при отправке сообщения пользователю.")

        admin_reply_state.pop(user.id, None)
        admin_reply_context.pop(user.id, None)
        return

    # Сохраняем текст для цитаты
    if message.content_type == "text":
        anon_messages[(user.id, message.message_id)] = message.text

    # Формируем кнопки для админов
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Посмотреть автора", callback_data=f"who_{message.message_id}_{user.id}"),
        InlineKeyboardButton("Ответить", callback_data=f"reply_{message.message_id}_{user.id}")
    )

    # Отправляем сообщение а��минам
    for admin_id in ADMIN_IDS:
        if message.content_type == "text":
            sent_admin_msg = await bot.send_message(
            admin_id,
            f"📨 Новое анонимное сообщение:\n\n{message.text}",
            reply_markup=kb
        )
        else:
              await bot.send_message(
                 admin_id,
                 f"📨 Новое анонимное сообщение с типом {message.content_type}",
                 reply_markup=kb 
        )
              await message.copy_to(admin_id) 

    admin_msg_to_user[sent_admin_msg.message_id] = user.id
    # Подтверждение пользователю
    await bot.send_message(user.id, "✉️ Сообщение доставлено. Ожидайте ответа!")


@dp.callback_query_handler(Text(startswith="who_"))
async def callback_who(callback: CallbackQuery):
    _, msg_id, user_id = callback.data.split("_")
    user_id = int(user_id)

    try:
        user = await bot.get_chat(user_id)
        text = (f"🕵️‍♂️ Автор сообщения:\n"
                f" Имя: {user.full_name}\n"
                f" ID: {user_id}\n"
                f" Username: @{user.username if user.username else 'нет'}")
    except Exception:
        text = "❗️ Не удалось получить информацию об авторе."

    # Вместо alert отправляем сообщение
    await bot.send_message(callback.from_user.id, text)
    await callback.answer()  # чтобы убрать часики у кнопки

@dp.callback_query_handler(Text(startswith="reply_"))
async def callback_reply(callback: CallbackQuery):
    _, msg_id, user_id = callback.data.split("_")
    user_id = int(user_id)
    admin_id = callback.from_user.id

    original_text = anon_messages.get((user_id, int(msg_id)), "Текст недоступен")

    admin_reply_state[admin_id] = user_id
    admin_reply_context[admin_id] = (user_id, int(msg_id), original_text)

    # Сообщение в чат вместо alert
    await bot.send_message(admin_id, 
        "✍️ Вы вошли в режим ответа пользователю {0}.\n"
        "\n"
        "📝Оригинальное сообщение:\n{1}".format(user_id, original_text)
    )
    await callback.answer()

@dp.callback_query_handler(Text(equals="send_again"))
async def callback_send_again(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if admin_id in admin_reply_state:
        # Сообщение в чат вместо alert
        await bot.send_message(admin_id, "Напишите новый ответ.")
    else:
        await bot.send_message(admin_id, "Вы не в режиме ответа.")
    await callback.answer()

if __name__ == "__main__":
    executor.start_polling(dp)

