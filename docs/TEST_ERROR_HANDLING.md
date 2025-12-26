# Error Handling & Startup Validation Testing Guide

This guide provides manual testing procedures to verify error handling and startup validation.

## Prerequisites

- Docker and Docker Compose installed
- Valid `.env` file with correct configuration
- Access to modify `.env` file temporarily

## Test Categories

1. Configuration Validation
2. Connection Error Handling
3. Startup Sequence Logging
4. Error Exit Codes

---

## 1. Configuration Validation Tests

### Test 1.1: Missing SLACK_BOT_TOKEN

**Action:**
1. Create a backup of `.env`: `cp .env .env.backup`
2. Comment out `SLACK_BOT_TOKEN` in `.env`
3. Run: `uv run python test_config_validation.py`

**Expected result:**
- Script reports validation error raised
- Error message mentions "SLACK_BOT_TOKEN"
- Test passes with ✅

**Cleanup:**
```bash
cp .env.backup .env
```

---

### Test 1.2: Missing POSTGRES_URL

**Action:**
1. Comment out `POSTGRES_URL` in `.env`
2. Run: `uv run python test_config_validation.py`

**Expected result:**
- Script reports validation error raised
- Error message mentions "POSTGRES_URL"
- Test passes with ✅

**Cleanup:**
```bash
cp .env.backup .env
```

---

### Test 1.3: Invalid LOG_LEVEL

**Action:**
1. Set `LOG_LEVEL=INVALID_LEVEL` in `.env`
2. Run: `uv run python test_config_validation.py`

**Expected result:**
- Script reports validation error raised
- Error message mentions invalid log level
- Test passes with ✅

**Cleanup:**
```bash
cp .env.backup .env
```

---

### Test 1.4: Run All Config Tests

**Action:**
```bash
uv run python test_config_validation.py
```

**Expected result:**
```
==================================================
Configuration Validation Tests
==================================================
Test 1: Missing SLACK_BOT_TOKEN
--------------------------------------------------
✅ PASSED: Validation error raised: ValidationError
   Error message: ...

Test 2: Missing POSTGRES_URL
--------------------------------------------------
✅ PASSED: Validation error raised: ValidationError
   Error message: ...

Test 3: Invalid LOG_LEVEL
--------------------------------------------------
✅ PASSED: Validation error raised: ValidationError
   Error message: ...

Test 4: Valid Configuration
--------------------------------------------------
✅ PASSED: Configuration loaded successfully
   Environment: local
   Log level: INFO
   Redis URL: redis://redis:6379/0

==================================================
Results: 4/4 tests passed
==================================================
```

---

## 2. Connection Error Handling Tests

### Test 2.1: Invalid PostgreSQL Connection

**Setup:**
```bash
docker compose up -d redis  # Start only Redis
```

**Action:**
```bash
uv run python test_connection_errors.py
```

**Expected result:**
- Test 1 passes: DatabaseConnectionError raised for invalid PostgreSQL
- Error message indicates connection failure
- Test passes with ✅

---

### Test 2.2: Invalid Redis Connection

**Action:**
```bash
uv run python test_connection_errors.py
```

**Expected result:**
- Test 2 passes: ApplicationError raised for invalid Redis
- Error message indicates connection failure
- Test passes with ✅

---

### Test 2.3: Valid Connections

**Setup:**
```bash
docker compose up -d postgres redis
```

**Action:**
```bash
uv run python test_connection_errors.py
```

**Expected result:**
```
Test 3: Valid Connections
--------------------------------------------------
✅ Database connection successful
✅ Redis connection successful
```

---

## 3. Startup Sequence Logging Tests

### Test 3.1: API Startup Logs

**Action:**
```bash
docker compose up api
```

**Expected logs (in order):**
```
fastapi_starting
database_initialized
redis_initialized
fastapi_started
```

**Verification:**
- All four events logged
- No errors in logs
- Service stays running

**Stop:**
```bash
docker compose down
```

---

### Test 3.2: Slack Bot Startup Logs

**Action:**
```bash
docker compose up slack-bot
```

**Expected logs (in order):**
```
slack_bot_starting
database_initialized
redis_initialized
slack_bot_startup_complete
slack_app_created
command_handlers_registered
connecting_to_slack
slack_bot_connected
```

**Verification:**
- All events logged in sequence
- No errors
- Bot stays connected

**Stop:**
```bash
docker compose down
```

---

### Test 3.3: All Services Startup

**Action:**
```bash
docker compose up
```

**Expected behavior:**
- postgres and redis start first (healthchecks pass)
- api service starts after dependencies are healthy
- slack-bot service starts after dependencies are healthy
- Both api and slack-bot log complete startup sequences
- All services remain running

**Verification:**
```bash
docker compose ps
# All services should show "Up" status
```

---

## 4. Error Exit Code Tests

### Test 4.1: API Startup Failure

**Setup:**
```bash
# Stop postgres
docker compose up -d redis
docker compose stop postgres
```

**Action:**
```bash
docker compose up api
```

**Expected result:**
- API attempts to connect to PostgreSQL
- Logs show: `fastapi_startup_failed` with error
- Container exits with non-zero exit code
- Check exit code: `docker compose ps api`

**Cleanup:**
```bash
docker compose down
```

---

### Test 4.2: Slack Bot Startup Failure (Invalid Token)

**Setup:**
1. Set `SLACK_BOT_TOKEN=xoxb-invalid-token` in `.env`
2. Start dependencies: `docker compose up -d postgres redis`

**Action:**
```bash
docker compose up slack-bot
```

**Expected result:**
- Bot attempts to connect
- Logs show error related to invalid token
- Container exits with error
- Error logged with `slack_bot_failed` event

**Cleanup:**
```bash
cp .env.backup .env
docker compose down
```

---

### Test 4.3: Graceful Shutdown

**Action:**
```bash
docker compose up
# Press Ctrl+C after all services are up
```

**Expected logs:**
- API logs: `fastapi_shutting_down`, `database_closed`, `redis_closed`, `fastapi_shutdown`
- Slack bot logs: `slack_bot_shutting_down`, `database_closed`, `redis_closed`, `slack_bot_shutdown`

**Verification:**
- All services shut down cleanly
- Connection cleanup messages logged
- No error messages during shutdown

---

## Summary Checklist

After completing all tests, verify:

- [ ] Missing configuration variables raise validation errors
- [ ] Invalid configuration values raise validation errors
- [ ] Invalid database connection raises DatabaseConnectionError
- [ ] Invalid Redis connection raises ApplicationError
- [ ] Valid connections work correctly
- [ ] API startup logs all required events
- [ ] Slack bot startup logs all required events
- [ ] Startup failures exit with non-zero codes
- [ ] Startup failures log clear error messages
- [ ] Graceful shutdown closes all connections
- [ ] Shutdown logs cleanup events
- [ ] All errors have descriptive messages
- [ ] No credentials appear in error logs

## Troubleshooting

### Tests fail to import modules

**Solution:**
```bash
uv sync
```

### Docker services don't start

**Solution:**
```bash
docker compose down -v
docker compose up --build
```

### Configuration cache issues

**Solution:**
The test scripts call `get_settings.cache_clear()` to handle this automatically.
