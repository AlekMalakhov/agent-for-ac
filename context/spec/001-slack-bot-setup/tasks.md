# Task List: Slack Bot Setup

**Goal:** Set up foundational Python infrastructure for Agent for AC with Slack bot, FastAPI health endpoints, PostgreSQL, and Redis.

**Implementation Strategy:** Each main task (slice) represents a small, end-to-end increment that leaves the application in a runnable state.

---

## Slice 1: Project Scaffolding & Configuration Foundation

**Outcome:** Project can be initialized with uv, has proper structure, and configuration can be loaded and validated (but app doesn't run yet).

- [x] **Initialize uv project and create directory structure**
  - [x] Run `uv init --lib agent-for-ac` to create project
  - [x] Create `src/` directory structure: `config/`, `core/`, `api/`, `slack/`, `schemas/`, `services/`
  - [x] Create empty `__init__.py` files in all directories
  - [x] Create `tests/` directory with `__init__.py`, `conftest.py`, `unit/` subdirectory

- [x] **Set up dependency management**
  - [x] Add all required dependencies to `pyproject.toml` (fastapi, slack-bolt, pydantic-settings, sqlmodel, redis, asyncpg, uvicorn, langchain, sentry-sdk, structlog, python-dotenv)
  - [x] Add dev dependencies (pytest, pytest-asyncio, httpx)
  - [x] Run `uv sync` to install dependencies and create lockfile

- [x] **Create configuration system**
  - [x] Implement `src/config/settings.py` with Pydantic Settings class
  - [x] Define all environment variables with proper types (SecretStr, PostgresDsn, RedisDsn)
  - [x] Add validation (log_level validator)
  - [x] Create singleton `get_settings()` function
  - [x] Create `.env.example` with all required variables documented
  - [x] Add `.env` to `.gitignore`

- [x] **Create basic project files**
  - [x] Create `.gitignore` (include `.env`, `__pycache__`, `*.pyc`, `uv.lock`, `.pytest_cache`, `*.egg-info`)
  - [x] Create `README.md` with project description and setup instructions placeholder

**Test:** Can run `python -c "from src.config.settings import get_settings; get_settings()"` without errors (after creating `.env` with minimal config).

---

## Slice 2: Logging Infrastructure & Core Exceptions

**Outcome:** Application can initialize logging and has proper exception handling foundation. Can run a minimal Python script that logs messages.

- [x] **Implement structured logging**
  - [x] Create `src/core/logging.py` with `configure_logging()` function
  - [x] Set up structlog with appropriate processors (timestamp, log level, console/JSON rendering)
  - [x] Configure log output based on TTY (pretty for development, JSON for production)
  - [x] Test log level configuration from settings

- [x] **Create exception hierarchy**
  - [x] Create `src/core/exceptions.py`
  - [x] Define `ApplicationError` base exception
  - [x] Define `ConfigurationError`, `DatabaseConnectionError`, `SlackConnectionError` subclasses

- [x] **Create minimal test script**
  - [x] Create test script that loads settings, configures logging, and logs test messages
  - [x] Verify structured logging works correctly with different log levels

**Test:** Can run test script that outputs properly formatted logs to console.

---

## Slice 3: Database & Redis Connection Layer

**Outcome:** Application can connect to PostgreSQL and Redis, create tables, and perform basic health checks. Infrastructure is runnable with Docker Compose.

- [x] **Implement database connection management**
  - [x] Create `src/core/database.py` with async SQLAlchemy engine setup
  - [x] Implement `init_database()` function (creates engine, tests connection, creates tables)
  - [x] Implement `close_database()` function
  - [x] Implement `get_db_session()` context manager
  - [x] Add proper error handling with sanitized logging (no credentials in logs)

- [x] **Implement Redis connection management**
  - [x] Create `src/core/cache.py` with async Redis client setup
  - [x] Implement `init_redis()` function (creates connection pool, tests with ping)
  - [x] Implement `close_redis()` function
  - [x] Implement `get_redis()` accessor function
  - [x] Add proper error handling with sanitized logging

- [x] **Create health check service**
  - [x] Create `src/services/health_check.py`
  - [x] Implement `check_database()` function (returns "connected" or "disconnected")
  - [x] Implement `check_redis()` function (returns "connected" or "disconnected")
  - [x] Handle cases where engine/client not initialized

- [x] **Set up Docker infrastructure**
  - [x] Create `docker-compose.yml` with PostgreSQL and Redis services only
  - [x] Add health checks for both services
  - [x] Add volume configuration for data persistence
  - [x] Test: `docker-compose up postgres redis` starts both services

- [x] **Create connection test script**
  - [x] Create script that loads config, initializes DB and Redis, runs health checks, closes connections
  - [x] Test script against Docker services

**Test:** Run Docker Compose (postgres + redis only), then run connection test script. Should see "database_connected" and "redis_connected" log messages.

---

## Slice 4: FastAPI Health Endpoints

**Outcome:** FastAPI application runs and exposes `/health` and `/readiness` endpoints. Can test via HTTP requests.

- [x] **Create Pydantic response schemas**
  - [x] Create `src/schemas/health.py`
  - [x] Define `HealthResponse` model (status, service fields)
  - [x] Define `ReadinessResponse` model (status, postgres, redis fields)

- [x] **Create health route handlers**
  - [x] Create `src/api/routes/health.py`
  - [x] Implement `GET /health` endpoint (always returns 200 with healthy status)
  - [x] Implement `GET /readiness` endpoint (checks DB and Redis, returns 200 if ready, 503 if not)
  - [x] Use health check service functions

- [x] **Create FastAPI application factory**
  - [x] Create `src/api/app.py`
  - [x] Implement `create_app()` factory function
  - [x] Add lifespan context manager for startup/shutdown logging
  - [x] Register health router
  - [x] Configure FastAPI metadata (title, description, version)

- [x] **Create API startup script**
  - [x] Create startup logic that initializes DB/Redis before starting FastAPI
  - [x] Handle graceful shutdown

- [x] **Add API service to Docker Compose**
  - [x] Create `Dockerfile` with Python 3.12, uv installation, dependency sync
  - [x] Add `api` service to `docker-compose.yml`
  - [x] Configure command to run uvicorn with factory pattern
  - [x] Add volume mount for hot reload
  - [x] Add dependency on postgres and redis with health checks
  - [x] Expose port 8000

**Test:** Run `docker-compose up` (postgres, redis, api). Test `curl http://localhost:8000/health` (should return `{"status": "healthy", "service": "agent-for-ac"}`). Test `curl http://localhost:8000/readiness` (should return ready status with both services connected).

---

## Slice 5: Slack Bot Connection & Basic Setup

**Outcome:** Slack bot connects to workspace via Socket Mode and appears online. Doesn't handle commands yet, but establishes connection.

- [x] **Create minimal Slack bot application**
  - [x] Create `src/slack/app.py` with `create_slack_app()` function
  - [x] Initialize `AsyncApp` with bot token from settings
  - [x] Create `AsyncSocketModeHandler` with app token
  - [x] Return handler (don't register any commands yet)

- [x] **Create Slack bot startup sequence**
  - [x] Implement `startup()` async function (loads config, initializes logging, Sentry, DB, Redis)
  - [x] Implement `shutdown()` async function (closes DB and Redis)
  - [x] Implement `main()` function that runs full startup → create bot → start Socket Mode → shutdown
  - [x] Add proper error handling (configuration, DB, Redis, Slack connection failures)
  - [x] Make module runnable with `if __name__ == "__main__": asyncio.run(main())`

- [x] **Add Slack bot service to Docker Compose**
  - [x] Add `slack-bot` service to `docker-compose.yml`
  - [x] Configure command to run `python -m src.slack.app`
  - [x] Add volume mount for hot reload
  - [x] Add dependency on postgres and redis with health checks
  - [x] Use same `.env` file

- [x] **Test Slack connection**
  - [x] Add real Slack tokens to `.env` file
  - [x] Run `docker-compose up` (all services)
  - [x] Verify in logs: "slack_bot_starting", "Connected to Slack via Socket Mode"
  - [x] Check Slack workspace - bot should appear online/active

**Test:** Bot appears online in Slack workspace. Logs show successful connection to Slack, DB, and Redis.

---

## Slice 6: Slash Command with Placeholder Responses

**Outcome:** Users can send `/ac-agent` commands in DMs and receive placeholder responses. Bot is now interactive.

- [x] **Create command handler module**
  - [x] Create `src/slack/handlers/__init__.py`
  - [x] Create `src/slack/handlers/commands.py` with `register()` function
  - [x] Implement `handle_ac_agent_command()` async function
  - [x] Add command acknowledgment (`await ack()`)
  - [x] Extract user_id, text, channel_type from command payload
  - [x] Add DM-only filter (reject if not "directmessage")
  - [x] Log command received with user_id and text

- [x] **Implement basic command responses**
  - [x] Handle empty command (no text) → respond with welcome message
  - [x] Handle command with any text → respond with "I received your command: `{text}`" message
  - [x] Use `await say()` to send responses

- [x] **Register handlers in Slack app**
  - [x] Update `src/slack/app.py` to call `commands.register(app)` before creating handler
  - [x] Import commands module

- [x] **Test Slack command interaction**
  - [x] Restart slack-bot service
  - [x] Open DM with bot in Slack
  - [x] Send `/ac-agent` → should receive welcome message
  - [x] Send `/ac-agent test` → should receive "I received your command: `test`"
  - [x] Try sending command in a channel → should receive "Please use this command in a direct message"

**Test:** Users can interact with bot via `/ac-agent` command in DMs and receive appropriate responses.

---

## Slice 7: Health Check Command

**Outcome:** Users can check system health via `/ac-agent health` command in Slack.

- [x] **Implement health check command handling**
  - [x] Update `handle_ac_agent_command()` in `src/slack/handlers/commands.py`
  - [x] Add check for `text.lower() == "health"`
  - [x] Call `check_database()` and `check_redis()` from health check service
  - [x] Format response with bot status, PostgreSQL status, Redis status
  - [x] Use Slack markdown with checkmarks/X marks for visual status
  - [x] Send formatted response via `await say()`

- [x] **Test health check via Slack**
  - [x] Restart slack-bot service
  - [x] Send `/ac-agent health` in DM → should receive formatted health status
  - [x] Stop postgres service: `docker-compose stop postgres`
  - [x] Send `/ac-agent health` again → should show PostgreSQL as disconnected
  - [x] Restart postgres: `docker-compose start postgres`
  - [x] Verify health check shows connected again

**Test:** `/ac-agent health` command accurately reports status of all system components.

---

## Slice 8: Error Handling & Startup Validation

**Outcome:** Application fails gracefully with clear error messages when misconfigured or when dependencies are unavailable.

- [x] **Test and verify configuration validation**
  - [x] Remove `SLACK_BOT_TOKEN` from `.env`, restart → verify clear error message logged
  - [x] Remove `POSTGRES_URL` from `.env`, restart → verify clear error message logged
  - [x] Restore valid config

- [x] **Test connection error handling**
  - [x] Set invalid Slack token in `.env`, restart → verify "Failed to connect to Slack" error
  - [x] Set invalid PostgreSQL URL, restart → verify "Failed to connect to PostgreSQL" error
  - [x] Set invalid Redis URL, restart → verify "Failed to connect to Redis" error
  - [x] Restore valid config

- [x] **Verify startup sequence logging**
  - [x] Run `docker-compose up` with all services
  - [x] Verify logs show complete startup sequence:
    - "configuration_loaded"
    - "database_connected"
    - "redis_connected"
    - "slack_app_created"
    - "slack_bot_starting"
    - "fastapi_starting"

- [x] **Test error exit codes**
  - [x] Verify application exits with non-zero code on startup failure

**Test:** Application fails fast with clear, actionable error messages for all error scenarios.

---

## Slice 9: Documentation & Final Integration Testing

**Outcome:** Project is fully documented and all integration tests pass. System is ready for development of next features.

- [x] **Write comprehensive README.md**
  - [x] Add project description and purpose
  - [x] Add prerequisites (Docker, Python 3.12, uv)
  - [x] Add setup instructions (clone, copy .env.example, configure tokens)
  - [x] Add usage instructions (how to start services, test endpoints, use Slack bot)
  - [x] Add development workflow (hot reload, logs)
  - [x] Add troubleshooting section

- [x] **Add inline code documentation**
  - [x] Review all modules and add docstrings where missing
  - [x] Add comments for complex logic (especially startup sequence)
  - [x] Ensure configuration variables are well-documented in `.env.example`

- [x] **Perform full integration test suite (manual)**
  - [x] Fresh start: `docker-compose down -v` (remove volumes)
  - [x] `docker-compose up --build`
  - [x] Test `/health` endpoint → returns healthy
  - [x] Test `/readiness` endpoint → returns ready
  - [x] Test Slack DM: `/ac-agent` → welcome message
  - [x] Test Slack DM: `/ac-agent health` → health status
  - [x] Test Slack DM: `/ac-agent test command` → echo response
  - [x] Test Slack channel: `/ac-agent` → DM-only message
  - [x] Stop/restart services → data persists (volumes work)

- [x] **Create development guide**
  - [x] Document local development workflow (running individual services)
  - [x] Document how to run tests: `uv run pytest`
  - [x] Document how to add new Slack commands
  - [x] Document logging best practices

**Test:** All manual integration tests pass. Documentation is clear and complete for onboarding new developers.

---

**Total:** 9 vertical slices, each leaving the application in a runnable state.
