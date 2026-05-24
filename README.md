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
1. Connect your GitHub repo or upload this folder to Railway
2. Go to your Railway project → Variables tab
3. Add environment variables:
   - `BOT_TOKEN` - Your Telegram bot token from BotFather
   - `GROUP_ID` - Your group chat ID (negative number, e.g., -1003027286018)
   - (Optional) `REWARD_LABEL` - Label for the reward (default: "អាវយឺត")
   - (Optional) `AGENT_URL` - Agent contact link
   - (Optional) `ENFORCE_ALLOWED_USERS`, `ALLOWED_USERS`, etc.
4. Railway will automatically detect the Procfile and deploy
5. View logs: Railway Dashboard → Your Service → Logs

Troubleshooting
- **Bot not responding**: Check that BOT_TOKEN and GROUP_ID are set correctly
- **Registration not saved**: Ensure `/data` directory has write permissions
- **Group not receiving reports**: Verify GROUP_ID format (must be negative for groups)
