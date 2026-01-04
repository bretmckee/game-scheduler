<!-- markdownlint-disable-file -->

# Task Details: RLS Phase 2 - BYPASSRLS Bot User Implementation

## Research Reference

**Source Research**: #file:../research/20260102-rls-performance-scaling-bot-analysis.md

## Phase 1: Create BYPASSRLS Database User

### Task 1.1: Add gamebot_bot user creation to database_users.py

Add code to create `gamebot_bot` database user with BYPASSRLS privilege after the `gamebot_app` user creation.

- **Files**:
  - services/init/database_users.py - Add bot user creation after line 146
- **Success**:
  - Bot user created with BYPASSRLS privilege (not SUPERUSER)
  - User has LOGIN privilege
  - Comment indicates purpose (bot/daemon services)
  - Logging confirms user creation
  - Grants CONNECT, USAGE on database/schema
  - Grants SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER on all tables
  - Grants USAGE, SELECT, UPDATE on sequences
  - Grants EXECUTE on functions
  - Sets DEFAULT PRIVILEGES for future objects created by gamebot_app
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 795-858) - Step 1: Create gamebot_bot Database User
- **Dependencies**:
  - gamebot_app user already created (current code)
  - POSTGRES_BOT_USER and POSTGRES_BOT_PASSWORD env vars set

### Task 1.2: Update environment template with bot user variables

Add bot user environment variables to the template file with documentation.

- **Files**:
  - config.template/env.template - Add after POSTGRES_APP_PASSWORD section
- **Success**:
  - POSTGRES_BOT_USER variable documented
  - POSTGRES_BOT_PASSWORD variable documented with security note
  - BOT_DATABASE_URL variable documented with format
  - Clear comments explain bot user purpose (BYPASSRLS for bot/daemon services)
  - Template values follow dev_*_change_in_prod pattern
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 860-880) - Step 2: Update Environment Variables (Template section)
- **Dependencies**:
  - None

### Task 1.3: Update all environment files with bot user credentials

Add bot user credentials to all environment configuration files.

- **Files**:
  - config/env.dev - Add bot user variables
  - config/env.staging - Add bot user variables
  - config/env.prod - Add bot user variables
  - config/env.int - Add bot user variables
  - config/env.e2e - Add bot user variables
- **Success**:
  - All 5 environment files updated
  - POSTGRES_BOT_USER=gamebot_bot in all files
  - POSTGRES_BOT_PASSWORD unique per environment
  - BOT_DATABASE_URL correctly formatted with user, password, host, port, database
  - Variables added after POSTGRES_APP_PASSWORD (consistent ordering)
  - Dev: dev_bot_password_change_in_prod
  - Staging: staging_bot_password_change_me
  - Prod: prod_bot_password_change_in_prod
  - Int: integration_bot_password
  - E2E: e2e_bot_password
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 882-932) - Step 2: Update Environment Variables (all environment files)
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: Configure Services to Use Bot User

### Task 2.1: Update Docker Compose for bot service

Configure bot service to use BOT_DATABASE_URL instead of DATABASE_URL.

- **Files**:
  - compose.yaml - Update bot service environment section
- **Success**:
  - Bot service DATABASE_URL changed to ${BOT_DATABASE_URL}
  - Comment added explaining bot uses separate user
  - No other bot configuration changed
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 934-940) - Step 3: Bot service configuration
- **Dependencies**:
  - Task 1.3 completion (BOT_DATABASE_URL defined in env files)

### Task 2.2: Update Docker Compose for daemon services

Configure notification and status-transition daemons to use BOT_DATABASE_URL.

- **Files**:
  - compose.yaml - Update notification-daemon environment
  - compose.yaml - Update status-transition-daemon environment
- **Success**:
  - notification-daemon DATABASE_URL changed to ${BOT_DATABASE_URL}
  - status-transition-daemon DATABASE_URL changed to ${BOT_DATABASE_URL}
  - Comments added explaining daemons use bot user (system services)
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 942-952) - Step 3: Daemon services configuration
- **Dependencies**:
  - Task 1.3 completion

### Task 2.3: Update init service to use admin database URL

Optionally switch init service to use ADMIN_DATABASE_URL for migrations.

- **Files**:
  - compose.yaml - Update init service environment (optional)
- **Success**:
  - Init service DATABASE_URL changed to ${ADMIN_DATABASE_URL}
  - Init service has POSTGRES_BOT_USER and POSTGRES_BOT_PASSWORD for user creation
  - Comment explains admin user used for migrations/schema changes
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 954-960) - Step 3: Init service configuration
- **Dependencies**:
  - gamebot_admin user already exists and configured

## Phase 3: Remove Guild Context Management

### Task 3.1: Remove RLS context setting from bot service

Remove guild context management code from bot service since it now bypasses RLS.

- **Files**:
  - Services that import or call set_current_guild_ids in bot service
  - Any bot-specific database dependency that sets guild context
- **Success**:
  - Identify all locations where bot service calls set_current_guild_ids
  - Remove those calls since bot bypasses RLS
  - Verify bot queries still work without guild context
  - No errors in bot service logs
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 962-967) - Step 4: Remove Guild Context Management
- **Dependencies**:
  - Task 2.1 completion (bot using BOT_DATABASE_URL)

### Task 3.2: Remove RLS context setting from daemon services

Remove guild context management code from daemon services.

- **Files**:
  - services/scheduler/notification_daemon.py - Remove guild context calls
  - services/scheduler/status_transition_daemon.py - Remove guild context calls
- **Success**:
  - All set_current_guild_ids calls removed from daemons
  - Daemon queries work without guild context
  - No errors in daemon logs
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 962-967) - Step 4: Remove Guild Context Management
- **Dependencies**:
  - Task 2.2 completion (daemons using BOT_DATABASE_URL)

## Phase 4: Validation and Testing

### Task 4.1: Create database user validation test

Create test to validate database user privileges are correct.

- **Files**:
  - tests/integration/test_database_users.py - New test file
- **Success**:
  - Test queries pg_roles to check user attributes
  - Validates gamebot_admin: rolsuper=true, rolbypassrls=true
  - Validates gamebot_app: rolsuper=false, rolbypassrls=false
  - Validates gamebot_bot: rolsuper=false, rolbypassrls=true
  - Test passes in CI/CD
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 969-989) - Step 5: Validation Testing (Test 3)
- **Dependencies**:
  - Task 1.1 completion (gamebot_bot user created)

### Task 4.2: Verify API still enforces RLS

Create test to verify API service queries are still filtered by RLS.

- **Files**:
  - tests/integration/test_rls_api_enforcement.py - New test file
- **Success**:
  - Test connects using gamebot_app user (API user)
  - Sets guild context to specific guilds
  - Queries game_sessions table
  - Validates only games from specified guilds returned
  - RLS is actively filtering results
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 969-989) - Step 5: Validation Testing (Test 2)
- **Dependencies**:
  - API service still using DATABASE_URL (gamebot_app)
  - RLS policies enabled on tables

### Task 4.3: Verify bot/daemons bypass RLS

Create test to verify bot/daemon services bypass RLS and see all guilds.

- **Files**:
  - tests/integration/test_rls_bot_bypass.py - New test file
- **Success**:
  - Test connects using gamebot_bot user (bot/daemon user)
  - Does NOT set guild context
  - Queries game_sessions table
  - Validates games from ALL guilds returned (no filtering)
  - RLS is bypassed for this user
- **Research References**:
  - #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 969-989) - Step 5: Validation Testing (Test 1)
- **Dependencies**:
  - Task 1.1 completion (gamebot_bot created with BYPASSRLS)
  - Bot/daemon services using BOT_DATABASE_URL

## Success Criteria

- All code changes implemented and tested
- Database user creation successful in all environments
- Bot and daemons connect with gamebot_bot user
- API connects with gamebot_app user (no change)
- RLS enforcement validated for API
- RLS bypass validated for bot/daemons
- No cross-guild data leaks
- All integration tests pass
- Performance improvement measurable (50-100μs per query saved)
