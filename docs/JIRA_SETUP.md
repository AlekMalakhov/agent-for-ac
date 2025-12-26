# Jira Integration Setup Guide

This guide explains how to set up the Jira integration for Agent for AC using Atlassian's official Remote MCP Server.

## Overview

Agent for AC integrates with Jira Cloud using the **Atlassian Remote MCP Server**, which provides:
- OAuth 2.1 authentication
- Secure, managed connection to your Jira instance
- Full read/write access to Jira issues
- Automatic permission management

## Prerequisites

- **Jira Cloud** account and site (e.g., `https://yourcompany.atlassian.net`)
- **Atlassian admin access** to create OAuth credentials
- **Node.js v18+** installed (required by the MCP server)

## Step 1: Create OAuth Credentials

1. Go to your Atlassian Developer Console: https://developer.atlassian.com/console/myapps/
2. Click **Create** → **OAuth 2.0 integration**
3. Fill in the app details:
   - **App name**: "Agent for AC"
   - **Description**: "Slack bot for generating acceptance criteria"
   - **App type**: "Server-side application"
4. Click **Create**
5. Note down your **Client ID** and **Client Secret** (you'll need these later)

## Step 2: Configure OAuth Scopes

Your OAuth app needs the following Jira scopes:

### Required Scopes:
- `read:jira-work` - Read Jira issues
- `write:jira-work` - Update Jira issues
- `read:jira-user` - Read user information

### Steps:
1. In your OAuth app settings, go to **Permissions**
2. Click **Add** → **Jira API**
3. Select the required scopes listed above
4. Click **Save changes**

## Step 3: Configure Redirect URLs

1. In your OAuth app settings, go to **Authorization**
2. Add the following redirect URL:
   ```
   http://localhost:3000/oauth/callback
   ```
3. For production deployments, add your production callback URL

## Step 4: Configure Environment Variables

Add the following variables to your `.env` file:

```bash
# Atlassian MCP Server Configuration
JIRA_SITE_URL=https://yourcompany.atlassian.net
JIRA_OAUTH_CLIENT_ID=your-oauth-client-id-here
JIRA_OAUTH_CLIENT_SECRET=your-oauth-client-secret-here
```

Replace:
- `yourcompany` with your Jira Cloud site name
- `your-oauth-client-id-here` with your OAuth Client ID from Step 1
- `your-oauth-client-secret-here` with your OAuth Client Secret from Step 1

## Step 5: Install Node.js Dependencies

The MCP server requires Node.js to run. Install the required package:

```bash
npm install -g @modelcontextprotocol/server-atlassian
```

Or using npx (no installation required):
```bash
# The MCP client will automatically use npx
```

## Step 6: Test the Connection

Start the application and check the logs for successful Jira service initialization:

```bash
docker compose up
```

Look for this log message:
```
jira_service_initialized
```

If you see an error, check:
- Your OAuth credentials are correct
- Your Jira site URL is correct
- Node.js v18+ is installed
- The MCP server package is accessible

## Usage

Once configured, users can interact with Jira from Slack:

```
/ac-agent PROJ-123
```

or

```
/ac-agent https://yourcompany.atlassian.net/browse/PROJ-123
```

The bot will:
1. Read the Jira ticket
2. Detect existing acceptance criteria
3. Generate new/improved AC
4. Write the AC back to the ticket
5. Provide feedback in Slack

## Supported Ticket Types

Agent for AC only supports:
- **Story** tickets
- **Task** tickets

Epics, Bugs, Sub-tasks, and other ticket types are not supported.

## Permissions

The bot respects Jira permissions:
- Users must have **view** permission to read tickets
- Users must have **edit** permission to update tickets
- Permission errors are reported clearly in Slack

## Troubleshooting

### "MCP server not connected" error
- **Cause**: OAuth credentials are invalid or MCP server failed to start
- **Solution**:
  - Verify your OAuth Client ID and Client Secret
  - Check that Node.js v18+ is installed
  - Review application logs for detailed error messages

### "Permission denied" error
- **Cause**: User lacks Jira permissions for the ticket
- **Solution**:
  - Verify the user has view/edit access to the ticket in Jira
  - Check project permissions in Jira admin settings

### "Ticket not found" error
- **Cause**: Ticket key is invalid or ticket was deleted
- **Solution**:
  - Verify the ticket key is correct
  - Check that the ticket exists in Jira

### "Unsupported ticket type" error
- **Cause**: Ticket is not a Story or Task
- **Solution**:
  - Only use the bot with Story and Task tickets
  - Convert the ticket type in Jira if needed

## Rate Limits

Atlassian's MCP server has rate limits:
- **Standard plan**: Moderate usage thresholds
- **Premium/Enterprise**: 1,000 requests/hour + per-user limits

If you hit rate limits, the bot will show an error message with guidance to wait before retrying.

## Security Considerations

- OAuth credentials are stored as **environment variables** (never in code)
- All tokens are handled as **SecretStr** (not logged)
- The MCP server uses **OAuth 2.1** (industry standard)
- Connections are encrypted via **HTTPS**
- Permission checks happen on **every request**

## Further Reading

- [Atlassian Remote MCP Server Documentation](https://www.atlassian.com/blog/announcements/remote-mcp-server)
- [OAuth 2.0 for Atlassian Apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Jira Cloud REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
