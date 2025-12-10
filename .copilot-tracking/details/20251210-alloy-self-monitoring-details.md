<!-- markdownlint-disable-file -->

# Task Details: Grafana Alloy Self-Monitoring

## Research Reference

**Source Research**: #file:../research/20251210-alloy-self-monitoring-research.md

## Phase 1: Add Alloy Metrics Self-Monitoring

### Task 1.1: Add prometheus.exporter.self component

Add the self-exporter component to expose Alloy's internal metrics for scraping.

- **Files**:
  - `grafana-alloy/config.alloy` - Add prometheus.exporter.self component after RabbitMQ scraping section
- **Success**:
  - Component exports metrics targets for scraping
  - No configuration errors in Alloy startup logs
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 36-49) - Metrics collection architecture
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 51-64) - prometheus.exporter.self component example
- **Dependencies**:
  - None - self-exporter is built-in to Alloy

### Task 1.2: Configure prometheus.scrape for Alloy metrics

Create scrape job to collect metrics from the self-exporter at 60s intervals.

- **Files**:
  - `grafana-alloy/config.alloy` - Add prometheus.scrape block after prometheus.exporter.self
- **Success**:
  - Scrape job collects metrics every 60 seconds
  - Metrics forwarded to prometheus receiver for conversion
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 51-64) - Complete metrics collection pipeline
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 149-171) - Complete self-monitoring example
- **Dependencies**:
  - Task 1.1 completion (prometheus.exporter.self must exist)

### Task 1.3: Add otelcol.receiver.prometheus for metrics conversion

Convert Prometheus metrics to OTLP format for export to Grafana Cloud.

- **Files**:
  - `grafana-alloy/config.alloy` - Add otelcol.receiver.prometheus block after scrape configuration
- **Success**:
  - Prometheus metrics converted to OTLP format
  - Metrics forwarded to existing grafana_cloud_otlp exporter
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 51-64) - Metrics conversion to OTLP
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 149-171) - Complete configuration example
- **Dependencies**:
  - Task 1.2 completion (prometheus.scrape must forward to receiver)
  - Existing otelcol.exporter.otlphttp.grafana_cloud_otlp component

## Phase 2: Enable Alloy Logs Export

### Task 2.1: Configure logging block for Loki export

Replace the existing logging block to enable JSON format and Loki forwarding.

- **Files**:
  - `grafana-alloy/config.alloy` - Update logging block at top of file
- **Success**:
  - Logging level set to "info"
  - Format changed to "json" for structured parsing
  - Logs forwarded to loki.write component
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 68-85) - Logs collection configuration
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 155-163) - Complete logging example
- **Dependencies**:
  - Task 2.2 must be implemented simultaneously (loki.write component required)

### Task 2.2: Add loki.write component for Grafana Cloud

Create Loki write endpoint with authentication for log export.

- **Files**:
  - `grafana-alloy/config.alloy` - Add loki.write block after logging configuration
- **Success**:
  - Loki endpoint configured with proper authentication
  - Environment variables used for credentials
  - Logs successfully exported to Grafana Cloud
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 68-85) - Loki write configuration
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 173-184) - Required environment variables
- **Dependencies**:
  - Task 2.3 completion (environment variables must be defined)

### Task 2.3: Add Loki environment variables to docker-compose

Add required Loki endpoint and authentication environment variables.

- **Files**:
  - `docker-compose.base.yml` - Add GRAFANA_CLOUD_LOKI_* variables to alloy service environment section
- **Success**:
  - GRAFANA_CLOUD_LOKI_ENDPOINT environment variable added
  - GRAFANA_CLOUD_LOKI_INSTANCE_ID environment variable added
  - Variables follow same pattern as existing OTLP variables
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 173-184) - Complete environment variable list
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 76-84) - Loki authentication requirements
- **Dependencies**:
  - None - can be added independently

## Phase 3: Enable Alloy Trace Sampling

### Task 3.1: Add tracing block with sampling configuration

Enable trace collection with 10% sampling for Alloy internal operations.

- **Files**:
  - `grafana-alloy/config.alloy` - Add tracing block after logging/loki configuration
- **Success**:
  - Tracing enabled with 10% sampling (0.1 fraction)
  - Traces forwarded to existing OTLP exporter
  - Minimal performance overhead (<5% CPU)
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 89-106) - Traces collection configuration
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 165-169) - Tracing block example
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 280-289) - Resource impact of trace collection
- **Dependencies**:
  - Existing otelcol.exporter.otlphttp.grafana_cloud_otlp component

## Phase 4: Documentation and Validation

### Task 4.1: Update Alloy configuration comments

Add comprehensive comments documenting self-monitoring architecture.

- **Files**:
  - `grafana-alloy/config.alloy` - Update header comments to document self-monitoring
- **Success**:
  - Architecture comments clearly explain self-monitoring signals
  - Each self-monitoring section has explanatory comments
  - Comments distinguish between application and Alloy telemetry
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 1-10) - Research overview and architecture
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 187-201) - Benefits of self-monitoring
- **Dependencies**:
  - All previous phases completed

### Task 4.2: Document required environment variables

Create or update documentation listing all required Grafana Cloud variables.

- **Files**:
  - `grafana-alloy/SETUP_GRAFANA_CLOUD.md` - Update with Loki-specific variables if file exists
  - `RUNTIME_CONFIG.md` - Add Loki environment variables to runtime configuration documentation
- **Success**:
  - All Loki variables documented with descriptions
  - Example values provided for Grafana Cloud endpoints
  - Clear distinction between OTLP and Loki authentication
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 173-184) - Complete environment variable reference
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 76-84) - Loki endpoint format
- **Dependencies**:
  - Phase 2 completion (Loki configuration implemented)

### Task 4.3: Verify Alloy self-monitoring in Grafana Cloud

Test and validate that all three signals are flowing to Grafana Cloud.

- **Files**:
  - No file changes - validation only
- **Success**:
  - Metrics query `{job="integrations/alloy"}` returns data in Grafana Cloud Explore (Mimir)
  - Logs query `{service_name="alloy"}` returns JSON-formatted logs in Grafana Cloud Explore (Loki)
  - Traces query with service.name="alloy" filter shows spans in Grafana Cloud Explore (Tempo)
  - Resource usage remains below 5% CPU and 20MB memory overhead
- **Research References**:
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 246-260) - Grafana Cloud dashboard recommendations
  - #file:../research/20251210-alloy-self-monitoring-research.md (Lines 264-277) - Recommended approach and resource impact
- **Dependencies**:
  - All previous phases completed
  - Grafana Cloud credentials properly configured
  - Alloy container running with updated configuration

## Dependencies

- Grafana Cloud account with OTLP Gateway and Loki endpoints configured
- Existing Grafana Alloy deployment running in Docker

## Success Criteria

- All three telemetry signals (metrics, logs, traces) flowing from Alloy to Grafana Cloud
- No configuration errors in Alloy startup logs
- Resource overhead remains minimal (<5% CPU, <20MB memory)
- Documentation updated with clear setup instructions
