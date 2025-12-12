<!-- markdownlint-disable-file -->

# Task Details: RabbitMQ Messaging Architecture Cleanup

## Research Reference

**Source Research**: #file:../research/20251211-dlq-exponential-growth-analysis.md

## Phase 1: Remove Unused Infrastructure

### Task 1.1: Remove unused queue constants from infrastructure.py

Remove QUEUE_API_EVENTS, QUEUE_SCHEDULER_EVENTS, and their related constants from shared/messaging/infrastructure.py.

- **Files**:
  - shared/messaging/infrastructure.py - Remove unused queue constant definitions
- **Success**:
  - QUEUE_API_EVENTS and QUEUE_SCHEDULER_EVENTS constants removed
  - No references to these constants remain in infrastructure.py
  - Code still compiles without errors
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 455-498) - Queue topology and unused queue identification
- **Dependencies**: None

### Task 1.2: Update PRIMARY_QUEUES and QUEUE_BINDINGS lists

Update PRIMARY_QUEUES list to only include bot_events and notification_queue. Update QUEUE_BINDINGS to remove scheduler_events and api_events bindings.

- **Files**:
  - shared/messaging/infrastructure.py - Update PRIMARY_QUEUES and QUEUE_BINDINGS lists
- **Success**:
  - PRIMARY_QUEUES contains only QUEUE_BOT_EVENTS and QUEUE_NOTIFICATION
  - QUEUE_BINDINGS contains only bindings for bot_events and notification_queue
  - No bindings reference api_events or scheduler_events
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 455-498) - Final queue topology specification
- **Dependencies**: Task 1.1 completion

### Task 1.3: Remove unused queue declarations from init_rabbitmq.py

Remove queue declaration logic for api_events and scheduler_events from RabbitMQ initialization script.

- **Files**:
  - scripts/init_rabbitmq.py - Remove unused queue declarations
- **Success**:
  - init_rabbitmq.py no longer declares api_events or scheduler_events queues
  - Script still declares bot_events and notification_queue successfully
  - Script runs without errors
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 455-498) - Queue cleanup requirements
- **Dependencies**: Task 1.2 completion (PRIMARY_QUEUES updated)

### Task 1.4: Update integration tests to remove unused queue references

Remove any test code that references api_events or scheduler_events queues.

- **Files**:
  - tests/integration/ - Search for and update tests referencing unused queues
- **Success**:
  - No test failures related to missing queues
  - Integration tests pass with new queue configuration
  - grep for "api_events\|scheduler_events" returns no results in tests/
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 455-498) - Queue removal impact
- **Dependencies**: Task 1.3 completion

## Phase 2: Implement Per-Queue DLQ Pattern

### Task 2.1: Add per-queue DLQ constants to infrastructure.py

Add QUEUE_BOT_EVENTS_DLQ and QUEUE_NOTIFICATION_DLQ constants and create DEAD_LETTER_QUEUES list.

- **Files**:
  - shared/messaging/infrastructure.py - Add DLQ constants and list
- **Success**:
  - QUEUE_BOT_EVENTS_DLQ = "bot_events.dlq" constant defined
  - QUEUE_NOTIFICATION_DLQ = "notification_queue.dlq" constant defined
  - DEAD_LETTER_QUEUES list contains both DLQ constants
  - Constants follow naming convention of primary_queue_name.dlq
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 673-802) - Per-queue DLQ architecture design
- **Dependencies**: Phase 1 completion

### Task 2.2: Update init_rabbitmq.py to create per-queue DLQs

Add logic to declare bot_events.dlq and notification_queue.dlq queues bound to DLX exchange.

- **Files**:
  - scripts/init_rabbitmq.py - Add per-queue DLQ declaration logic
- **Success**:
  - bot_events.dlq queue declared as durable, no TTL
  - notification_queue.dlq queue declared as durable, no TTL
  - Both DLQs bound to game_scheduler.dlx exchange
  - DLQs created before primary queues (dependency order)
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 673-802) - DLQ implementation specification
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 455-498) - Final queue topology
- **Dependencies**: Task 2.1 completion

### Task 2.3: Remove shared "DLQ" queue declaration

Remove QUEUE_DLQ constant and its declaration from init_rabbitmq.py.

- **Files**:
  - shared/messaging/infrastructure.py - Remove QUEUE_DLQ constant
  - scripts/init_rabbitmq.py - Remove DLQ queue declaration
- **Success**:
  - QUEUE_DLQ constant removed from infrastructure.py
  - No references to "DLQ" queue in init_rabbitmq.py
  - Only per-queue DLQs remain (bot_events.dlq, notification_queue.dlq)
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 86-175) - Root cause of exponential growth (shared DLQ)
- **Dependencies**: Task 2.2 completion

## Phase 3: Create Dedicated Retry Service

### Task 3.1: Create retry_daemon.py with RetryDaemon class

Create new retry service that processes all DLQs with configurable retry intervals.

- **Files**:
  - services/retry/__init__.py - Create package
  - services/retry/retry_daemon.py - Implement RetryDaemon class
- **Success**:
  - RetryDaemon class with __init__, run, _process_dlq, _get_routing_key methods
  - Processes bot_events.dlq and notification_queue.dlq every retry_interval_seconds
  - Extracts routing key from x-death header for republishing
  - Uses SyncPublisher for message republishing
  - ACKs messages after successful republish, NACKs on failure
  - Includes OpenTelemetry tracing
  - Handles empty queues gracefully
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 673-802) - Complete retry service implementation code
- **Dependencies**: Phase 2 completion (per-queue DLQs exist)

### Task 3.2: Create retry_daemon_wrapper.py entry point

Create wrapper script with signal handling and configuration loading.

- **Files**:
  - services/retry/retry_daemon_wrapper.py - Entry point for containerized deployment
- **Success**:
  - Loads RABBITMQ_URL from environment
  - Loads RETRY_INTERVAL_SECONDS from environment (default 900)
  - Implements signal handlers for SIGTERM/SIGINT
  - Creates RetryDaemon instance and calls run()
  - Includes proper shutdown handling
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 804-821) - Wrapper implementation pattern
- **Dependencies**: Task 3.1 completion

### Task 3.3: Create retry.Dockerfile

Create Dockerfile for building retry service container.

- **Files**:
  - docker/retry.Dockerfile - Container build configuration
- **Success**:
  - Uses python:3.11-slim base image
  - Installs dependencies from pyproject.toml
  - Copies shared/ and services/retry/ directories
  - Sets CMD to run retry_daemon_wrapper.py
  - Follows multi-stage build pattern if needed
  - Includes health check if appropriate
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 823-839) - Dockerfile specification
  - #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices
- **Dependencies**: Task 3.2 completion

### Task 3.4: Add retry-daemon service to docker-compose.base.yml

Add retry service definition to base compose file for all environments.

- **Files**:
  - docker-compose.base.yml - Add retry-daemon service
- **Success**:
  - retry-daemon service uses docker/retry.Dockerfile
  - Depends on rabbitmq service
  - Mounts shared/ for development
  - Sets RABBITMQ_URL and RETRY_INTERVAL_SECONDS env vars
  - Includes restart policy (unless-stopped)
  - Connected to app-network
  - Includes OpenTelemetry configuration
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 841-857) - Docker Compose service specification
- **Dependencies**: Task 3.3 completion

### Task 3.5: Add retry-daemon to test compose files

Add retry-daemon dependency to integration and e2e test configurations.

- **Files**:
  - docker-compose.test.yml - Add retry-daemon dependency to e2e-tests
  - docker-compose.integration.yml - Ensure retry-daemon starts for integration tests
- **Success**:
  - e2e-tests depends on retry-daemon in docker-compose.test.yml
  - retry-daemon starts with integration tests
  - Tests can verify DLQ processing behavior
- **Research References**:
  - Existing daemon dependencies in test compose files
- **Dependencies**: Task 3.4 completion

### Task 3.6: Add observability configuration for retry-daemon

Add Grafana Alloy scraping configuration for retry-daemon metrics if exposed.

- **Files**:
  - grafana-alloy/config.alloy - Add retry-daemon to service list if implementing metrics
- **Success**:
  - Retry-daemon traces appear in Grafana Cloud (already configured via OTEL)
  - Logs are collected via OTEL exporter
  - If metrics endpoint added later, scraping config is ready
- **Research References**:
  - Existing OTEL configuration in docker-compose.base.yml
  - grafana-alloy/config.alloy patterns for other services
- **Dependencies**: Task 3.4 completion

### Task 3.7: Create integration tests for retry daemon

Create comprehensive integration tests for DLQ retry functionality.

- **Files**:
  - tests/integration/test_retry_daemon.py - Integration tests for retry service
- **Success**:
  - Test message enters DLQ via TTL expiry
  - Test retry daemon republishes message to primary queue
  - Test routing key preservation from x-death header
  - Test both bot_events.dlq and notification_queue.dlq processing
  - Test retry interval configuration
  - Test error handling (NACK on republish failure)
  - All tests pass
- **Research References**:
  - tests/integration/test_notification_daemon.py - Pattern for daemon integration tests
  - tests/integration/test_rabbitmq_infrastructure.py - RabbitMQ test patterns
- **Dependencies**: Task 3.4 completion

## Phase 4: Remove DLQ Processing from Scheduler Daemons

### Task 4.1: Remove process_dlq parameter from notification_daemon_wrapper.py

Set process_dlq=False and remove dlq_check_interval parameter from notification daemon.

- **Files**:
  - services/scheduler/notification_daemon_wrapper.py - Update daemon configuration
- **Success**:
  - process_dlq parameter set to False
  - dlq_check_interval parameter removed
  - Daemon still starts and processes notifications correctly
  - No errors in daemon logs about DLQ processing
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 86-175) - Root cause analysis (duplicate processing)
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 859-873) - Daemon configuration changes
- **Dependencies**: Phase 3 completion (retry service ready)

### Task 4.2: Remove process_dlq parameter from status_transition_daemon_wrapper.py

Set process_dlq=False and remove dlq_check_interval parameter from status transition daemon.

- **Files**:
  - services/scheduler/status_transition_daemon_wrapper.py - Update daemon configuration
- **Success**:
  - process_dlq parameter set to False
  - dlq_check_interval parameter removed
  - Daemon still starts and processes status transitions correctly
  - No errors in daemon logs about DLQ processing
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 86-175) - Root cause analysis (duplicate processing)
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 859-873) - Daemon configuration changes
- **Dependencies**: Task 4.1 completion

### Task 4.3: Remove DLQ processing code from generic_scheduler_daemon.py

Remove _process_dlq_messages method, process_dlq parameter, dlq_check_interval parameter, and last_dlq_check tracking.

- **Files**:
  - services/scheduler/generic_scheduler_daemon.py - Remove DLQ processing logic
- **Success**:
  - process_dlq and dlq_check_interval parameters removed from __init__
  - last_dlq_check instance variable removed
  - _process_dlq_messages method completely removed (~80 lines)
  - DLQ check logic removed from run() method
  - Docstrings updated to reflect removal
  - No pika imports if only used for DLQ processing
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 250-348) - Current DLQ processing implementation to remove
- **Dependencies**: Task 4.2 completion (both wrappers updated)

### Task 4.4: Update daemon tests to remove DLQ expectations

Remove or update tests that verify DLQ processing behavior in daemons.

- **Files**:
  - tests/services/scheduler/ - Update daemon tests
- **Success**:
  - Tests no longer expect daemons to process DLQ
  - Tests no longer mock/verify _process_dlq_messages calls
  - All daemon tests pass
  - No test references to process_dlq or dlq_check_interval parameters
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 859-892) - Implementation tasks for daemon cleanup
- **Dependencies**: Task 4.3 completion

## Phase 5: Testing and Validation

### Task 5.1: Write unit tests for RetryDaemon class

Create comprehensive unit tests for retry service logic.

- **Files**:
  - tests/services/retry/__init__.py - Create test package
  - tests/services/retry/test_retry_daemon.py - Unit tests for RetryDaemon
- **Success**:
  - Test _process_dlq with mock publisher
  - Test _get_routing_key extraction from x-death header
  - Test error handling when republish fails
  - Test empty queue handling (no messages)
  - Test multiple messages in DLQ
  - All tests pass with 100% coverage of retry_daemon.py
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 894-922) - Testing strategy specification
  - #file:../../.github/instructions/python.instructions.md - Python testing conventions
- **Dependencies**: Phase 4 completion

### Task 5.2: Write integration tests for DLQ retry flow

Create integration tests verifying end-to-end DLQ processing.

- **Files**:
  - tests/integration/test_retry_daemon_integration.py - Integration tests
- **Success**:
  - Test message enters DLQ via TTL expiry
  - Test retry service republishes message to primary queue
  - Test bot successfully processes republished message
  - Test retry service handles both bot_events.dlq and notification_queue.dlq
  - Test retry interval is configurable
  - All integration tests pass
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 894-922) - Integration test requirements
- **Dependencies**: Task 5.1 completion

### Task 5.3: Verify all existing tests pass with new architecture

Run full test suite to ensure no regressions.

- **Files**:
  - All test files across test suite
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - All e2e tests pass
  - No test failures related to queue changes
  - No test failures related to DLQ processing removal
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 894-922) - Testing and validation phase
- **Dependencies**: Task 5.2 completion

## Phase 6: Documentation and Cleanup

### Task 6.1: Update RUNTIME_CONFIG.md with retry service documentation

Document retry service configuration, behavior, and monitoring.

- **Files**:
  - RUNTIME_CONFIG.md - Add retry service section
- **Success**:
  - Documents retry service purpose (DLQ processing)
  - Lists environment variables (RETRY_INTERVAL_SECONDS)
  - Explains per-queue DLQ architecture
  - Provides troubleshooting guidance
  - Includes monitoring recommendations
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 924-962) - Documentation requirements
- **Dependencies**: Phase 5 completion

### Task 6.2: Add DLQ monitoring guidance

Document how to monitor DLQ depth and configure alerts.

- **Files**:
  - RUNTIME_CONFIG.md - Add DLQ monitoring section
  - grafana-alloy/config.alloy - Add DLQ metrics if not present
- **Success**:
  - Documents how to check DLQ depth via RabbitMQ UI or CLI
  - Provides alert threshold recommendations (e.g., >10 messages)
  - Explains what DLQ growth indicates (bot downtime, processing failures)
  - Includes manual recovery procedure
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 924-962) - Monitoring and documentation phase
- **Dependencies**: Task 6.1 completion

### Task 6.3: Document migration steps for existing deployments

Create migration guide for updating existing production systems.

- **Files**:
  - DEPLOYMENT_QUICKSTART.md or new MIGRATION.md - Migration procedure
- **Success**:
  - Documents steps to drain existing shared DLQ
  - Explains how to deploy retry service
  - Lists environment variables to set
  - Provides rollback procedure if issues occur
  - Includes verification steps post-migration
- **Research References**:
  - #file:../research/20251211-dlq-exponential-growth-analysis.md (Lines 924-962) - Migration documentation needs
- **Dependencies**: Task 6.2 completion

## Success Criteria

- DLQ message count remains stable (no exponential growth)
- Retry service successfully republishes messages from both DLQs
- notification_daemon and status_transition_daemon no longer process DLQs
- All unit and integration tests pass
- Unused queues removed from RabbitMQ (api_events, scheduler_events)
- Retry service processes DLQs with configurable interval
- No duplicate message processing observed
- Documentation complete and accurate
