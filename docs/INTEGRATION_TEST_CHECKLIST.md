# Integration Test Checklist

Complete end-to-end testing checklist for Agent for AC. Run through this checklist before considering the system production-ready.

## Pre-Test Setup

- [ ] Docker and Docker Compose installed
- [ ] uv installed and configured
- [ ] `.env` file created with valid tokens
- [ ] Slack app created and configured (see SLACK_SETUP.md)
- [ ] Clean state: `docker compose down -v`

## 1. Fresh Installation Test

### 1.1 Initial Setup

```bash
# Start from clean state
docker compose down -v
rm -rf .venv/

# Install dependencies
uv sync
```

**Verification:**
- [ ] Dependencies installed without errors
- [ ] `uv.lock` file created
- [ ] `.venv/` directory created

### 1.2 Configuration Validation

```bash
uv run python test_config_validation.py
```

**Verification:**
- [ ] All 4 tests pass
- [ ] Validation errors caught for missing variables
- [ ] Valid configuration loads successfully

### 1.3 First Docker Start

```bash
docker compose up --build
```

**Verification:**
- [ ] All images build successfully
- [ ] postgres service starts and becomes healthy
- [ ] redis service starts and becomes healthy
- [ ] api service starts after dependencies
- [ ] slack-bot service starts after dependencies
- [ ] No error messages in logs

## 2. Database & Cache Tests

### 2.1 Connection Test

```bash
# In another terminal
uv run python test_connections.py
```

**Verification:**
- [ ] Database connection: connected
- [ ] Redis connection: connected
- [ ] No errors in output
- [ ] Proper cleanup logged

### 2.2 Connection Error Handling

```bash
uv run python test_connection_errors.py
```

**Verification:**
- [ ] Invalid PostgreSQL connection raises error
- [ ] Invalid Redis connection raises error
- [ ] Valid connections work
- [ ] All 3 tests pass

### 2.3 Database Persistence

```bash
# Stop services
docker compose down

# Start again (without -v to keep volumes)
docker compose up -d

# Check PostgreSQL
docker compose exec postgres psql -U agent_ac -d agent_ac_db -c "\dt"
```

**Verification:**
- [ ] Database preserves data between restarts
- [ ] Tables exist
- [ ] No connection errors

## 3. API Endpoint Tests

### 3.1 Health Endpoint

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status":"healthy","service":"agent-for-ac"}
```

**Verification:**
- [ ] Returns HTTP 200
- [ ] Response matches expected format
- [ ] Response time < 100ms

### 3.2 Readiness Endpoint (All Healthy)

```bash
curl http://localhost:8000/readiness
```

**Expected Response:**
```json
{"status":"ready","postgres":"connected","redis":"connected"}
```

**Verification:**
- [ ] Returns HTTP 200
- [ ] Both services show "connected"
- [ ] status is "ready"

### 3.3 Readiness Endpoint (Database Down)

```bash
# Stop PostgreSQL
docker compose stop postgres

# Test readiness
curl -v http://localhost:8000/readiness

# Restart PostgreSQL
docker compose start postgres
```

**Verification:**
- [ ] Returns HTTP 503
- [ ] postgres shows "disconnected"
- [ ] redis shows "connected"
- [ ] status is "not_ready"

### 3.4 API Documentation

**Visit in browser:**
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

**Verification:**
- [ ] Swagger UI loads correctly
- [ ] All endpoints visible (/health, /readiness)
- [ ] Can execute requests from Swagger UI
- [ ] ReDoc documentation renders correctly

### 3.5 API Test Script

```bash
uv run python test_api.py
```

**Verification:**
- [ ] Health endpoint test passes
- [ ] Readiness endpoint test passes
- [ ] No errors in output

## 4. Slack Bot Tests

### 4.1 Bot Connection

**Check logs:**
```bash
docker compose logs slack-bot | grep connected
```

**Expected:**
- `slack_bot_connected` with message "Connected to Slack via Socket Mode"

**In Slack workspace:**

**Verification:**
- [ ] Bot appears in app list
- [ ] Bot shows as "Active" (green dot)
- [ ] Can open DM with bot

### 4.2 Welcome Command

**In Slack DM with bot:**
```
/ac-agent
```

**Expected Response:**
```
👋 Hello! I'm the Agent for AC bot.

I can help you generate and evaluate acceptance criteria for Jira tickets.

*Available commands:*
• `/ac-agent health` - Check system health
• `/ac-agent <jira-link>` - Generate or evaluate acceptance criteria (coming soon)

Try sending me a command!
```

**Verification:**
- [ ] Response received within 2 seconds
- [ ] Message formatted correctly
- [ ] Emoji displays
- [ ] Commands listed with bullet points

### 4.3 DM-Only Enforcement

**In a public channel (not DM):**
```
/ac-agent
```

**Expected Response:**
```
Please use this command in a direct message with me.
```

**Verification:**
- [ ] Bot rejects command in channels
- [ ] User informed to use DMs
- [ ] No error in logs

### 4.4 Health Check Command (All Healthy)

**In Slack DM:**
```
/ac-agent health
```

**Expected Response:**
```
✅ *System Health Status*

✅ PostgreSQL: `connected`
✅ Redis: `connected`

_All systems operational._
```

**Verification:**
- [ ] Response shows all services connected
- [ ] Green checkmarks display
- [ ] Message formatted with markdown

### 4.5 Health Check Command (Database Down)

**Stop PostgreSQL:**
```bash
docker compose stop postgres
```

**In Slack DM:**
```
/ac-agent health
```

**Expected Response:**
```
⚠️ *System Health Status*

❌ PostgreSQL: `disconnected`
✅ Redis: `connected`

_Some systems are experiencing issues._
```

**Restart:**
```bash
docker compose start postgres
```

**Verification:**
- [ ] Shows PostgreSQL as disconnected
- [ ] Shows Redis as connected
- [ ] Warning icon displayed
- [ ] Issues message shown

### 4.6 Echo Command

**In Slack DM:**
```
/ac-agent test message
```

**Expected Response:**
```
I received your command: `test message`

_Command processing is not yet implemented._
```

**Verification:**
- [ ] Command text echoed correctly
- [ ] Code formatting applied
- [ ] Placeholder message shown

### 4.7 Case Insensitivity

**In Slack DM:**
```
/ac-agent HEALTH
/ac-agent Health
/ac-agent HeLtH
```

**Verification:**
- [ ] All variations trigger health check
- [ ] Response identical for all cases

## 5. Logging Tests

### 5.1 Structured Logging

**Check logs:**
```bash
docker compose logs api | head -20
docker compose logs slack-bot | head -20
```

**Verification:**
- [ ] Logs in JSON format (in container)
- [ ] Contains timestamp field
- [ ] Contains log level
- [ ] Contains event name
- [ ] Contains relevant context fields

### 5.2 Log Levels

**Test DEBUG level:**
```bash
LOG_LEVEL=DEBUG docker compose up api
```

**Verification:**
- [ ] DEBUG messages visible
- [ ] More verbose output
- [ ] All log levels present

**Test WARNING level:**
```bash
LOG_LEVEL=WARNING docker compose up api
```

**Verification:**
- [ ] INFO messages filtered out
- [ ] Only WARNING and ERROR visible
- [ ] Reduced log volume

### 5.3 Startup Sequence Logs

**Expected sequence for API:**
1. `fastapi_starting`
2. `database_initialized`
3. `redis_initialized`
4. `fastapi_started`

**Expected sequence for Slack bot:**
1. `slack_bot_starting`
2. `database_initialized`
3. `redis_initialized`
4. `slack_bot_startup_complete`
5. `slack_app_created`
6. `command_handlers_registered`
7. `connecting_to_slack`
8. `slack_bot_connected`

**Verification:**
- [ ] API logs all events in order
- [ ] Slack bot logs all events in order
- [ ] No errors between events

## 6. Error Handling Tests

### 6.1 Configuration Errors

**Test with missing token:**
```bash
# Comment out SLACK_BOT_TOKEN in .env
docker compose up slack-bot
```

**Verification:**
- [ ] Service fails to start
- [ ] Clear error message in logs
- [ ] Mentions missing variable
- [ ] Container exits with non-zero code

**Restore configuration after test**

### 6.2 Database Connection Errors

**Test with invalid database:**
```bash
# Set invalid POSTGRES_URL in .env
POSTGRES_URL=postgresql+asyncpg://invalid:invalid@localhost:9999/invalid
docker compose up api
```

**Verification:**
- [ ] Service fails to start
- [ ] `fastapi_startup_failed` logged
- [ ] Error message mentions PostgreSQL
- [ ] No credentials in error message

**Restore configuration after test**

### 6.3 Graceful Shutdown

**Start services:**
```bash
docker compose up
```

**Press Ctrl+C**

**Verification:**
- [ ] `fastapi_shutting_down` logged
- [ ] `slack_bot_shutting_down` logged
- [ ] `database_closed` logged
- [ ] `redis_closed` logged
- [ ] All services stop cleanly
- [ ] No errors during shutdown

## 7. Performance Tests

### 7.1 Response Times

**API health check:**
```bash
time curl http://localhost:8000/health
```

**Verification:**
- [ ] Response time < 50ms
- [ ] Consistent across multiple calls

**Slack command response:**

**Verification:**
- [ ] Response within 2 seconds
- [ ] Acknowledgment immediate
- [ ] No timeout errors

### 7.2 Concurrent Requests

**Test API concurrency:**
```bash
# Install apache bench if needed
for i in {1..100}; do
  curl -s http://localhost:8000/health > /dev/null &
done
wait
```

**Verification:**
- [ ] All requests succeed
- [ ] No connection errors
- [ ] Services remain stable

## 8. Data Persistence

### 8.1 Volume Persistence

**Create test data:**
```bash
# Access PostgreSQL
docker compose exec postgres psql -U agent_ac -d agent_ac_db

# Create test table and data
CREATE TABLE test_persistence (id SERIAL PRIMARY KEY, value TEXT);
INSERT INTO test_persistence (value) VALUES ('test_data');
\q
```

**Restart without removing volumes:**
```bash
docker compose down
docker compose up -d
```

**Verify data persists:**
```bash
docker compose exec postgres psql -U agent_ac -d agent_ac_db -c "SELECT * FROM test_persistence;"
```

**Verification:**
- [ ] Data persists after restart
- [ ] Table structure preserved
- [ ] Values readable

**Cleanup:**
```bash
docker compose exec postgres psql -U agent_ac -d agent_ac_db -c "DROP TABLE test_persistence;"
```

### 8.2 Redis Persistence

**Test Redis:**
```bash
# Set a value
docker compose exec redis redis-cli SET test_key "test_value"

# Restart
docker compose restart redis

# Verify
docker compose exec redis redis-cli GET test_key
```

**Verification:**
- [ ] Value persists after restart
- [ ] Redis data preserved

## 9. Documentation Verification

**Verify all documentation files exist:**
- [ ] README.md
- [ ] SLACK_SETUP.md
- [ ] TEST_SLACK_COMMANDS.md
- [ ] TEST_HEALTH_CHECK.md
- [ ] TEST_ERROR_HANDLING.md
- [ ] TESTING_GUIDE.md
- [ ] DEVELOPMENT.md
- [ ] INTEGRATION_TEST_CHECKLIST.md (this file)

**Verify all test scripts exist:**
- [ ] test_logging.py
- [ ] test_config_validation.py
- [ ] test_connection_errors.py
- [ ] test_connections.py
- [ ] test_api.py

**Verify all scripts are executable:**
```bash
uv run python test_logging.py
uv run python test_config_validation.py
uv run python test_connection_errors.py
uv run python test_connections.py
uv run python test_api.py
```

## 10. Final Checklist

- [ ] All services start successfully
- [ ] All health checks pass
- [ ] All API endpoints respond correctly
- [ ] Slack bot connects and stays online
- [ ] All Slack commands work in DMs
- [ ] DM-only enforcement works
- [ ] Health check shows accurate status
- [ ] Error handling works correctly
- [ ] Logging is structured and complete
- [ ] Configuration validation works
- [ ] Data persists across restarts
- [ ] Graceful shutdown works
- [ ] All test scripts pass
- [ ] All documentation complete and accurate
- [ ] No secrets in repository
- [ ] .gitignore configured correctly

## Sign-Off

**Date:** _____________

**Tested by:** _____________

**Version:** _____________

**Result:** ☐ PASS  ☐ FAIL

**Notes:**
_______________________________________________
_______________________________________________
_______________________________________________

**Issues Found:**
_______________________________________________
_______________________________________________
_______________________________________________
