<!-- markdownlint-disable-file -->
# Task Research Notes: Init Container Sleep Pattern

## Research Executed

### File Analysis
- [compose.yaml](compose.yaml)
  - Init service uses `restart: "no"` policy
  - Dependent services use `condition: service_completed_successfully`
  - Bot, API, notification-daemon, status-transition-daemon, retry all depend on init
- [docker/init.Dockerfile](docker/init.Dockerfile)
  - Uses Python entrypoint, runs services/init/main.py
  - No existing healthcheck defined
- [services/init/main.py](services/init/main.py)
  - Runs 5 initialization steps sequentially
  - Returns exit code 0 on success, 1 on failure
  - Uses OpenTelemetry instrumentation

### External Research
- #fetch:https://docs.docker.com/compose/startup-order/
  - `service_completed_successfully` waits for container exit code 0
  - `service_healthy` waits for healthcheck to pass
  - Dependent services restart when dependency is restarted
- #fetch:https://docs.docker.com/reference/compose-file/services/#healthcheck
  - Healthcheck can use test commands to verify service readiness
  - Support for `disable: true` to disable healthchecks
  - Interval, timeout, retries, start_period configuration

## Key Discoveries

### Current Behavior Problem
The init container exits after successful initialization, triggering re-runs when:
- Any dependent service is restarted (bot, API, daemons)
- Docker Compose recreates containers
- Manual service restarts occur

This is inefficient as initialization should only run once per environment lifecycle.

### Docker Compose Dependency Patterns
Docker Compose provides three dependency conditions:
1. `service_started` - Service container is running
2. `service_healthy` - Healthcheck passes (for long-running services)
3. `service_completed_successfully` - Container exits with code 0 (for init containers)

### Sleep Pattern Architecture
Converting init to a long-running service requires:
1. Touch a completion marker file after initialization
2. Sleep indefinitely after successful init
3. Healthcheck verifies marker file exists
4. Change `restart: "no"` to `restart: unless-stopped`
5. Change dependent services from `service_completed_successfully` to `service_healthy`

## Recommended Approach

### Implementation Strategy

**Phase 1: Modify Init Service Logic**
- After successful initialization, touch `/tmp/init-complete` marker file
- Replace `return 0` with infinite sleep: `import time; time.sleep(float('inf'))`
- On error, skip marker file and exit with code 1 (preserves failure detection)

**Phase 2: Add Healthcheck**
```yaml
healthcheck:
  test: ["CMD", "test", "-f", "/tmp/init-complete"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 120s  # Allow 2 minutes for initialization
```

**Phase 3: Update Compose Configuration**
- Change init service: `restart: unless-stopped`
- Update all dependent services dependency from:
  ```yaml
  init:
    condition: service_completed_successfully
  ```
  to:
  ```yaml
  init:
    condition: service_healthy
  ```

### Complete Example

**[services/init/main.py](services/init/main.py) modification:**
```python
def main() -> int:
    init_telemetry("init-service")
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("init.environment") as span:
        try:
            # ... existing initialization steps ...

            span.set_status(trace.Status(trace.StatusCode.OK))
            logger.info("=" * 60)
            logger.info("Environment Initialization Complete")
            logger.info("=" * 60)

            # Create marker file to indicate completion
            marker_file = Path("/tmp/init-complete")
            marker_file.touch()
            logger.info(f"Created completion marker: {marker_file}")

            # Sleep indefinitely to keep container running
            logger.info("Entering sleep mode. Container will remain healthy.")
            import time
            time.sleep(float('inf'))

        except Exception as e:
            logger.error("Initialization Failed")
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            return 1
        finally:
            flush_telemetry()
```

**[compose.yaml](compose.yaml) init service:**
```yaml
init:
  build:
    context: .
    dockerfile: docker/init.Dockerfile
  image: ${IMAGE_REGISTRY:-}game-scheduler-init:${IMAGE_TAG:-latest}
  container_name: ${CONTAINER_PREFIX:-gamebot}-init
  environment:
    DATABASE_URL: ${DATABASE_URL}
    POSTGRES_HOST: postgres
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
    RABBITMQ_URL: ${RABBITMQ_URL}
    OTEL_SERVICE_NAME: init-service
    OTEL_EXPORTER_OTLP_ENDPOINT: http://grafana-alloy:4318
    OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
    OTEL_TRACES_EXPORTER: otlp
    OTEL_METRICS_EXPORTER: otlp
    OTEL_LOGS_EXPORTER: otlp
  depends_on:
    postgres:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
    grafana-alloy:
      condition: service_started
  healthcheck:
    test: ["CMD", "test", "-f", "/tmp/init-complete"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 120s
  restart: unless-stopped
  networks:
    - app-network
  logging: *logging-default
  labels:
    service: "init"
    environment: "${ENVIRONMENT:-production}"
```

**Dependent services (bot, api, notification-daemon, etc.):**
```yaml
depends_on:
  init:
    condition: service_healthy  # Changed from service_completed_successfully
  grafana-alloy:
    condition: service_started
```

## Implementation Guidance

**Objectives:**
1. Prevent unnecessary re-initialization when services restart
2. Maintain clear initialization success/failure signaling
3. Enable healthcheck-based dependency management
4. Preserve observability through logging and telemetry

**Key Tasks:**
1. Modify [services/init/main.py](services/init/main.py) to touch marker file and sleep indefinitely
2. Add healthcheck to init service in [compose.yaml](compose.yaml)
3. Change init restart policy to `unless-stopped`
4. Update all dependent services to use `service_healthy` condition
5. Verify in compose.override.yaml, compose.e2e.yaml, compose.int.yaml if overrides exist

**Dependencies:**
- No external library changes required
- Python `pathlib.Path` for marker file (already in stdlib)
- Docker Compose healthcheck support (standard feature)

**Success Criteria:**
- Init container remains running after initialization
- Dependent services start only after healthcheck passes
- Restarting dependent services does NOT trigger init re-run
- Init failure still prevents dependent services from starting
- Marker file visible for debugging: `docker exec <init-container> test -f /tmp/init-complete && echo "Initialized" || echo "Not initialized"`

**Benefits:**
1. **Efficiency**: Initialization runs once per environment lifecycle
2. **Consistency**: Clear healthcheck pattern matches other services
3. **Debugging**: Marker file provides explicit initialization state
4. **Reliability**: Sleep pattern is standard for initialization containers
5. **Backward Compatible**: Failure behavior unchanged (exit 1 on error)

**Considerations:**
1. **Container Restart**: If init container itself restarts, it will re-run initialization
   - This is correct behavior - initialization should re-run if init crashes
2. **Marker File Location**: Using `/tmp/` is standard for ephemeral state
   - Consider `/app/.initialized` if you want it visible in volume mounts
3. **Sleep Implementation**: `time.sleep(float('inf'))` is Pythonic and standard
   - Alternative: `while True: time.sleep(86400)` for daily wakeup logging
4. **Healthcheck Timing**: `start_period: 120s` allows generous init time
   - Adjust based on actual initialization duration in your environment
5. **Multiple Compose Files**: Verify compose.override.yaml doesn't override init definition

## Alternative Approaches Considered

### Alternative 1: Shell Script Sleep
Touch file and exec sleep in entrypoint script instead of Python code.
- **Rejected**: Less observable, harder to integrate with OpenTelemetry, breaks existing logging patterns

### Alternative 2: Keep Current Pattern (No Change)
Accept re-initialization on service restarts.
- **Rejected**: Wasteful, causes delays, triggers unnecessary database/rabbitmq operations

### Alternative 3: External State Management
Check external state (database flag) to skip initialization if already complete.
- **Rejected**: Complex, adds database dependency to init logic, harder to debug, doesn't solve core problem
