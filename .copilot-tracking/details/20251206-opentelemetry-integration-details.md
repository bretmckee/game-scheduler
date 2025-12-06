<!-- markdownlint-disable-file -->
# Task Details: OpenTelemetry Integration

## Research Reference

**Source Research**: #file:../research/20251206-opentelemetry-compatibility-research.md

## Phase 1: Python Dependencies and Base Configuration

### Task 1.1: Add OpenTelemetry Python packages to pyproject.toml

Add OpenTelemetry SDK and instrumentation libraries to project dependencies.

- **Files**:
  - `pyproject.toml` - Add to [project.dependencies] section
- **Success**:
  - All required OpenTelemetry packages added to dependencies
  - `uv sync` completes without errors
  - Package versions compatible with Python 3.13
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 214-225) - Recommended packages list
  - #fetch:"https://opentelemetry.io/docs/languages/python/libraries/" - Python instrumentation libraries
- **Dependencies**:
  - None (foundational task)
- **Packages to Add**:
  - `opentelemetry-api>=1.28.2`
  - `opentelemetry-sdk>=1.28.2`
  - `opentelemetry-instrumentation-fastapi>=0.49b2`
  - `opentelemetry-instrumentation-sqlalchemy>=0.49b2`
  - `opentelemetry-instrumentation-asyncpg>=0.49b2`
  - `opentelemetry-instrumentation-redis>=0.49b2`
  - `opentelemetry-instrumentation-aio-pika>=0.49b2`
  - `opentelemetry-exporter-otlp>=1.28.2`

### Task 1.2: Create shared OpenTelemetry initialization module

Create a reusable module for initializing OpenTelemetry tracing and metrics across all services.

- **Files**:
  - `shared/telemetry.py` - New file for OpenTelemetry initialization
- **Success**:
  - Module provides `init_telemetry(service_name: str)` function
  - Configures TracerProvider with BatchSpanProcessor
  - Configures MeterProvider for metrics
  - Reads OTLP endpoint from environment variables
  - Handles graceful degradation if OTel endpoint unavailable
  - Includes proper error handling and logging
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 147-165) - Manual instrumentation pattern
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 227-245) - Environment variables
- **Dependencies**:
  - Task 1.1 completion
- **Implementation Notes**:
  - Use environment variables: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`
  - Configure BatchSpanProcessor for efficient export
  - Add service.name resource attribute
  - Include SDK version and deployment environment attributes

### Task 1.3: Add OpenTelemetry environment variables to .env.example

Document required OpenTelemetry configuration in example environment file.

- **Files**:
  - `.env.example` - Add OTel configuration section
- **Success**:
  - All required OTel environment variables documented
  - Clear comments explain purpose of each variable
  - Default values appropriate for local development
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 227-245) - Environment variables list
- **Dependencies**:
  - None (documentation task)
- **Variables to Add**:
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://grafana-alloy:4318`
  - `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`
  - `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true`
  - Service-specific names set in docker-compose

## Phase 2: Service Instrumentation

### Task 2.1: Instrument FastAPI service (services/api)

Add automatic and manual instrumentation to the FastAPI API service.

- **Files**:
  - `services/api/main.py` - Import and initialize telemetry
  - `services/api/dependencies/permissions.py` - Add manual spans for auth checks
  - `services/api/routes/*.py` - Add manual spans for business logic operations
- **Success**:
  - FastAPI automatically creates spans for all HTTP requests
  - SQLAlchemy queries create child spans with SQL visible
  - Redis operations create child spans
  - Manual spans added for game creation, scheduling, and notification operations
  - Span attributes include user_id, guild_id, game_id where applicable
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 75-82) - FastAPI instrumentation
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 147-165) - Manual instrumentation pattern
- **Dependencies**:
  - Phase 1 completion
- **Implementation Steps**:
  1. Import `FastAPIInstrumentor` from `opentelemetry.instrumentation.fastapi`
  2. Call `FastAPIInstrumentor().instrument_app(app)` after app creation
  3. Initialize shared telemetry module: `init_telemetry("api-service")`
  4. Add manual spans in route handlers for business logic
  5. Set span attributes for important context (game_id, user_id, etc.)

### Task 2.2: Instrument Discord Bot service (services/bot)

Add manual instrumentation to Discord bot commands and event handlers.

- **Files**:
  - `services/bot/main.py` - Initialize telemetry
  - `services/bot/cogs/*.py` - Add spans for command handlers
  - `services/bot/event_handlers/*.py` - Add spans for event processing
- **Success**:
  - Each bot command creates a root span
  - Event handlers create spans with Discord context
  - HTTP calls to API service propagate trace context
  - Span attributes include guild_id, channel_id, user_id, command_name
  - RabbitMQ message publishing creates spans
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 84-88) - discord.py manual instrumentation approach
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 147-165) - Manual instrumentation pattern
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 101-104) - aio-pika instrumentation
- **Dependencies**:
  - Phase 1 completion
- **Implementation Steps**:
  1. Initialize shared telemetry module: `init_telemetry("bot-service")`
  2. Create decorator for bot commands that creates spans
  3. Add trace context propagation to httpx client calls
  4. Instrument RabbitMQ publisher with aio-pika instrumentation
  5. Set Discord-specific span attributes (guild_id, channel_id, etc.)
  6. Handle span lifecycle for async command handlers

### Task 2.3: Instrument Notification Daemon

Add instrumentation to the notification scheduling daemon.

- **Files**:
  - `services/scheduler/notification_daemon.py` - Add telemetry initialization and spans
- **Success**:
  - Scheduled notification tasks create root spans
  - Database queries for pending notifications create child spans
  - RabbitMQ message publishing creates spans with queue/routing key
  - Span attributes include notification_id, game_id, scheduled_time
  - Errors are recorded in spans with exception details
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 90-95) - SQLAlchemy instrumentation
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 101-104) - aio-pika instrumentation
- **Dependencies**:
  - Phase 1 completion
- **Implementation Steps**:
  1. Initialize shared telemetry module: `init_telemetry("notification-daemon")`
  2. Create span for each notification check cycle
  3. Instrument RabbitMQ publisher with aio-pika instrumentation
  4. Add span attributes for notification context
  5. Record exceptions in spans before logging

### Task 2.4: Instrument Status Transition Daemon

Add instrumentation to the game status transition daemon.

- **Files**:
  - `services/scheduler/status_transition_daemon.py` - Add telemetry initialization and spans
- **Success**:
  - Status transition checks create root spans
  - Database queries create child spans
  - Status update operations create spans with old/new status
  - RabbitMQ event publishing creates spans
  - Span attributes include game_id, old_status, new_status, transition_time
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 90-95) - SQLAlchemy instrumentation
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 101-104) - aio-pika instrumentation
- **Dependencies**:
  - Phase 1 completion
- **Implementation Steps**:
  1. Initialize shared telemetry module: `init_telemetry("status-transition-daemon")`
  2. Create span for each status check cycle
  3. Add spans for individual game status transitions
  4. Instrument RabbitMQ publisher
  5. Set span attributes for transition context

## Phase 3: Infrastructure Telemetry Collection

### Task 3.1: Create OpenTelemetry Collector configuration

Create Alloy configuration file for receiving telemetry from services and infrastructure.

- **Files**:
  - `docker/alloy-config.alloy` - New Alloy configuration file
- **Success**:
  - OTLP receiver accepts gRPC and HTTP protocols
  - PostgreSQL receiver collects database metrics
  - Redis receiver collects cache metrics
  - Batch processor configured for efficient export
  - Memory limiter prevents resource exhaustion
  - Console exporter for local debugging
  - OTLP exporter for Grafana Cloud integration
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 167-208) - Collector pipeline configuration
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 247-265) - PostgreSQL receiver
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 267-276) - Redis receiver
- **Dependencies**:
  - None (configuration file)
- **Configuration Sections**:
  - `otelcol.receiver.otlp` - Accept OTLP from services
  - `otelcol.receiver.postgresql` - Query PostgreSQL stats
  - `otelcol.receiver.redis` - Query Redis INFO
  - `otelcol.processor.batch` - Batch telemetry for efficiency
  - `otelcol.processor.memory_limiter` - Prevent OOM
  - `otelcol.exporter.otlp` - Export to Grafana Cloud
  - `otelcol.exporter.debug` - Console logging for development

### Task 3.2: Add Grafana Alloy service to docker-compose

Add OpenTelemetry Collector service using Grafana Alloy distribution.

- **Files**:
  - `docker-compose.base.yml` - Add grafana-alloy service definition
  - `.env.example` - Add Grafana Cloud credentials placeholders
- **Success**:
  - Alloy service defined with appropriate resource limits
  - Configuration volume mounted from docker/alloy-config.alloy
  - OTLP ports (4317, 4318) exposed for service connections
  - Health check configured
  - Depends on postgres, redis for metrics collection
  - Environment variables for Grafana Cloud credentials
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 278-298) - Docker Compose service definition
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 593-605) - Alloy deployment configuration
- **Dependencies**:
  - Task 3.1 completion
- **Service Configuration**:
  - Image: `grafana/alloy:latest`
  - Ports: 4317 (gRPC), 4318 (HTTP), 12345 (Alloy API)
  - Resource limits: memory 512MB
  - Health check on Alloy API endpoint

### Task 3.3: Configure PostgreSQL metrics collection

Configure Alloy to collect PostgreSQL database metrics.

- **Files**:
  - `docker/alloy-config.alloy` - Add PostgreSQL receiver configuration
- **Success**:
  - Receiver connects to PostgreSQL using runtime credentials
  - Collects connection pool metrics (active, idle, max connections)
  - Collects query performance metrics (commits, rollbacks, blocks read/hit)
  - Collects table statistics (inserts, updates, deletes, seq/idx scans)
  - Metrics collected every 60 seconds
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 51-56) - PostgreSQL receiver capabilities
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 247-265) - PostgreSQL receiver config
- **Dependencies**:
  - Task 3.1, 3.2 completion
- **Configuration Details**:
  - Endpoint: `postgres:5432`
  - Database: from `${DATABASE_NAME}` env var
  - Username/password: from `${DATABASE_USER}`, `${DATABASE_PASSWORD}` env vars
  - Collection interval: 60s
  - TLS: disabled for internal Docker network

### Task 3.4: Configure Redis metrics collection

Configure Alloy to collect Redis cache metrics.

- **Files**:
  - `docker/alloy-config.alloy` - Add Redis receiver configuration
- **Success**:
  - Receiver connects to Redis
  - Collects memory usage metrics (used_memory, peak_memory)
  - Collects command statistics (commands processed, keyspace hits/misses)
  - Collects connection metrics (connected clients, blocked clients)
  - Metrics collected every 60 seconds
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 58-63) - Redis receiver capabilities
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 267-276) - Redis receiver config
- **Dependencies**:
  - Task 3.1, 3.2 completion
- **Configuration Details**:
  - Endpoint: `redis:6379`
  - Collection interval: 60s
  - TLS: disabled for internal Docker network

## Phase 4: Grafana Cloud Integration

### Task 4.1: Document Grafana Cloud setup process

Create documentation for setting up Grafana Cloud account and obtaining credentials.

- **Files**:
  - `docs/OBSERVABILITY.md` - New documentation file
- **Success**:
  - Step-by-step Grafana Cloud signup process documented
  - Instructions for obtaining API keys for Tempo, Loki, Prometheus
  - Environment variable configuration documented
  - Dashboard setup guidance provided
  - Free tier limits and usage monitoring explained
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 476-502) - Grafana Cloud overview
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 571-591) - Grafana Cloud setup steps
- **Dependencies**:
  - None (documentation task)
- **Documentation Sections**:
  1. Grafana Cloud account creation
  2. Obtaining OTLP endpoint URLs and credentials
  3. Setting environment variables
  4. Accessing telemetry in Grafana UI
  5. Pre-built dashboard installation
  6. Alert configuration examples

### Task 4.2: Create Alloy configuration for Grafana Cloud export

Configure Alloy to export telemetry to Grafana Cloud endpoints.

- **Files**:
  - `docker/alloy-config.alloy` - Add Grafana Cloud exporters
- **Success**:
  - OTLP exporter sends traces to Grafana Cloud Tempo
  - Prometheus remote_write exporter sends metrics to Grafana Cloud Mimir
  - Loki exporter sends logs to Grafana Cloud Loki
  - Authentication configured using instance ID and API key
  - Retry logic and batching configured for reliability
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 593-650) - Alloy Grafana Cloud configuration
- **Dependencies**:
  - Task 3.1, 3.2 completion
  - Grafana Cloud account created (Task 4.1)
- **Configuration Components**:
  - `otelcol.exporter.otlp` for Tempo traces
  - `prometheus.remote_write` for Mimir metrics
  - `loki.write` for Loki logs
  - `otelcol.auth.basic` for authentication
  - Environment variables: `GRAFANA_CLOUD_INSTANCE_ID`, `GRAFANA_CLOUD_API_KEY`, endpoint URLs

### Task 4.3: Update RUNTIME_CONFIG.md with OpenTelemetry documentation

Add comprehensive OpenTelemetry runtime configuration documentation to existing runtime config guide.

- **Files**:
  - `RUNTIME_CONFIG.md` - Add new OpenTelemetry section
- **Success**:
  - OpenTelemetry architecture explained
  - Service instrumentation approach documented
  - Alloy collector role and configuration described
  - Environment variable reference provided
  - Grafana Cloud integration explained
  - Troubleshooting guide included
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 117-146) - OpenTelemetry architecture
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 227-245) - Environment variables
- **Dependencies**:
  - Phase 1-3 completion
- **Documentation Sections**:
  - How OpenTelemetry works in the application
  - Configuration options and environment variables
  - Changing telemetry endpoints at runtime
  - Disabling telemetry for testing
  - Performance impact and mitigation

## Phase 5: Testing and Validation

### Task 5.1: Create integration tests for trace propagation

Write integration tests to verify trace context propagates correctly across service boundaries.

- **Files**:
  - `tests/integration/test_telemetry_propagation.py` - New test file
- **Success**:
  - Test verifies API HTTP request creates trace
  - Test verifies API -> database query creates child span
  - Test verifies API -> RabbitMQ publish propagates trace context
  - Test verifies bot receives trace context from RabbitMQ message
  - Test verifies daemon -> API HTTP call propagates trace context
  - All spans linked in same trace with correct parent-child relationships
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 147-165) - Manual instrumentation pattern
  - #githubRepo:"open-telemetry/opentelemetry-python testing" - Python OTel testing examples
- **Dependencies**:
  - Phase 1, 2 completion
- **Test Cases**:
  1. `test_api_request_creates_trace` - HTTP request to API endpoint
  2. `test_database_queries_are_child_spans` - Verify DB spans
  3. `test_rabbitmq_propagates_context` - Publish/consume trace linking
  4. `test_bot_command_creates_root_span` - Discord command span creation
  5. `test_daemon_http_call_propagates_trace` - Daemon to API tracing

### Task 5.2: Verify metrics collection from all infrastructure components

Create validation script to check metrics are being collected from PostgreSQL and Redis.

- **Files**:
  - `tests/integration/test_infrastructure_metrics.py` - New test file
- **Success**:
  - Test queries Alloy metrics endpoint
  - Verifies PostgreSQL metrics present (connections, queries, cache hits)
  - Verifies Redis metrics present (memory, commands, keyspace hits)
  - Validates metric labels include service name, instance
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 247-276) - PostgreSQL and Redis receivers
- **Dependencies**:
  - Phase 3 completion
- **Test Cases**:
  1. `test_postgresql_metrics_collected` - Query for DB metrics
  2. `test_redis_metrics_collected` - Query for cache metrics
  3. `test_metric_labels_present` - Verify proper labeling

### Task 5.3: Test log correlation with trace IDs

Verify logs include trace IDs for correlation with traces.

- **Files**:
  - `tests/integration/test_log_correlation.py` - New test file
- **Success**:
  - Test makes API request
  - Captures application logs
  - Verifies log entries include trace_id field
  - Verifies trace_id matches span trace_id
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 227-245) - Log auto-instrumentation config
- **Dependencies**:
  - Phase 2 completion
- **Test Cases**:
  1. `test_logs_include_trace_id` - Verify trace_id in log entries
  2. `test_trace_id_matches_span` - Correlation validation

### Task 5.4: Performance baseline and overhead measurement

Measure application performance with and without OpenTelemetry to verify <5% overhead target.

- **Files**:
  - `tests/performance/test_telemetry_overhead.py` - New test file
  - `docs/PERFORMANCE.md` - Document baseline and overhead measurements
- **Success**:
  - Baseline P50, P95, P99 latencies measured without OTel
  - Latencies measured with OTel enabled
  - Performance overhead documented
  - Overhead remains below 5% for P99 latency
  - Memory overhead measured and documented
- **Research References**:
  - #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 344-349) - Performance objectives
- **Dependencies**:
  - All previous phases completion
- **Test Scenarios**:
  1. API endpoint latency (GET /api/v1/games)
  2. API write latency (POST /api/v1/games)
  3. Database query performance
  4. RabbitMQ publish latency
  5. Memory usage baseline vs instrumented
