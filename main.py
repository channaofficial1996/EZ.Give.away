import os, json, asyncio, re
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

# -------- ENV --------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID  = os.getenv("GROUP_ID")          # e.g. -1003027286018

# Optional: Admins (CSV of Telegram user IDs) to use /groupid
ADMIN_IDS = set(u.strip() for u in os.getenv("ADMIN_IDS", "").split(",") if u.strip())

# Anti-dup + allow-lists
ENFORCE_ALLOWED_USERS  = os.getenv("ENFORCE_ALLOWED_USERS",  "0") == "1"
ENFORCE_ALLOWED_PHONES = os.getenv("ENFORCE_ALLOWED_PHONES", "0") == "1"
ALLOWED_USERS  = set(u.strip() for u in os.getenv("ALLOWED_USERS",  "").split(",") if u.strip())
ALLOWED_PHONES = set(p.strip() for p in os.getenv("ALLOWED_PHONES", "").split(",") if p.strip())

# Khmer reward label
REWARD_LABEL = os.getenv("REWARD_LABEL", "អាវយឺត")

if not all([BOT_TOKEN, GROUP_ID]):
    raise RuntimeError("Missing one of: BOT_TOKEN / GROUP_ID")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# -------- Local store (anti-dup) --------
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
    """Normalize to E.164 KH (+855...). Accepts +855, leading 0, or digits."""
    p = re.sub(r"[ \-]", "", raw or "")
    digits = "+" + re.sub(r"[^\d]", "", p[1:]) if p.startswith("+") else re.sub(r"[^\d]", "", p)
    if digits.startswith("+855"):
        return digits
    if digits.startswith("0") and len(digits) >= 9:
        return "+855" + digits[1:]
    if digits.isdigit() and 8 <= len(digits) <= 12:
        return "+855" + (digits if not digits.startswith("0") else digits[1:])
    return digits

def user_exists(uid: int) -> bool:
    return str(uid) in set(STATE.get("user_index", []))

def phone_exists(phone_e164: str) -> bool:
    return phone_e164 in set(STATE.get("phone_index", []))

def add_user(uid: int):
    s = set(STATE.get("user_index", [])); s.add(str(uid))
    STATE["user_index"] = sorted(s); save_state(STATE)

def add_phone(phone_e164: str):
    s = set(STATE.get("phone_index", [])); s.add(phone_e164)
    STATE["phone_index"] = sorted(s); save_state(STATE)

def is_user_allowed(uid: int) -> bool:
    if not ENFORCE_ALLOWED_USERS: return True
    return str(uid) in ALLOWED_USERS and len(ALLOWED_USERS) > 0

def is_phone_allowed(phone_e164: str) -> bool:
    if not ENFORCE_ALLOWED_PHONES: return True
    return phone_e164 in ALLOWED_PHONES and len(ALLOWED_PHONES) > 0

# -------- UI --------
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 ចុះឈ្មោះ"), KeyboardButton(text="👔 ទាក់ទងភ្នាក់ងារ")]],
    resize_keyboard=True
)
user_state = {}  # uid -> {"step": "name"/"phone", "src": "Register", "name": str}

# -------- Commands --------
@dp.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "សួស្ដី! នេះគឺ <b>LaLa Bot</b> (Group-only) សម្រាប់ចុះឈ្មោះយកអាវយឺត 👕\n"
        "សូមជ្រើសរើសពីម៉ឺនុយខាងក្រោម។",
        reply_markup=main_kb
    )

@dp.message(F.text == "/myid")
async def myid_cmd(msg: Message):
    uid = msg.from_user.id
    await msg.answer(f"🆔 Your Telegram User ID: <code>{uid}</code>", parse_mode=ParseMode.HTML)

@dp.message(F.text == "/groupid")
async def groupid_cmd(msg: Message):
    uid = str(msg.from_user.id)
    if ADMIN_IDS and uid not in ADMIN_IDS:
        await msg.answer("⛔️ Only admins can use /groupid")
        return
    chat_id = msg.chat.id
    await msg.answer(f"💬 This chat id: <code>{chat_id}</code>", parse_mode=ParseMode.HTML)

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

        # 1) Duplicate checks
        if user_exists(uid):
            await msg.answer("⛔️ <b>Account Telegram នេះ</b> បានចុះឈ្មោះរួចហើយ។", parse_mode=ParseMode.HTML, reply_markup=main_kb)
            user_state.pop(uid, None); return
        if phone_exists(phone_e164):
            await msg.answer("⚠️ លេខទូរសព្ទនេះបានចុះឈ្មោះរួចហើយ។", parse_mode=ParseMode.HTML, reply_markup=main_kb)
            user_state.pop(uid, None); return

        # 2) Allow-lists (optional)
        if not is_user_allowed(uid):
            await msg.answer("⛔️ Account Telegram នេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។", reply_markup=main_kb)
            user_state.pop(uid, None); return
        if not is_phone_allowed(phone_e164):
            await msg.answer("⛔️ លេខទូរសព្ទនេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។", reply_markup=main_kb)
            user_state.pop(uid, None); return

        # 3) Save indices
        add_user(uid)
        add_phone(phone_e164)

        full_name = st.get("name", "")
        member_status = "NEW"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4) Send report to group
        report = (
            "🆕 <b>ការចុះឈ្មោះយកអាវយឺត</b>\n"
            f"📅 Date Time: <b>{ts}</b>\n"
            f"🆔 User ID: <code>{uid}</code>\n"
            f"👤 Full Name: <b>{full_name}</b>\n"
            f"📱 Phone: <b>{phone_e164}</b>\n"
            f"🎁 រង្វាន់: <b>{REWARD_LABEL}</b>\n"
            f"🟢 Member: <b>{member_status}</b>"
        )
        try:
            await bot.send_message(chat_id=int(GROUP_ID), text=report)
        except Exception as e:
            await msg.answer(f"⚠️ មិនអាចផ្ញើទៅ Group បាន: {e}")

        # 5) Confirm to user
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
