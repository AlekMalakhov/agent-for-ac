# Slack Command Testing Guide

This guide explains how to test the `/ac-agent` slash command.

## Prerequisites

- Slack bot is running and connected (see `SLACK_SETUP.md`)
- You have access to the Slack workspace where the bot is installed
- The bot appears online in Slack

## Test Scenarios

### 1. Test Slash Command Context (DM vs channel)

**Action:** Send `/ac-agent` in a public channel (not a DM), in the main message box (not in a thread).

**Expected result:**
```
Slack does not support running slash commands inside threads. Please use `/ac-agent` in a direct message with me, or mention this app in a channel or thread (for example: `@Agent for AC health`).
```

**Verification:**
- User sees a clear explanation that:
  - Slash‑команда должна использоваться в DM или основном инпуте канала
  - В тредах нужно использовать `@упоминание` (`@Agent for AC ...`)

---

### 2. Test Welcome Message (Empty Command in DM)

**Action:**
1. Open a direct message with the bot
2. Send `/ac-agent` (with no text after it)

**Expected result:**
```
👋 Hello! I'm the Agent for AC bot.

I can help you generate and evaluate acceptance criteria for Jira tickets.

*Available commands:*
• `/ac-agent health` - Check system health
• `/ac-agent <jira-link>` - Generate or evaluate acceptance criteria (coming soon)

Try sending me a command!
```

**Verification:**
- User receives friendly welcome message
- Available commands are listed
- Message is properly formatted with Slack markdown

---

### 3. Test Health Check via Slash Command (DM)

**Action:**
1. In a direct message with the bot, send:
   ```
   /ac-agent health
   ```

**Expected result:**
```
✅ *System Health Status*

✅ Service: `running`

_All systems operational._
```

**Verification:**
- The response matches the documentation in `README.md`
- Slack markdown formatting is correct

---

### 4. Test Health Check via @Mention in Channel/Thread

**Action:**
1. In any channel, either in a new message or in a thread, send:
   - `@Agent for AC health`

**Expected result:**
- The bot replies with the same health status message as for `/ac-agent health`
- If the command was sent in a thread, the bot's response appears **in the same thread**

**Verification:**
- The reply comes from the bot user
- The logs contain an `app_mention_received` event

---

## Checking Logs

While testing, monitor the bot logs:

```bash
docker compose logs -f slack-bot
```

You should see log entries like:
```json
{
  "event": "command_received",
  "user_id": "U1234567890",
  "command_text": "test command",
  "channel_name": "directmessage",
  "timestamp": "2024-01-15T10:30:45.123456Z"
}
```

## Troubleshooting

### Command doesn't respond
- Check that the bot is running: `docker compose ps`
- Check bot logs: `docker compose logs slack-bot`
- Verify the bot appears online in Slack
- Check that Socket Mode is enabled in Slack app settings

### "Dispatch failed" error
- Ensure the command is registered in Slack app settings
- The command name should be `/ac-agent`
- Restart the bot: `docker compose restart slack-bot`

### Command works differently in DM vs thread
- Slash‑команда `/ac-agent` корректно работает в DM (и в основном инпуте канала)
- В тредах стоит использовать `@Agent for AC ...` вместо `/ac-agent`

## Next Steps

After verifying these tests pass, the next slice will implement:
- Health check command (`/ac-agent health`)
- Integration with the health check service
- More sophisticated command parsing
