# Quick Start Guide

Get Agent for AC running in 5 minutes.

## Prerequisites Check

Before you start, verify you have:

```bash
# Check Docker is running
docker ps
# Should show: CONTAINER ID   IMAGE   ...

# Check Docker Compose is installed
docker compose version
# Should show: Docker Compose version v2.x.x

# Check you're in the project directory
pwd
# Should end with: /agent_for_ac
```

---

## Step 1: Environment Configuration (One-time setup)

Copy the example environment file and configure it:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

**Required environment variables:**

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Jira Configuration
JIRA_SITE_URL=https://yourcompany.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token-here

# LLM Configuration (choose one provider)
LLM_PROVIDER=anthropic  # or "bedrock"

# If using Anthropic:
ANTHROPIC_API_KEY=sk-ant-...

# If using AWS Bedrock:
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1

# Optional
SENTRY_DSN=
LOG_LEVEL=INFO
ENVIRONMENT=local
```

**Setup Guides:**
- **Slack Setup:** See [docs/SLACK_SETUP.md](docs/SLACK_SETUP.md)
- **Jira Setup:** See [docs/JIRA_SETUP.md](docs/JIRA_SETUP.md)

---

## Step 2: Start All Services

**Single command to start everything:**

```bash
docker compose up
```

**What this does:**
1. Starts FastAPI (health endpoints on port 8000)
2. Starts Slack Bot (connects to your workspace)

**Expected output:**
```
✔ Container agent_ac_api       Created
✔ Container agent_ac_slack_bot Created

agent_ac_api        | {"event": "slack_bot_starting", "environment": "local"}
agent_ac_api        | {"event": "jira_service_initialized"}
agent_ac_api        | {"event": "fastapi_started"}
agent_ac_api        | Uvicorn running on http://0.0.0.0:8000
agent_ac_slack_bot  | {"event": "slack_bot_starting", "environment": "local"}
agent_ac_slack_bot  | {"event": "jira_connected", "base_url": "https://..."}
agent_ac_slack_bot  | {"event": "slack_app_created"}
agent_ac_slack_bot  | {"event": "connecting_to_slack"}
agent_ac_slack_bot  | INFO:slack_bolt.AsyncApp:A new session (s_xxx) has been established
agent_ac_slack_bot  | INFO:slack_bolt.AsyncApp:⚡️ Bolt app is running!
```

✅ **When you see "⚡️ Bolt app is running!" the Slack bot is successfully connected**

**⏱️ First run:** May take 2-3 minutes (downloading images, installing packages)
**⏱️ Subsequent runs:** 10-20 seconds

---

## Step 3: Verify Everything is Running

### Check Service Status

**In a new terminal:**

```bash
docker compose ps
```

**Expected output:**
```
NAME                 STATUS
agent_ac_api         Up
agent_ac_slack_bot   Up
```

✅ All should show "Up" status

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status":"healthy","service":"agent-for-ac"}
```

### Test Slack Bot

1. Open your Slack workspace
2. Find "Agent for AC" bot (should show green dot = online)
3. **In a channel**, mention the bot:
   ```
   @Agent for AC health
   ```
4. You should receive a health status message

**Bot interaction modes:**
- **In DM:** Use `/ac-agent` slash command
- **In channels:** Mention the bot with `@Agent for AC`
- **In threads:** Bot automatically replies in the same thread

---

## Step 4: Try Generating Acceptance Criteria (Optional)

**Quick workflow example:**

1. **Start workflow** (in channel):
   ```
   @Agent for AC https://yourcompany.atlassian.net/browse/PROJ-123
   ```

2. **Choose format** when prompted:
   ```
   @Agent for AC checklist
   ```

3. **Answer questions** if bot needs more info:
   ```
   @Agent for AC Yes, it should support mobile devices
   ```

4. **Refine the generated AC** using natural language:
   ```
   @Agent for AC Make criterion #3 more specific about error handling
   @Agent for AC Add a criterion for accessibility
   @Agent for AC Convert to BDD format
   ```

5. **Approve when satisfied**:
   ```
   @Agent for AC approve
   ```

**Chat refinement commands:**
- Modify: "Make #3 more specific"
- Add: "Add error handling criterion"
- Remove: "Remove the last one"
- Change format: "Convert to BDD"
- Regenerate: "Regenerate focusing on edge cases"

---

## Step 5: Interactive API Documentation

Open in your browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test the endpoints directly from the Swagger UI.

---

## Common Commands

### Running in Background

```bash
# Start all services in detached mode
docker compose up -d

# Check logs
docker compose logs -f

# Check specific service logs
docker compose logs -f slack-bot
docker compose logs -f api
```

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (clean state)
docker compose down -v
```

### Restarting Services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart slack-bot
docker compose restart api
```

### Rebuilding After Code Changes

```bash
# Rebuild and restart
docker compose up --build

# Rebuild specific service
docker compose up --build api
```

---

## Testing the Application

### Run Test Scripts

```bash
# Test with a Jira ticket
uv run python test_with_jira_ticket.py

# Test AI orchestration
uv run python test_ai_orchestration.py

# Generate acceptance criteria
uv run python test_generate_ac.py
```

---

## Troubleshooting

### Issue: "Cannot connect to Docker daemon"

**Solution:**
```bash
# Start Docker Desktop (on Mac)
open -a Docker

# Wait for Docker to start, then try again
docker compose up
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or change the port in docker-compose.yml
# Then restart
docker compose down
docker compose up
```

### Issue: Slack bot shows "disconnected"

**Solution:**
1. Verify tokens in `.env` are valid
2. Check Slack app settings - Socket Mode should be enabled
3. Check logs: `docker compose logs slack-bot`
4. Look for error messages in logs
5. Restart the bot: `docker compose restart slack-bot`

### Issue: "uv: command not found"

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell
source ~/.zshrc  # or ~/.bashrc
```

### Issue: Changes not reflected

**Solution:**
```bash
# Code changes - rebuild
docker compose up --build

# Environment changes - restart
docker compose restart
```

---

## Development Workflow

### Making Code Changes

1. **Edit code** in `src/` directory
2. **Save the file** - changes are reflected immediately (hot reload)
3. **Check logs** to see if service reloaded
   ```bash
   docker compose logs -f api
   # or
   docker compose logs -f slack-bot
   ```

### Adding New Dependencies

```bash
# Add a new package
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Rebuild Docker images
docker compose up --build
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f slack-bot

# Last 50 lines
docker compose logs --tail 50 api

# Filter logs
docker compose logs slack-bot | grep error
```

---

## Daily Development Cycle

### Starting Your Day

```bash
# Start all services in background
docker compose up -d

# Verify everything is running
docker compose ps

# Check API is responding
curl http://localhost:8000/health
```

### During Development

```bash
# Monitor logs in one terminal
docker compose logs -f

# Make code changes in your editor
# Changes auto-reload (no restart needed)

# Run tests
uv run python test_with_jira_ticket.py
```

### Ending Your Day

```bash
# Stop services
docker compose down

# Or keep them running (minimal resource usage)
# Just close the terminal
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start all services | `docker compose up` |
| Start in background | `docker compose up -d` |
| Stop services | `docker compose down` |
| View logs | `docker compose logs -f` |
| Restart service | `docker compose restart slack-bot` |
| Rebuild | `docker compose up --build` |
| Clean restart | `docker compose down -v && docker compose up` |
| Check status | `docker compose ps` |
| Run tests | `uv run python test_with_jira_ticket.py` |

---

## Getting Help

**Documentation:**
- Main README: `README.md`
- Slack Setup: `docs/SLACK_SETUP.md`
- Jira Setup: `docs/JIRA_SETUP.md`
- Testing Guide: `docs/TESTING_GUIDE.md`

**Check Logs:**
```bash
docker compose logs -f
```

**Common Issues:**
- See "Troubleshooting" section above
- Check `docs/TEST_ERROR_HANDLING.md`

**Resources:**
- FastAPI docs: https://fastapi.tiangolo.com
- Slack Bolt: https://slack.dev/bolt-python
- Docker Compose: https://docs.docker.com/compose/

---

**🚀 You're ready to go! Run `docker compose up` and you're live!**
