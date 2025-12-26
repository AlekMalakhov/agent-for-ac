# Testing Quick Reference Card

## Slice 8: Error Handling & Startup Validation

### Quick Test Commands

#### 1. Configuration Validation (No dependencies needed)
```bash
uv run python test_config_validation.py
```
**Tests:** 4 validation scenarios
**Time:** ~5 seconds
**Dependencies:** None

---

#### 2. Connection Error Handling (Requires Docker)
```bash
# Start dependencies
docker compose up -d postgres redis

# Run tests
uv run python test_connection_errors.py

# Cleanup
docker compose down
```
**Tests:** 3 connection scenarios
**Time:** ~10 seconds
**Dependencies:** PostgreSQL, Redis

---

### Test Scripts Overview

| Script | Tests | Async | Dependencies |
|--------|-------|-------|--------------|
| `test_config_validation.py` | 4 | No | None |
| `test_connection_errors.py` | 3 | Yes | postgres, redis |

---

### Test Coverage

#### Configuration Validation
- ✅ Missing SLACK_BOT_TOKEN
- ✅ Missing POSTGRES_URL
- ✅ Invalid LOG_LEVEL
- ✅ Valid configuration

#### Connection Error Handling
- ✅ Invalid PostgreSQL connection
- ✅ Invalid Redis connection
- ✅ Valid connections

#### Manual Testing (see TEST_ERROR_HANDLING.md)
- ✅ API startup logging
- ✅ Slack bot startup logging
- ✅ Error exit codes
- ✅ Graceful shutdown

---

### Expected Output

#### Configuration Tests
```
==================================================
Configuration Validation Tests
==================================================
Test 1: Missing SLACK_BOT_TOKEN
--------------------------------------------------
✅ PASSED: Validation error raised: ValidationError

Test 2: Missing POSTGRES_URL
--------------------------------------------------
✅ PASSED: Validation error raised: ValidationError

Test 3: Invalid LOG_LEVEL
--------------------------------------------------
✅ PASSED: Validation error raised: ValidationError

Test 4: Valid Configuration
--------------------------------------------------
✅ PASSED: Configuration loaded successfully

==================================================
Results: 4/4 tests passed
==================================================
```

#### Connection Tests
```
==================================================
Connection Error Handling Tests
==================================================
Test 1: Invalid PostgreSQL Connection
--------------------------------------------------
✅ PASSED: DatabaseConnectionError raised

Test 2: Invalid Redis Connection
--------------------------------------------------
✅ PASSED: ApplicationError raised

Test 3: Valid Connections
--------------------------------------------------
✅ Database connection successful
✅ Redis connection successful

==================================================
Results: 3/3 tests passed
==================================================
```

---

### Exit Codes

- `0` = All tests passed
- `1` = One or more tests failed

**Check last exit code:**
```bash
echo $?
```

---

### Troubleshooting

#### Import errors
```bash
uv sync
```

#### Docker issues
```bash
docker compose down -v
docker compose up -d postgres redis
```

#### Configuration cache
Tests automatically call `get_settings.cache_clear()`

---

### File Locations

All files are in project root:
- `/Users/amalakhov/awos/agent_for_ac/test_config_validation.py`
- `/Users/amalakhov/awos/agent_for_ac/test_connection_errors.py`
- `/Users/amalakhov/awos/agent_for_ac/TEST_ERROR_HANDLING.md`
- `/Users/amalakhov/awos/agent_for_ac/TESTING_GUIDE.md`

---

### Documentation

| Document | Purpose |
|----------|---------|
| `TEST_ERROR_HANDLING.md` | Manual testing procedures |
| `TESTING_GUIDE.md` | Comprehensive testing overview |
| `TESTING_QUICK_REFERENCE.md` | This quick reference |
| `SLICE_8_IMPLEMENTATION.md` | Implementation details |

---

### CI/CD Integration

```bash
#!/bin/bash
set -e

# Configuration tests (no dependencies)
uv run python test_config_validation.py

# Start services
docker compose up -d postgres redis
sleep 5

# Connection tests
uv run python test_connection_errors.py

# Cleanup
docker compose down -v

echo "All tests passed!"
```

---

### Key Features

All test scripts:
- ✅ Save and restore environment state
- ✅ Use try/finally for guaranteed cleanup
- ✅ Clear Pydantic Settings cache
- ✅ Provide colored output (✅/❌/⚠️)
- ✅ Exit with proper codes (0/1)
- ✅ Include descriptive error messages

---

### Next Steps

1. Run automated tests: `uv run python test_config_validation.py`
2. Run connection tests with Docker
3. Follow manual testing guide: `TEST_ERROR_HANDLING.md`
4. Verify startup/shutdown behavior
5. Check error logging and exit codes

---

### Support

For detailed documentation, see:
- **TESTING_GUIDE.md** - Complete testing documentation
- **TEST_ERROR_HANDLING.md** - Step-by-step manual procedures
- **SLICE_8_IMPLEMENTATION.md** - Technical implementation details
