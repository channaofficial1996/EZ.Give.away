# Railway Deployment Guide

## Prerequisites
- A Telegram bot token from BotFather
- Your Telegram group ID
- A Railway account (railway.app)

## Step 1: Get Your Credentials

### Telegram Bot Token
1. Open Telegram and search for "@BotFather"
2. Send `/newbot` command
3. Follow the prompts to create a new bot
4. Copy the token (format: `123456789:ABCDEfghijklmnop...`)
5. **IMPORTANT**: Do NOT share this token publicly

### Group ID
1. Add the bot to your Telegram group
2. Send the `/groupid` command in the group
3. The bot will reply with your group's ID (should be negative, like `-1003027286018`)

## Step 2: Deploy on Railway

### Option A: Connect via GitHub
1. Push your code to GitHub
2. Go to [railway.app](https://railway.app)
3. Create a new project
4. Select "Deploy from GitHub repo"
5. Choose your repository
6. Click "Deploy"
7. Go to Variables tab and add environment variables (see below)

### Option B: Deploy from CLI
1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. In your project folder: `railway link` (create new project)
4. Deploy: `railway up`
5. Set variables: `railway variables`

## Step 3: Set Environment Variables

In Railway Dashboard:
1. Go to your project → Variables tab
2. Click "Add Variable"
3. Add these required variables:
   - **BOT_TOKEN**: Your bot token from BotFather
   - **GROUP_ID**: Your group's ID (negative number)

4. (Optional) Add these variables:
   - **REWARD_LABEL**: Default is "អាវយឺត" (Khmer T-shirt)
   - **AGENT_URL**: URL to contact agent (default: https://t.me/bestservicebj88)
   - **ADMIN_IDS**: Comma-separated admin user IDs
   - **ENFORCE_ALLOWED_USERS**: Set to "1" to restrict to specific users
   - **ALLOWED_USERS**: Comma-separated user IDs to allow
   - **ENFORCE_ALLOWED_PHONES**: Set to "1" to restrict to specific phone numbers
   - **ALLOWED_PHONES**: Comma-separated phone numbers in E.164 format

## Step 4: Monitor Your Bot

1. In Railway Dashboard, go to Logs tab to see real-time output
2. Test the bot by sending `/start` in Telegram
3. Verify registrations appear in your group

## Troubleshooting

### Bot doesn't respond
- Check that BOT_TOKEN is correct (no spaces)
- Ensure the bot was added to the group
- Check Railway logs for errors

### Group doesn't receive messages
- Verify GROUP_ID is correct and negative
- Make sure bot has permission to post in the group
- Check that the group is set up correctly

### Registration data not persisting
- Railway containers can restart - data is stored in `data/state.json`
- After restart, the bot will have an empty user list
- Consider using Railway Volumes for persistent storage (optional)

## Advanced: Add Persistent Storage

If you want to keep registration data between restarts:
1. In Railway, go to your service
2. Click "Data" tab
3. Create a new volume
4. Mount it to `/app/data`
5. This ensures data persists across restarts

## Support

For issues:
1. Check Railway logs for error messages
2. Verify all environment variables are set
3. Test locally first: `python main.py` with `.env` file
4. Check Telegram API status at https://telegram.org
