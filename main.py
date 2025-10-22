import os, json, asyncio, re
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")          # e.g. -1001234567890

ENFORCE_ALLOWED_PHONES = os.getenv("ENFORCE_ALLOWED_PHONES", "0") == "1"
ENFORCE_ALLOWED_USERS  = os.getenv("ENFORCE_ALLOWED_USERS",  "0") == "1"

ALLOWED_PHONES = set(p.strip() for p in os.getenv("ALLOWED_PHONES", "").split(",") if p.strip())
ALLOWED_USERS  = set(u.strip() for u in os.getenv("ALLOWED_USERS",  "").split(",") if u.strip())

REWARD_LABEL = os.getenv("REWARD_LABEL", "អាវយឺត")

if not all([BOT_TOKEN, GROUP_ID]):
    raise RuntimeError("Missing one of: BOT_TOKEN / GROUP_ID")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = DATA_DIR / "state.json"

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"phone_index": [], "user_index": []}

def save_state(state):
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

STATE = load_state()

def normalize_kh_phone(raw: str) -> str:
    p = re.sub(r"[ \-]", "", raw or "")
    if p.startswith("+"):
        digits = "+" + re.sub(r"[^\d]", "", p[1:])
    else:
        digits = re.sub(r"[^\d]", "", p)
    if digits.startswith("+855"):
        return digits
    if digits.startswith("0") and len(digits) >= 9:
        return "+855" + digits[1:]
    if digits.isdigit():
        if 8 <= len(digits) <= 12:
            return "+855" + digits if not digits.startswith("0") else "+855" + digits[1:]
    return digits

def phone_exists(phone_e164: str) -> bool:
    return phone_e164 in set(STATE.get("phone_index", []))

def user_exists(user_id: int) -> bool:
    return str(user_id) in set(STATE.get("user_index", []))

def add_phone(phone_e164: str):
    s = set(STATE.get("phone_index", []))
    s.add(phone_e164)
    STATE["phone_index"] = sorted(s)
    save_state(STATE)

def add_user(user_id: int):
    s = set(STATE.get("user_index", []))
    s.add(str(user_id))
    STATE["user_index"] = sorted(s)
    save_state(STATE)

def is_phone_allowed(phone_e164: str) -> bool:
    if not ENFORCE_ALLOWED_PHONES:
        return True
    if len(ALLOWED_PHONES) == 0:
        return False
    return phone_e164 in ALLOWED_PHONES

def is_user_allowed(user_id: int) -> bool:
    if not ENFORCE_ALLOWED_USERS:
        return True
    if len(ALLOWED_USERS) == 0:
        return False
    return str(user_id) in ALLOWED_USERS

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 ចុះឈ្មោះ"), KeyboardButton(text="👔 ទាក់ទងភ្នាក់ងារ")]],
    resize_keyboard=True
)
user_state = {}

@dp.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "សួស្ដី! នេះគឺ <b>LaLa Bot</b> (Group-only Report) សម្រាប់ចុះឈ្មោះយកអាវយឺត 👕\n"
        "សូមជ្រើសរើសពីម៉ឺនុយខាងក្រោម។",
        reply_markup=main_kb
    )

@dp.message(F.text == "👔 ទាក់ទងភ្នាក់ងារ")
async def contact_agent(msg: Message):
    await msg.answer(
        "👔 ទាក់ទងភ្នាក់ងារ:\n"
        "• Agent A: @your_agent | +855 xx xxx xxx\n"
        "• អាចកំណត់តាម ENV (not stored)"
    )

@dp.message(F.text == "📝 ចុះឈ្មោះ")
async def register_start(msg: Message):
    uid = msg.from_user.id
    user_state[uid] = {"step": "name", "src": "Register"}
    await msg.answer("សូមបញ្ចូល <b>ឈ្មោះពេញ</b> របស់អ្នក 🧍:", parse_mode=ParseMode.HTML)

@dp.message()
async def collect_flow(msg: Message):
    uid = msg.from_user.id
    if uid not in user_state:
        return
    st = user_state[uid]
    step = st.get("step")

    if step == "name":
        name = (msg.text or "").strip()
        if len(name) < 2:
            await msg.answer("ឈ្មោះមិនត្រឹមត្រូវ 😅 សូមវាយឡើងវិញ។")
            return
        st["name"] = name
        st["step"] = "phone"
        await msg.answer("✅ បានទទួលឈ្មោះ!\nឥឡូវសូមវាយ <b>លេខទូរសព្ទ</b> 📱:", parse_mode=ParseMode.HTML)
        return

    if step == "phone":
        raw = (msg.text or "").strip()
        raw_digits = re.sub(r"[^\d+]", "", raw)
        if len(re.sub(r"[^\d]", "", raw_digits)) < 8:
            await msg.answer("លេខទូរសព្ទមិនត្រឹមត្រូវ ☎️ សូមវាយឡើងវិញ (យ៉ាងហោចណាស់ 8 តួលេខ)។")
            return

        phone_e164 = normalize_kh_phone(raw)

        if user_exists(uid):
            await msg.answer(
                "⛔️ <b>Account Telegram នេះ</b> បានចុះឈ្មោះរួចហើយ។\n"
                "មិនអាចទទួលបានអាវម្តងទៀតបានទេ។",
                parse_mode=ParseMode.HTML,
                reply_markup=main_kb
            )
            user_state.pop(uid, None)
            return

        if not is_user_allowed(uid):
            await msg.answer("⛔️ Account Telegram នេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។", reply_markup=main_kb)
            user_state.pop(uid, None)
            return

        if not is_phone_allowed(phone_e164):
            await msg.answer("⛔️ លេខទូរសព្ទនេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។", reply_markup=main_kb)
            user_state.pop(uid, None)
            return

        if phone_exists(phone_e164):
            await msg.answer(
                "⚠️ លេខទូរសព្ទនេះបានចុះឈ្មោះរួចហើយ។\n"
                "មិនអាចទទួលបានអាវម្តងទៀតបានទេ។",
                parse_mode=ParseMode.HTML,
                reply_markup=main_kb
            )
            user_state.pop(uid, None)
            return

        full_name = st.get("name", "")
        src = st.get("src", "Register")

        add_user(uid)
        add_phone(phone_e164)

        member_status = "NEW"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            "🆕 <b>ការចុះឈ្មោះយកអាវយឺត</b>\n"
            f"📅 Date Time: <b>{ts}</b>\n"
            f"🆔 User ID: <code>{uid}</code>\n"
            f"👤 Full Name: <b>{full_name}</b>\n"
            f"📱 Phone: <b>{phone_e164}</b>\n"
            f"🎁 រង្វាន់: <b>{REWARD_LABEL}</b>\n"
            f"🟢 Member: <b>{member_status}</b>"
        )
        try:
            await bot.send_message(chat_id=int(GROUP_ID), text=text)
        except Exception as e:
            await msg.answer(f"⚠️ ព័ត៌មាន: មិនអាចផ្ញើទៅ Group បាន ({e})។")

        await msg.answer(
            "🎉 <b>បញ្ចប់ការចុះឈ្មោះ</b>\n\n"
            f"👤 ឈ្មោះ: <b>{full_name}</b>\n"
            f"📱 លេខ: <b>{phone_e164}</b>\n"
            f"🎁 រង្វាន់: <b>{REWARD_LABEL}</b>\n"
            "📤 បានផ្ញើរបាយការណ៍ទៅ Group ហើយ!\n",
            parse_mode=ParseMode.HTML,
            reply_markup=main_kb
        )

        user_state.pop(uid, None)
        return

async def main():
    print("🚀 LaLa bot (group-only) running — anti-dup by user & phone")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
