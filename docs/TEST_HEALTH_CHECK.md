# Health Check Command Testing Guide

This guide explains how to test the `/ac-agent health` command.

## Prerequisites

- Slack bot is running and connected
- Docker Compose services are up (api, slack-bot)
- You have access to DM with the bot

## Test Scenarios

### 1. Test Health Check - System Operational

**Setup:**
```bash
# Ensure bot service is running
docker compose up -d slack-bot
docker compose ps  # Verify healthy
```

**Action:**
1. Open DM with the bot in Slack or mention bot in a channel
2. Send `/ac-agent health` or `@Agent for AC health`

**Expected result:**
```
✅ *System Health Status*

✅ Service: `running`

_All systems operational._
```

**Verification:**
- Service shows "running"
- Green checkmark (✅) displayed
- Message indicates system is operational

---

### 2. Test Jira Connectivity (Optional)

The health check confirms the bot is running. To test Jira connectivity, try processing a ticket:

**Action:**
```
@Agent for AC https://yourcompany.atlassian.net/browse/PROJ-123
```

**Expected result:**
- If Jira is configured correctly: Bot reads the ticket and starts workflow
- If Jira has issues: Bot shows clear error message about connection or permissions

---

## Checking Logs

While testing, monitor the bot logs:

```bash
docker compose logs -f slack-bot
```

Expected log entries:
```json
{
  "event": "command_received",
  "user_id": "U1234567890",
  "command_text": "health",
  "channel_name": "directmessage"
}
{
  "event": "health_check_completed"
}
```

## Integration Testing

Test the health check in different contexts:

```bash
# 1. Start bot
docker compose up -d slack-bot

# 2. Wait for bot to connect
docker compose logs -f slack-bot
# Wait for "Connected to Slack via Socket Mode"

# 3. Test in DM:
/ac-agent health
# → Should show service running

# 4. Test in channel:
@Agent for AC health
# → Should show service running

# 5. Test in thread (after starting a workflow):
@Agent for AC health
# → Should work in thread context too
```

## Troubleshooting

### Bot shows as offline

**Check service status:**
```bash
docker compose ps
```

**Check bot logs:**
```bash
docker compose logs slack-bot
```

**Verify tokens:**
- Check `.env` has valid `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`
- Verify Socket Mode is enabled in Slack app settings

**Restart bot:**
```bash
docker compose restart slack-bot
```

### Bot doesn't respond to health command

**Verify command syntax:**
- Use `/ac-agent health` (lowercase) in DM
- Or use `@Agent for AC health` in channels

**Check bot is connected:**
```bash
docker compose logs slack-bot | grep "Connected to Slack"
```

**Try mentioning in channel:**
Sometimes @mentions work better than slash commands.

## Expected Behavior Summary

| Context | Command | Expected Response |
|---------|---------|-------------------|
| DM | `/ac-agent health` | ✅ Service: running |
| Channel | `@Agent for AC health` | ✅ Service: running |
| Thread | `@Agent for AC health` | ✅ Service: running |

**Note:** The bot uses stateless architecture, so it doesn't have database dependencies to check. The health command simply confirms the bot service is running and responsive.
