import sqlite3
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import logging

# ================= НАСТРОЙКИ =================
TOKEN = "8403087254:AAHPZ0TfCk74CWp7F-3UxX8jKJcxxAy9AVs"
ADMIN_ID = 5347419966  # ТОЛЬКО ТВОЙ ID

ALL_NAMES = ["Эльхан", "Гульсум", "Доминик", "Миразиз", "ИмранНазаров", "Теодор"]

USERNAME_TO_NAME = {
    "@sharapov_02": "Эльхан",
    "@love_is090": "Гульсум",
    "@successmydevision": "Доминик",
    "@Nooob_Proooo": "Миразиз",
    "@imka2013": "ИмранНазаров",
    "@theostorm012": "Теодор"
}

# ================= ЛОГИРОВАНИЕ =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= БАЗА ДАННЫХ =================
conn = sqlite3.connect("santa.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS participants (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    assigned_name TEXT
)
""")
conn.commit()

# ================= БОТ =================
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

logger.info("=" * 50)
logger.info(f"🎅 ТАЙНЫЙ САНТА БОТ ЗАПУЩЕН!")
logger.info(f"👑 АДМИН ID: {ADMIN_ID}")
logger.info("=" * 50)

# ================= КОМАНДА /start =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    logger.info(f"/start от {message.from_user.id} (@{message.from_user.username})")
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎁 Участвовать", callback_data="participate"))
    await message.answer(
        "Привет! Нажми кнопку, чтобы участвовать в Тайном Санте 🎅",
        reply_markup=keyboard
    )

# ================= КНОПКА "УЧАСТВОВАТЬ" =================
@dp.callback_query_handler(lambda c: c.data == "participate")
async def participate_callback(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    username = callback_query.from_user.username
    
    logger.info(f"Кнопка нажата: user_id={user_id}, username={username}")
    
    if not username:
        await callback_query.message.answer("❌ Нет username. Поставь в настройках Telegram.")
        await callback_query.answer()
        return
    
    # Проверяем, участвовал ли уже
    cursor.execute("SELECT assigned_name FROM participants WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        await callback_query.message.answer(f"🎄 Ты уже участвуешь! Тебе выпал: **{result[0]}**", parse_mode="Markdown")
        await callback_query.answer()
        return
    
    # Получаем уже выданные имена
    cursor.execute("SELECT assigned_name FROM participants")
    used_names = [row[0] for row in cursor.fetchall()]
    free_names = [n for n in ALL_NAMES if n not in used_names]
    
    # Исключаем собственное имя
    user_key = f"@{username}"
    if user_key in USERNAME_TO_NAME:
        my_name = USERNAME_TO_NAME[user_key]
        if my_name in free_names:
            free_names.remove(my_name)
    
    if not free_names:
        await callback_query.message.answer("🎁 Все имена уже разобрали!")
        await callback_query.answer()
        return
    
    # Выдаём случайное имя
    chosen = random.choice(free_names)
    
    # Сохраняем в базу
    cursor.execute(
        "INSERT INTO participants (user_id, username, assigned_name) VALUES (?, ?, ?)",
        (user_id, username, chosen)
    )
    conn.commit()
    
    await callback_query.message.answer(f"🎅 Твой получатель подарка: **{chosen}**", parse_mode="Markdown")
    await callback_query.answer()

# ================= АДМИН: /admin =================
@dp.message_handler(commands=["admin"])
async def admin_list(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"/admin запрошен от {user_id} (нужен {ADMIN_ID})")
    
    if user_id != ADMIN_ID:
        logger.warning(f"ОТКАЗ В ДОСТУПЕ! {user_id} != {ADMIN_ID}")
        await message.answer("❌ Нет доступа! Эта команда только для организатора.")
        return
    
    logger.info(f"ДОСТУП РАЗРЕШЁН для админа {ADMIN_ID}")
    cursor.execute("SELECT username, assigned_name FROM participants")
    rows = cursor.fetchall()
    
    if not rows:
        await message.answer("📭 Никто не участвовал.")
        return
    
    text = "📋 **Список участников:**\n\n"
    for username, name in rows:
        text += f"@{username} → {name}\n"
    
    await message.answer(text, parse_mode="Markdown")

# ================= АДМИН: /reset =================
@dp.message_handler(commands=["reset"])
async def reset_all(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"/reset запрошен от {user_id} (нужен {ADMIN_ID})")
    
    if user_id != ADMIN_ID:
        logger.warning(f"ОТКАЗ В ДОСТУПЕ ДЛЯ /reset! {user_id} != {ADMIN_ID}")
        await message.answer("❌ Нет доступа! Эта команда только для организатора.")
        return
    
    cursor.execute("DELETE FROM participants")
    conn.commit()
    logger.info("✅ База данных ОЧИЩЕНА!")
    await message.answer("✅ **Все результаты сброшены!**\nУчастники могут нажимать 'Участвовать' заново.", parse_mode="Markdown")

# ================= АДМИН: /disqualify =================
@dp.message_handler(commands=["disqualify"])
async def disqualify_user(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ Нет доступа!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Используй: `/disqualify @username`", parse_mode="Markdown")
        return
    
    username_to_remove = args[1]
    cursor.execute("DELETE FROM participants WHERE username=?", (username_to_remove,))
    conn.commit()
    
    if cursor.rowcount > 0:
        await message.answer(f"✅ {username_to_remove} дисквалифицирован!")
    else:
        await message.answer(f"❌ {username_to_remove} не найден.")

# ================= АДМИН: /message =================
@dp.message_handler(commands=["message"])
async def message_user(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ Нет доступа!")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Используй: `/message @username текст`", parse_mode="Markdown")
        return
    
    username_to = args[1]
    text_to_send = args[2]
    
    cursor.execute("SELECT user_id FROM participants WHERE username=?", (username_to,))
    row = cursor.fetchone()
    
    if not row:
        await message.answer(f"❌ {username_to} не найден.")
        return
    
    user_id_to = int(row[0])
    await bot.send_message(user_id_to, f"📩 **Сообщение от организатора:**\n\n{text_to_send}", parse_mode="Markdown")
    await message.answer(f"✅ Отправлено @{username_to}")

# ================= АДМИН: /remind =================
@dp.message_handler(commands=["remind"])
async def remind_all(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ Нет доступа!")
        return
    
    # Получаем текст напоминания
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Используй: `/remind текст_напоминания`\n\n"
            "**Пример:**\n"
            "`/remind Не забудьте купить подарки до пятницы! 🎁`",
            parse_mode="Markdown"
        )
        return
    
    reminder_text = args[1]
    
    # Получаем всех участников
    cursor.execute("SELECT user_id, username FROM participants")
    rows = cursor.fetchall()
    
    if not rows:
        await message.answer("📭 Нет участников для рассылки.")
        return
    
    success_count = 0
    fail_count = 0
    fail_usernames = []
    
    for user_id_db, username in rows:
        try:
            await bot.send_message(
                int(user_id_db),
                f"🔔 **Напоминание от организатора:**\n\n{reminder_text}",
                parse_mode="Markdown"
            )
            success_count += 1
            logger.info(f"Напоминание отправлено @{username}")
        except Exception as e:
            logger.error(f"Не удалось отправить @{username}: {e}")
            fail_count += 1
            fail_usernames.append(username)
    
    # Формируем отчёт
    report = f"✅ **Рассылка завершена!**\n\n📨 Отправлено: {success_count} участникам\n❌ Не отправлено: {fail_count}"
    
    if fail_usernames:
        report += f"\n\n**Не удалось отправить:**\n" + "\n".join([f"• @{u}" for u in fail_usernames[:5]])
        if len(fail_usernames) > 5:
            report += f"\n• ... и ещё {len(fail_usernames) - 5}"
    
    await message.answer(report, parse_mode="Markdown")

# ================= КОМАНДА /myid для проверки =================
@dp.message_handler(commands=["myid"])
async def my_id(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"/myid от {user_id} (@{username})")
    await message.answer(f"📊 **Твой ID:** `{user_id}`\n**Username:** @{username}", parse_mode="Markdown")

# ================= КОМАНДА /help =================
@dp.message_handler(commands=["help"])
async def help_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        help_text = (
            "🎅 **Команды для организатора:**\n\n"
            "`/admin` - посмотреть список участников\n"
            "`/reset` - сбросить всех (начать заново)\n"
            "`/disqualify @username` - удалить участника\n"
            "`/message @username текст` - написать участнику\n"
            "`/remind текст` - разослать напоминание всем\n"
            "`/myid` - узнать свой ID\n\n"
            "**Для участников:**\n"
            "Просто нажми кнопку '🎁 Участвовать'!"
        )
    else:
        help_text = (
            "🎅 **Привет! Я бот Тайный Санта!**\n\n"
            "1. Нажми кнопку '🎁 Участвовать'\n"
            "2. Получи случайное имя одноклассника\n"
            "3. Приготовь подарок для этого человека!\n\n"
            "❓ Если кнопка не появляется, напиши /start"
        )
    
    await message.answer(help_text, parse_mode="Markdown")

# ================= ЗАПУСК =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)