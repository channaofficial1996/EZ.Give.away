# main.py  — LaLa (Group-only) FULL + Group Photo + Asia/Bangkok time
import os, json, asyncio, re, logging, signal
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from zoneinfo import ZoneInfo  # ★ timezone

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lala")

# ---------- ENV ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID  = os.getenv("GROUP_ID")                  # e.g. -1003027286018
REWARD_LABEL = os.getenv("REWARD_LABEL", "អាវយឺត")

# Agent contact (inline button/link)
AGENT_URL = os.getenv("AGENT_URL", "https://t.me/bestservicebj88")

# Admins allowed to use /groupid
ADMIN_IDS = set(u.strip() for u in os.getenv("ADMIN_IDS", "").split(",") if u.strip())

# Anti-dup + allow-lists
ENFORCE_ALLOWED_USERS  = os.getenv("ENFORCE_ALLOWED_USERS",  "0") == "1"
ENFORCE_ALLOWED_PHONES = os.getenv("ENFORCE_ALLOWED_PHONES", "0") == "1"
ALLOWED_USERS  = set(u.strip() for u in os.getenv("ALLOWED_USERS",  "").split(",") if u.strip())
ALLOWED_PHONES = set(p.strip() for p in os.getenv("ALLOWED_PHONES", "").split(",") if p.strip())

if not all([BOT_TOKEN, GROUP_ID]):
    raise RuntimeError("Missing one of: BOT_TOKEN / GROUP_ID")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ---------- Local store ----------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = DATA_DIR / "state.json"

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            log.exception("load_state failed")
    return {"phone_index": [], "user_index": []}

def save_state(state):
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        log.exception("save_state failed")

STATE = load_state()

def normalize_kh_phone(raw: str) -> str:
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
    return True if not ENFORCE_ALLOWED_USERS else (str(uid) in ALLOWED_USERS and len(ALLOWED_USERS) > 0)

def is_phone_allowed(phone_e164: str) -> bool:
    return True if not ENFORCE_ALLOWED_PHONES else (phone_e164 in ALLOWED_PHONES and len(ALLOWED_PHONES) > 0)

# ---------- UI ----------
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 ចុះឈ្មោះ"), KeyboardButton(text="👔 ទាក់ទងភ្នាក់ងារ")]],
    resize_keyboard=True
)
agent_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="👔 ទាក់ទងភ្នាក់ងារ", url=AGENT_URL)]]
)
user_state = {}  # uid -> {"step": "name"/"phone", "name": str}

# ---------- Commands ----------
@dp.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "សួស្ដី! នេះគឺ <b>LaLa Bot</b> (Group-only) សម្រាប់ចុះឈ្មោះយកអាវយឺត 👕\n"
        "សូមជ្រើសរើសពីម៉ឺនុយខាងក្រោម។",
        reply_markup=main_kb
    )

@dp.message(F.text == "/myid")
async def myid_cmd(msg: Message):
    await msg.answer(f"🆔 Your Telegram User ID: <code>{msg.from_user.id}</code>")

@dp.message(F.text == "/groupid")
async def groupid_cmd(msg: Message):
    if ADMIN_IDS and str(msg.from_user.id) not in ADMIN_IDS:
        await msg.answer("⛔️ Only admins can use /groupid"); return
    await msg.answer(f"💬 This chat id: <code>{msg.chat.id}</code>")

@dp.message(F.text == "👔 ទាក់ទងភ្នាក់ងារ")
async def contact_agent(msg: Message):
    await msg.answer("👔 ចុចប៊ូតុងខាងក្រោមដើម្បីទាក់ទងភ្នាក់ងារ:", reply_markup=agent_inline_kb)

@dp.message(F.text == "📝 ចុះឈ្មោះ")
async def register_start(msg: Message):
    uid = msg.from_user.id
    user_state[uid] = {"step": "name"}
    await msg.answer("សូមបញ្ចូល <b>ឈ្មោះពេញ</b> របស់អ្នក 🧍:")

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
            await msg.answer("ឈ្មោះមិនត្រឹមត្រូវ 😅 សូមវាយឡើងវិញ។"); return
        st["name"] = name
        st["step"] = "phone"
        await msg.answer("✅ បានទទួលឈ្មោះ!\nឥឡូវសូមវាយ <b>លេខទូរសព្ទ</b> 📱:")
        return

    if step == "phone":
        try:
            raw = (msg.text or "").strip()
            log.info(f"[phone] raw={raw!r} uid={uid}")
            raw_digits = re.sub(r"[^\d+]", "", raw)
            if len(re.sub(r"[^\d]", "", raw_digits)) < 8:
                await msg.answer("លេខទូរសព្ទមិនត្រឹមត្រូវ ☎️ សូមវាយឡើងវិញ (យ៉ាងហោចណាស់ 8 តួលេខ)។")
                return

            phone_e164 = normalize_kh_phone(raw)
            log.info(f"[phone] normalized={phone_e164} uid={uid}")

            # duplicate checks
            if user_exists(uid):
                await msg.answer("⛔️ <b>Account Telegram នេះ</b> បានចុះឈ្មោះរួចហើយ។", reply_markup=main_kb)
                user_state.pop(uid, None); return
            if phone_exists(phone_e164):
                await msg.answer("⚠️ លេខទូរសព្ទនេះបានចុះឈ្មោះរួចហើយ។", reply_markup=main_kb)
                user_state.pop(uid, None); return

            # allow-lists
            if not is_user_allowed(uid):
                await msg.answer("⛔️ Account Telegram នេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។", reply_markup=main_kb)
                user_state.pop(uid, None); return
            if not is_phone_allowed(phone_e164):
                await msg.answer("⛔️ លេខទូរសព្ទនេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។", reply_markup=main_kb)
                user_state.pop(uid, None); return

            # save indices
            add_user(uid); add_phone(phone_e164)

            full_name = st.get("name", "")
            username = f"@{msg.from_user.username}" if msg.from_user and msg.from_user.username else "(no username)"
            member_status = "NEW"
            ts = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")  # ★ UTC+7

            # group report (try photo first; fallback to text)
            report = (
                "🆕 <b>ការចុះឈ្មោះយកអាវយឺត</b>\n"
                f"📅 Date Time (UTC+7): <b>{ts}</b>\n"
                f"🆔 User ID: <code>{uid}</code>\n"
                f"🔗 Username: <b>{username}</b>\n"
                f"👤 Full Name: <b>{full_name}</b>\n"
                f"📱 Phone: <b>{phone_e164}</b>\n"
                f"🎁 រង្វាន់: <b>{REWARD_LABEL}</b>\n"
                f"🟢 Member: <b>{member_status}</b>"
            )
            try:
                voucher_path = DATA_DIR / "voucher.jpg"   # រូបអាវសម្រាប់ group
                if voucher_path.exists():
                    await bot.send_photo(
                        chat_id=int(GROUP_ID),
                        photo=FSInputFile(voucher_path),
                        caption=report
                    )
                    log.info(f"[group] photo+caption sent to {GROUP_ID}")
                else:
                    await bot.send_message(chat_id=int(GROUP_ID), text=report)
                    log.info(f"[group] text report sent to {GROUP_ID} (no voucher.jpg)")
            except Exception as e:
                log.error(f"[group] send failed: {e}")
                await msg.answer(f"⚠️ ព័ត៌មាន: មិនអាចផ្ញើទៅ Group បាន ({e})។")

            # congratulation + voucher (DM to user)
            confirm_text = (
                "🎉 <b>អបអរសាទរ!</b>\n"
                "បងទទួលបាន <b>អាវយឺត ១</b> 👕\n"
                "សូមបង្ហាញ <b>រូបភាពនេះ</b> ទៅក្រុមការងារ ដើម្បីទទួលអាវ។\n\n"
                f"🔗 Username: <b>{username}</b>\n"
                f"👤 ឈ្មោះ: <b>{full_name}</b>\n"
                f"📱 លេខ: <b>{phone_e164}</b>\n"
                f"🎁 រង្វាន់: <b>{REWARD_LABEL}</b>"
            )
            try:
                user_voucher = DATA_DIR / "voucher.jpg"
                if user_voucher.exists():
                    await bot.send_photo(chat_id=msg.chat.id, photo=FSInputFile(user_voucher), caption=confirm_text)
                else:
                    await msg.answer(confirm_text, reply_markup=main_kb)
            except Exception:
                await msg.answer(confirm_text, reply_markup=main_kb)

            user_state.pop(uid, None)
            return

        except Exception as e:
            log.exception(f"[phone] unexpected error: {e}")
            await msg.answer("⚠️ មានកំហុសមួយកើតឡើង សូមវាយលេខទូរសព្ទម្តងទៀត។")
            return

async def main():
    print("🚀 LaLa bot (group-only) running — anti-dup by user & phone")
    try:
        # Test bot connection
        me = await bot.get_me()
        log.info(f"✅ Bot connected: @{me.username} (ID: {me.id})")
    except Exception as e:
        log.error(f"❌ Failed to connect to Telegram: {e}")
        raise

    # Setup graceful shutdown
    loop = asyncio.get_event_loop()
    
    def handle_signal(signum, frame):
        log.info(f"📍 Signal {signum} received - initiating graceful shutdown...")
        # Request dispatcher shutdown
        asyncio.create_task(dp.feed_update(None))
    
    # Register signal handlers for graceful shutdown
    loop.add_signal_handler(signal.SIGTERM, handle_signal, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, handle_signal, signal.SIGINT, None)
    
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        log.info("📍 Polling cancelled")
    finally:
        log.info("🛑 Shutting down bot...")
        save_state(STATE)  # Save state on shutdown
        await bot.session.close()
        log.info("✅ Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("⚠️ Bot interrupted by user")
