import json
import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
from dotenv import load_dotenv

# ----------- Load .env -----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

BLOCKED_FILE = "blocked.json"
STATE_FILE = "state.json"
LIMIT_FILE = "limit.json"
USERS_FILE = "users.json"
SETTINGS_FILE = "settings.json"

# ---------- JSON helper functions ----------
def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USERS_FILE, [])
    settings = load_json(SETTINGS_FILE, {"proposal_visible": True})
    user = update.effective_user

    if user.id != ADMIN_ID and user.id not in users:
        users.append(user.id)
        save_json(USERS_FILE, users)
        username = f"@{user.username}" if user.username else "❌ username yo‘q"
        await context.bot.send_message(chat_id=ADMIN_ID,
            text=f"🆕 Yangi foydalanuvchi:\n\n👤 {user.full_name}\n🆔 {user.id}\n🔗 {username}")

    if user.id == ADMIN_ID:
        keyboard = [
            [KeyboardButton("📋 Bloklanganlar ro'yxati")],
            [KeyboardButton("📋 Limiti tugaganlar")],
            [KeyboardButton("📊 Statistika")],
            [KeyboardButton("⚙️ Taklif tugmasi boshqaruvi")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("👋 Salom Admin!", reply_markup=reply_markup)
        return

    keyboard = [[KeyboardButton("✉️ Xabar yuborish")]]
    if settings.get("proposal_visible", True):
        keyboard[0].append(KeyboardButton("Taklif yuborish"))
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Botga xush kelibsiz!", reply_markup=reply_markup)

# ---------- Handle admin (menu + reply) ----------
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_json(STATE_FILE, {})
    admin_data = state.get(str(ADMIN_ID), {})

    # --- Agar inline reply kutilyapti ---
    if admin_data.get("awaiting_reply"):
        target = admin_data["reply_to"]
        reply_text = update.message.text
        await context.bot.send_message(chat_id=target, text=f"💬 Admin xabari:\n\n{reply_text}")
        state.pop(str(ADMIN_ID))
        save_json(STATE_FILE, state)
        await update.message.reply_text("✅ Javob foydalanuvchiga yuborildi!")
        return

    # --- Admin menyusi tugmalari ---
    text = update.message.text
    if text == "📋 Bloklanganlar ro'yxati":
        blocked = load_json(BLOCKED_FILE, [])
        if blocked:
            text_msg = "🚫 Bloklanganlar:\n\n" + "\n".join(str(uid) for uid in blocked)
            keyboard = [[InlineKeyboardButton(f"♻️ Blokdan ochish {uid}", callback_data=f"unblock_{uid}")] for uid in blocked]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text_msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text("🚫 Bloklanganlar: Hech kim yo‘q")

    elif text == "📋 Limiti tugaganlar":
        limit = load_json(LIMIT_FILE, [])
        if limit:
            text_msg = f"📋 Limiti tugaganlar: {limit}"
            keyboard = [[InlineKeyboardButton("♻️ Limitni ochish", callback_data="clear_limit")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text_msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text("📋 Limiti tugaganlar: Hech kim yo‘q")

    elif text == "📊 Statistika":
        users = load_json(USERS_FILE, [])
        await update.message.reply_text(f"📊 Foydalanuvchilar soni: {len(users)}")

    elif text == "⚙️ Taklif tugmasi boshqaruvi":
        settings = load_json(SETTINGS_FILE, {"proposal_visible": True})
        status = settings.get("proposal_visible", True)
        settings["proposal_visible"] = not status
        save_json(SETTINGS_FILE, settings)
        await update.message.reply_text(
            f"⚙️ Taklif tugmasi {'ko‘rinadigan' if not status else 'ko‘rinmaydigan'} qilindi"
        )

    else:
        await update.message.reply_text("👉 Admin menyusidagi tugmalardan foydalaning.")

# ---------- Handle user messages ----------
async def handle_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        return

    state = load_json(STATE_FILE, {})
    blocked = load_json(BLOCKED_FILE, [])
    limit = load_json(LIMIT_FILE, [])
    settings = load_json(SETTINGS_FILE, {"proposal_visible": True})

    if user_id in blocked:
        await update.message.reply_text("🚫 Siz bloklangansiz.")
        return

    # --- Taklif yuborish ---
    if update.message.text == "Taklif yuborish":
        if not settings.get("proposal_visible", True):
            await update.message.reply_text("⚠️ Sozlamalar o'zgartirilgan! Botni menyu orqali yangilang.")
            return
        if user_id in limit:
            await update.message.reply_text("⚠️ Limitingiz tugagan. Boshqa taklif yubora olmaysiz.")
            return
        state[str(user_id)] = {"proposal": [], "awaiting_proposal": True}
        save_json(STATE_FILE, state)
        keyboard = [[KeyboardButton("Yuborish"), KeyboardButton("Bekor qilish")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "✍️ Taklifingizni kiriting. \n\nFoydalanish yo'riqnomasi: \n1-Manhwaga oid rasm yoki videoni yuboring, bot uni vaqtinchalik saqlab turadi. \n2-Manhwa nomini yuboring(inlgliz yoki rus tilida). \n3-Izoh qo'shing(ixtiyoriy). \n4-Yuborish tugmasini bosing. \n\nOgohlantirish: faqatgina bitta taklif yubora olasiz, shuning uchun bunga etiborli bo'ling.",
            reply_markup=reply_markup
        )
        return

    user_state = state.get(str(user_id), {})

    if user_state.get("awaiting_proposal"):
        username = f"@{update.effective_user.username}" if update.effective_user.username else "❌ username yo‘q"

        if update.message.text == "Yuborish":
            for item in user_state.get("proposal", []):
                if item["type"] == "text":
                    await context.bot.send_message(chat_id=ADMIN_ID,
                        text=f"📩 Taklif (text):\n\n👤 {update.effective_user.full_name}\n🆔 {user_id}\n🔗 {username}\n\n{item['content']}")
                elif item["type"] == "photo":
                    await context.bot.send_photo(chat_id=ADMIN_ID, photo=item["content"],
                        caption=f"📩 Taklif (photo) 👤 {update.effective_user.full_name} 🆔 {user_id} 🔗 {username}")
                elif item["type"] == "video":
                    await context.bot.send_video(chat_id=ADMIN_ID, video=item["content"],
                        caption=f"📩 Taklif (video) 👤 {update.effective_user.full_name} 🆔 {user_id} 🔗 {username}")
            state.pop(str(user_id))
            save_json(STATE_FILE, state)
            if user_id not in limit:
                limit.append(user_id)
                save_json(LIMIT_FILE, limit)

            keyboard = [[KeyboardButton("✉️ Xabar yuborish")]]
            if settings.get("proposal_visible", True):
                keyboard[0].append(KeyboardButton("Taklif yuborish"))
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("✅ Taklif yuborildi!", reply_markup=reply_markup)

        elif update.message.text == "Bekor qilish":
            state.pop(str(user_id))
            save_json(STATE_FILE, state)
            keyboard = [[KeyboardButton("✉️ Xabar yuborish")]]
            if settings.get("proposal_visible", True):
                keyboard[0].append(KeyboardButton("Taklif yuborish"))
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("❌ Taklif bekor qilindi.", reply_markup=reply_markup)

        elif update.message.text:
            user_state["proposal"].append({"type": "text", "content": update.message.text})
            state[str(user_id)] = user_state
            save_json(STATE_FILE, state)
            await update.message.reply_text("✅ Xabar saqlandi. Izoh qo'shing yoki 'Yuborish' tugmasini bosing.")
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
            user_state["proposal"].append({"type": "photo", "content": file_id})
            state[str(user_id)] = user_state
            save_json(STATE_FILE, state)
            await update.message.reply_text("✅ Rasm saqlandi. Nomini kiriting.")
        elif update.message.video:
            file_id = update.message.video.file_id
            user_state["proposal"].append({"type": "video", "content": file_id})
            state[str(user_id)] = user_state
            save_json(STATE_FILE, state)
            await update.message.reply_text("✅ Video saqlandi. Nomini kiriting.")
        return

    if update.message.text == "✉️ Xabar yuborish":
        state[str(user_id)] = {"awaiting_message": True}
        save_json(STATE_FILE, state)
        await update.message.reply_text("✍️ Xabaringizni kiriting:")
        return

    if str(user_id) in state and state[str(user_id)].get("awaiting_message"):
        state[str(user_id)]["awaiting_message"] = False
        save_json(STATE_FILE, state)
        username = f"@{update.effective_user.username}" if update.effective_user.username else "❌ username yo‘q"
        text = f"📩 Yangi xabar:\n\n👤 {update.effective_user.full_name}\n🆔 {user_id}\n🔗 {username}\n\n💬 {update.message.text}"
        keyboard = [
            [
                InlineKeyboardButton("🚫 Bloklash", callback_data=f"block_{user_id}"),
                InlineKeyboardButton("✍️ Javob yozish", callback_data=f"reply_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=reply_markup)
        await update.message.reply_text("✅ Xabaringiz yuborildi!")
    else:
        await update.message.reply_text("👉 Tugmalardan foydalaning.")

# ---------- Inline callback handler ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    blocked = load_json(BLOCKED_FILE, [])
    state = load_json(STATE_FILE, {})

    if query.from_user.id != ADMIN_ID:
        return

    if data.startswith("block_"):
        target = int(data.split("_")[1])
        if target not in blocked:
            blocked.append(target)
            save_json(BLOCKED_FILE, blocked)
            await query.message.reply_text(f"🚫 {target} bloklandi!")

    elif data.startswith("unblock_"):
        target = int(data.split("_")[1])
        if target in blocked:
            blocked.remove(target)
            save_json(BLOCKED_FILE, blocked)
            await query.message.reply_text(f"♻️ {target} blokdan ochildi!")

    elif data.startswith("reply_"):
        target = int(data.split("_")[1])

        # Inline tugmalar: Javob yozish va Bekor qilish
        keyboard = [[
            InlineKeyboardButton("✍️ Javob yozish", callback_data=f"confirm_reply_{target}"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_reply_{target}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("✍️ Javob yozish tanlandi:", reply_markup=reply_markup)

    elif data.startswith("confirm_reply_"):
        target = int(data.split("_")[2])
        state[str(ADMIN_ID)] = {"reply_to": target, "awaiting_reply": True}
        save_json(STATE_FILE, state)
        await query.message.reply_text("✍️ Javob yozing:")

    elif data.startswith("cancel_reply_"):
        target = int(data.split("_")[2])
        if str(ADMIN_ID) in state:
            state.pop(str(ADMIN_ID))
            save_json(STATE_FILE, state)
        await query.message.reply_text("❌ Javob yozish bekor qilindi.")

    elif data == "clear_limit":
        save_json(LIMIT_FILE, [])
        await query.message.reply_text("✅ Barcha foydalanuvchilar limiti ochildi!")

# ---------- Main ----------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.User(ADMIN_ID) & filters.TEXT, handle_admin))
    app.add_handler(MessageHandler(filters.ALL & (~filters.User(ADMIN_ID)), handle_user))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot ishlayapti...")
    app.run_polling()

if __name__ == "__main__":
    main()
