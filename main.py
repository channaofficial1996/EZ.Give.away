import os, json, asyncio, re
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

import gspread
from google.oauth2.service_account import Credentials

# ========== ENV ==========
BOT_TOKEN = os.getenv("8145331081:AAEg_ru70no470k29WLiKUvtcOXwQRrifdY")
GROUP_ID = os.getenv("-1003027286018")          # e.g. -1001234567890
SHEET_ID = os.getenv("1Bo20Yfb4mmuwrskqJv1mDwIiS6dem0SpekoQRqois9I")          # Google Sheet ID
GSERVICE_JSON = os.getenv("GSERVICE_JSON")# Entire service account JSON as a single-line string

# Phone allow enforcement (only phones present in AllowedPhones may register)
ENFORCE_ALLOWED_PHONES = os.getenv("ENFORCE_ALLOWED_PHONES", "0") == "1"
# User allow enforcement (only Telegram user IDs present in AllowedUsers may register)
ENFORCE_ALLOWED_USERS = os.getenv("ENFORCE_ALLOWED_USERS", "0") == "1"

# Khmer label for reward (shirt)
REWARD_LABEL = os.getenv("REWARD_LABEL", "អាវយឺត")

if not all([BOT_TOKEN, GROUP_ID, SHEET_ID, GSERVICE_JSON]):
    raise RuntimeError("Missing one of: BOT_TOKEN / GROUP_ID / SHEET_ID / GSERVICE_JSON")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ========== Google Sheets helpers ==========
def gclient():
    info = json.loads(GSERVICE_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def open_sheet():
    gc = gclient()
    sh = gc.open_by_key(SHEET_ID)

    def ensure_ws(title, header):
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=3000, cols=12)
            if header:
                ws.append_row(header)
        return ws

    # Data worksheets
    ws_reg = ensure_ws("Registrations",
        ["Timestamp","TelegramUserID","FullName","PhoneE164","SourceButton","Username","FirstName","LastName","Reward","MemberStatus"])
    ws_phone_idx = ensure_ws("PhoneIndex",
        ["PhoneE164","FirstSeenAt","Count"])
    ws_user_idx = ensure_ws("UserIndex",
        ["TelegramUserID","FirstSeenAt","Count"])
    ws_allow_phone = ensure_ws("AllowedPhones",
        ["PhoneE164"])        # optional
    ws_allow_user = ensure_ws("AllowedUsers",
        ["TelegramUserID"])    # optional
    return sh, ws_reg, ws_phone_idx, ws_user_idx, ws_allow_phone, ws_allow_user

def normalize_kh_phone(raw: str) -> str:
    """Normalize to E.164 KH (+855...). Accepts +855, leading 0, or plain digits."""
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

# ---- Index helpers ----
def value_in_col(ws, idx_zero_based=0):
    try:
        col = ws.col_values(idx_zero_based + 1)
    except Exception:
        return set()
    return set(v.strip() for v in col[1:])  # skip header

def phone_exists_in_index(phone_e164: str) -> bool:
    _, _, ws_phone_idx, _, _, _ = open_sheet()
    return phone_e164 in value_in_col(ws_phone_idx, 0)

def user_exists_in_index(user_id: int) -> bool:
    _, _, _, ws_user_idx, _, _ = open_sheet()
    return str(user_id) in value_in_col(ws_user_idx, 0)

def bump_index(ws, key: str, count_col: int):
    col_vals = [c.strip() for c in ws.col_values(1)]
    if key in col_vals:
        row = col_vals.index(key) + 1
        try:
            current = int(ws.cell(row, count_col).value or "1")
        except:
            current = 1
        ws.update_cell(row, count_col, current + 1)
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # For phone index: [PhoneE164, FirstSeenAt, Count]
        # For user index:  [TelegramUserID, FirstSeenAt, Count]
        ws.append_row([key, now, 1])

def is_phone_allowed(phone_e164: str) -> bool:
    _, _, _, _, ws_allow_phone, _ = open_sheet()
    if not ENFORCE_ALLOWED_PHONES:
        return True
    allowed = value_in_col(ws_allow_phone, 0)
    if len(allowed) == 0:
        return False  # strict when enforcement is enabled
    return phone_e164 in allowed

def is_user_allowed(user_id: int) -> bool:
    _, _, _, _, _, ws_allow_user = open_sheet()
    if not ENFORCE_ALLOWED_USERS:
        return True
    allowed = value_in_col(ws_allow_user, 0)
    if len(allowed) == 0:
        return False  # strict when enforcement is enabled
    return str(user_id) in allowed

def append_registration_row(full_name: str, phone_e164: str, src: str, msg: Message, reward: str, member_status: str):
    _, ws_reg, _, _, _, _ = open_sheet()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uid = msg.from_user.id if msg.from_user else ""
    username = f"@{msg.from_user.username}" if msg.from_user and msg.from_user.username else ""
    first_name = msg.from_user.first_name if msg.from_user and msg.from_user.first_name else ""
    last_name = msg.from_user.last_name if msg.from_user and msg.from_user.last_name else ""
    ws_reg.append_row([ts, uid, full_name, phone_e164, src, username, first_name, last_name, reward, member_status])

# ========== UI & State ==========
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 ចុះឈ្មោះ"), KeyboardButton(text="👔 ទាក់ទងភ្នាក់ងារ")]],
    resize_keyboard=True
)
user_state = {}  # uid -> {"step": "name"/"phone", "src": "Register", "name": str}

@dp.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "សួស្ដី! នេះគឺ <b>LaLa Bot</b> សម្រាប់ចុះឈ្មោះយកអាវយឺត 👕\n"
        "សូមជ្រើសរើសពីម៉ឺនុយខាងក្រោម។",
        reply_markup=main_kb
    )

@dp.message(F.text == "👔 ទាក់ទងភ្នាក់ងារ")
async def contact_agent(msg: Message):
    await msg.answer(
        "👔 ទាក់ទងភ្នាក់ងារ:\n"
        "• Agent A: @your_agent | +855 xx xxx xxx\n"
        "• អាចកំណត់តាម ENV: AGENTS (បន្ថែមបានបន្តិចក្រោយ)"
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

        # 🔐 First, reject if this Telegram user already registered
        if user_exists_in_index(uid):
            await msg.answer(
                "⛔️ យើងរកឃើញថា <b>Account Telegram នេះ</b> បានចុះឈ្មោះរួចហើយ។\n"
                "មិនអាចទទួលបានអាវម្តងទៀតបានទេ។",
                parse_mode=ParseMode.HTML,
                reply_markup=main_kb
            )
            user_state.pop(uid, None)
            return

        # 🔏 Enforce allowed lists (optional)
        if not is_user_allowed(uid):
            await msg.answer(
                "⛔️ Account Telegram នេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។\n"
                "សូមទាក់ទងភ្នាក់ងារ ឬរង់ចាំអោយបន្ថែមចូលបញ្ជីមុននឹងចុះឈ្មោះវិញ។",
                reply_markup=main_kb
            )
            user_state.pop(uid, None)
            return

        if not is_phone_allowed(phone_e164):
            await msg.answer(
                "⛔️ លេខទូរសព្ទនេះមិនមានក្នុងបញ្ជីអនុញ្ញាតទេ។\n"
                "សូមទាក់ទងភ្នាក់ងារ ឬរង់ចាំអោយបន្ថែមចូលបញ្ជីមុននឹងចុះឈ្មោះវិញ។",
                reply_markup=main_kb
            )
            user_state.pop(uid, None)
            return

        # 🔁 Also block if phone already registered (extra protection)
        if phone_exists_in_index(phone_e164):
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

        # Save to sheet
        member_status = "NEW"  # Since both user & phone are new by this point
        try:
            append_registration_row(full_name, phone_e164, src, msg, REWARD_LABEL, member_status)
        except Exception as e:
            await msg.answer(f"⚠️ មិនអាចកត់ត្រាទៅ Sheet បានទេ: {e}")

        # Insert into indices
        try:
            _, _, ws_phone_idx, ws_user_idx, _, _ = open_sheet()
            # phone index
            bump_index(ws_phone_idx, phone_e164, 3)
            # user index
            bump_index(ws_user_idx, str(uid), 3)
        except Exception:
            pass

        # Notify group (with requested fields)
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

        # Confirm to user
        await msg.answer(
            "🎉 <b>បញ្ចប់ការចុះឈ្មោះ</b>\n\n"
            f"👤 ឈ្មោះ: <b>{full_name}</b>\n"
            f"📱 លេខ: <b>{phone_e164}</b>\n"
            f"🎁 រង្វាន់: <b>{REWARD_LABEL}</b>\n"
            "🧾 បានកត់ត្រាទៅ Google Sheet ហើយ!\n",
            parse_mode=ParseMode.HTML,
            reply_markup=main_kb
        )

        user_state.pop(uid, None)
        return

async def main():
    print("🚀 LaLa bot running (register + group + sheets + anti-dup by user & phone + allow-lists)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
