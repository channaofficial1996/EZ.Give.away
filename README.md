# LaLa Register Bot (Telegram)

Features:
- 📝 Registration flow (full name + phone)
- 📤 Sends result to a Telegram Group with fields:
  - Date Time
  - User ID
  - Full Name
  - Phone Number
  - Reward (រង្វាន់អាវ)
  - Member status (NEW / OLD)
- 🧾 Saves to Google Sheet (`Registrations`)
- 🔒 Anti-duplicate via both `UserIndex` (by Telegram account) and `PhoneIndex` (by phone)
- ✅ Optional allow-lists:
  - `AllowedUsers` (by Telegram user ID) → enabled with `ENFORCE_ALLOWED_USERS=1`
  - `AllowedPhones` (by phone) → enabled with `ENFORCE_ALLOWED_PHONES=1`

Auto-created worksheets:
- `Registrations` (Timestamp, TelegramUserID, FullName, PhoneE164, SourceButton, Username, FirstName, LastName, Reward, MemberStatus)
- `UserIndex` (TelegramUserID, FirstSeenAt, Count)
- `PhoneIndex` (PhoneE164, FirstSeenAt, Count)
- `AllowedUsers` (TelegramUserID) – optional
- `AllowedPhones` (PhoneE164) – optional

## Setup

1) Create a Google Service Account; share your Google Sheet with the `client_email` as **Editor**.
2) Create a Sheet and note its ID.
3) Create a bot via @BotFather and get BOT_TOKEN.
4) Fill `.env.example` (or Railway environment variables).

## Run Local

```bash
pip install -r requirements.txt
export BOT_TOKEN=...
export GROUP_ID=-100...
export SHEET_ID=...
export GSERVICE_JSON='{"type":"service_account", ... }'
# Optional strict modes:
export ENFORCE_ALLOWED_PHONES=0
export ENFORCE_ALLOWED_USERS=0
python main.py
```

## Deploy on Railway

- Upload or connect this repo
- Set variables in Railway Settings:
  - BOT_TOKEN, GROUP_ID, SHEET_ID, GSERVICE_JSON
  - ENFORCE_ALLOWED_PHONES (0/1), ENFORCE_ALLOWED_USERS (0/1)
  - REWARD_LABEL
- `Procfile` already set: worker runs `python main.py`.
