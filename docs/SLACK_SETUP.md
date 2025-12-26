# Slack Bot Setup Instructions

This guide explains how to create a Slack app and configure it for the Agent for AC bot.

## Prerequisites

- Admin access to a Slack workspace (or permission to install apps)
- Access to [Slack API Dashboard](https://api.slack.com/apps)

## Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter app name: **"Agent for AC"**
5. Select your workspace
6. Click **"Create App"**

## Step 2: Enable Socket Mode

1. In your app settings, go to **"Socket Mode"** in the left sidebar
2. Toggle **"Enable Socket Mode"** to ON
3. Enter a token name (e.g., "Socket Mode Token")
4. Click **"Generate"**
5. **Copy the App-Level Token** (starts with `xapp-`) - this is your `SLACK_APP_TOKEN`
6. Click **"Done"**

## Step 3: Configure OAuth & Permissions

1. Go to **"OAuth & Permissions"** in the left sidebar
2. Scroll down to **"Scopes"** → **"Bot Token Scopes"**
3. Add the following scopes:
   - `chat:write` - Send messages as the bot
   - `im:history` - View messages in direct messages
   - `im:read` - View basic information about direct messages
   - `im:write` - Start direct messages with people
   - `commands` - Add slash commands
   - `app_mentions:read` - Receive `@mention` events in channels and threads

## Step 4: Configure Event Subscriptions (for DMs and threads)

1. Go to **"Event Subscriptions"** in the left sidebar
2. Toggle **"Enable Events"** to ON
3. Under **"Subscribe to bot events"**, add:
   - `message.im` - Receive direct messages
   - `app_mention` - Receive `@Agent for AC ...` mentions in channels and threads

## Step 5: Install App to Workspace

1. Scroll to the top of the **"OAuth & Permissions"** page
2. Click **"Install to Workspace"**
3. Review the permissions and click **"Allow"**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`) - this is your `SLACK_BOT_TOKEN`

## Step 6: Configure Slash Commands (Optional for later)

1. Go to **"Slash Commands"** in the left sidebar
2. Click **"Create New Command"**
3. Enter command: `/ac-agent`
4. Request URL: Not needed for Socket Mode (enter any URL like `https://example.com`)
5. Short description: "Generate or evaluate acceptance criteria"
6. Click **"Save"**

## Step 6: Configure Environment Variables

1. Copy your tokens from steps 2 and 4
2. Update your `.env` file:

```bash
SLACK_BOT_TOKEN=xoxb-your-actual-token-here
SLACK_APP_TOKEN=xapp-your-actual-token-here
```

3. Keep these tokens secure and never commit them to version control!

## Step 8: Test the Connection

1. Start the services:
   ```bash
   docker compose up
   ```

2. Check the logs for:
   - `slack_bot_starting`
   - `slack_app_created`
   - `connecting_to_slack`
   - `slack_bot_connected` with message "Connected to Slack via Socket Mode"

3. In your Slack workspace, the bot should now appear online

## Troubleshooting

### Bot doesn't connect
- Verify both tokens are correct
- Check that Socket Mode is enabled
- Ensure the app is installed to your workspace

### "Token is invalid" error
- Make sure you're using the Bot User OAuth Token (xoxb-) for SLACK_BOT_TOKEN
- Make sure you're using the App-Level Token (xapp-) for SLACK_APP_TOKEN

### Permission errors
- Review the OAuth scopes in step 3
- Reinstall the app if you added new scopes

## Next Steps

Once the bot is connected, you can:
- Send direct messages to the bot
- Use the `/ac-agent` command (when implemented)
- Monitor logs for activity
