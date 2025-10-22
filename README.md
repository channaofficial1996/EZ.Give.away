# LaLa Register Bot — Group-only Edition

✅ No Google Sheets. The bot only **sends reports to the group** and stores anti-duplicate data locally in `data/state.json`.

Features
- 📝 Registration: ask Full Name + Phone
- 📤 Sends report to Telegram Group with:
  - Date Time, User ID, Full Name, Phone, Reward label, Member status (NEW)
- 🔒 Anti-duplicate:
  - by Telegram **User ID**
  - by **Phone** (normalized to +855... when possible)
- ✅ Optional allow-lists via ENV:
  - `ENFORCE_ALLOWED_USERS=1` with `ALLOWED_USERS=123,456`
  - `ENFORCE_ALLOWED_PHONES=1` with `ALLOWED_PHONES=+855123...`

Run locally
```bash
pip install -r requirements.txt
export BOT_TOKEN=...
export GROUP_ID=-100...
python main.py
```

Deploy on Railway
- Upload this folder or connect a repo
- Set env: BOT_TOKEN, GROUP_ID (+ optional ENFORCE/ALLOWED vars)
- Procfile is provided (worker).
