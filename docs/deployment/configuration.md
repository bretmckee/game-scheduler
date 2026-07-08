# Runtime Configuration

The application supports runtime configuration for multiple services, allowing
you to change settings without rebuilding Docker images.

## Frontend Runtime Configuration

### How It Works

1. At container startup, the frontend entrypoint script
   (`docker/frontend-entrypoint.sh`) reads the `BACKEND_URL` environment variable
2. It generates `/usr/share/nginx/html/config.js` by substituting the value into
   the template
3. The frontend loads this config file before the React app starts
4. The app uses the runtime configuration instead of build-time values

## Configuration

### When to Use Each Mode

**Use Proxy Mode (BACKEND_URL set to same domain) when:**

- Frontend and API are accessed through the same hostname/IP
- Using the provided nginx proxy configuration (default docker-compose setup)
- You want maximum flexibility (works with any hostname: localhost, IP, domain)
- Both services are in the same Docker network

**Use Direct API Access (BACKEND_URL set to different domain) when:**

- API is on a completely different domain/server than the frontend
- Example: Frontend at `https://game-scheduler.example.com`, API at
  `https://api.example.com`
- You need to bypass the nginx proxy for some reason

### For Proxy Mode (Recommended for Standard Deployment)

Set `BACKEND_URL` to the same domain as frontend in your `.env` file:

```bash
BACKEND_URL=https://your-domain.com
```

**How it works:**

1. User accesses: `http://your-server:3000`
2. Frontend makes requests to: `/api/v1/auth/user` (relative URL)
3. Nginx proxies to: `http://api:8000/api/v1/auth/user` (internal Docker
   network)

This works whether users access via `localhost`, `192.168.1.100`, or any domain
name.

### For Direct API Access

Set `BACKEND_URL` to your backend's full URL:

```bash
# Local development (if not using docker-compose)
BACKEND_URL=http://localhost:8000

# Production with separate API domain
BACKEND_URL=https://api.example.com

# Production with separate API server
BACKEND_URL=http://192.168.1.100:8000
```

**Note:** In the standard docker-compose deployment, port 8000 is exposed, but
using direct access is less flexible than proxy mode.

## Changing Configuration

To change the backend URL on a running system:

1. Update the `BACKEND_URL` value in your `.env` file
2. Restart only the frontend container:
   ```bash
   docker compose restart frontend
   ```

No rebuild required! The new configuration takes effect immediately.

## Development

During local development with `npm run dev`, the frontend uses:

1. `VITE_API_URL` environment variable (if set)
2. Vite proxy configuration (in `vite.config.ts`)

## OpenTelemetry and Observability Configuration

### Overview

The application uses OpenTelemetry for distributed tracing, metrics collection,
and log aggregation. Telemetry data is collected by Grafana Alloy and forwarded
to Grafana Cloud for visualization and analysis.

### How It Works

1. All Python services (API, bot) are instrumented with OpenTelemetry
   SDKs
2. Services send traces, metrics, and logs to Grafana Alloy via OTLP (ports 4317
   gRPC, 4318 HTTP)
3. Grafana Alloy batches and forwards telemetry to Grafana Cloud
4. Infrastructure metrics (PostgreSQL, Redis) are collected by Alloy exporters
5. All telemetry is visualized in Grafana Cloud dashboards

### Configuration

#### Required Environment Variables

Set these in your `.env` file (see `config/template/env.template` for template):

```bash
# Grafana Cloud Tempo Instance ID (7-digit number)
# Found in: Grafana Cloud Portal → Connections → Tempo
# Used for: Direct trace ingestion to Tempo via OTLP
GRAFANA_CLOUD_TEMPO_INSTANCE_ID=1234567

# Grafana Cloud Prometheus Instance ID (7-digit number)
# Found in: Grafana Cloud Portal → Connections → Prometheus
# Used for: Infrastructure metrics via Prometheus remote_write
# IMPORTANT: This is DIFFERENT from OTLP instance ID!
GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID=2345678

# Grafana Cloud Loki Instance ID (7-digit number)
# Found in: Grafana Cloud Portal → Connections → Loki
# Used for: Log aggregation via Loki push API
# IMPORTANT: This is DIFFERENT from OTLP and Prometheus IDs!
GRAFANA_CLOUD_LOKI_INSTANCE_ID=3456789

# Grafana Cloud API Key (format: glc_xxxxx...)
# Generated from: Security → API Keys
# Required permissions: Metrics Write, Logs Write, Traces Write
# NOTE: Same API key works across all services
GRAFANA_CLOUD_API_KEY=glc_your_api_key_here

# Grafana Cloud Tempo Endpoint (gRPC with TLS on port 443)
# Format: tempo-prod-{number}-prod-{region}.grafana.net:443
GRAFANA_CLOUD_TEMPO_ENDPOINT=tempo-prod-15-prod-us-west-0.grafana.net:443

# Grafana Cloud Prometheus endpoint (WITH https:// prefix)
# Used for infrastructure metrics
GRAFANA_CLOUD_PROMETHEUS_ENDPOINT=https://prometheus-prod-36-prod-us-west-0.grafana.net/api/prom/push
```

#### Optional Port Configuration

```bash
# Alloy OTLP receiver ports (defaults shown)
ALLOY_OTLP_GRPC_PORT=4317
ALLOY_OTLP_HTTP_PORT=4318
```

### Setup Instructions

For detailed step-by-step instructions on setting up Grafana Cloud and obtaining
credentials, see:

- `config/grafana-alloy/SETUP_GRAFANA_CLOUD.md` - Complete setup guide

### Architecture

**Telemetry Flow:**

```
Application Services → Grafana Alloy → Grafana Cloud
     (OTLP)              (Batching)     (Visualization)
```

**Services Instrumented:**

- `api` - FastAPI REST API with HTTP, database, Redis spans
- `bot` - Discord bot with command, event, and scheduler spans

**Infrastructure Metrics:**

- PostgreSQL - Connection counts, query performance, database size
- Redis - Memory usage, command rates, key counts

### Grafana Cloud Free Tier Limits

- **Traces:** 50 GB/month (14-day retention)
- **Logs:** 50 GB/month (14-day retention)
- **Metrics:** 10,000 active series (13-month retention)

### Disabling Observability

To run without OpenTelemetry (e.g., local development without Grafana Cloud):

1. Stop the Alloy service:

   ```bash
   docker compose stop grafana-alloy
   ```

2. Services will continue to work normally, but telemetry won't be collected

**Note:** The application is designed to work with or without observability
configured.

### Troubleshooting

**Alloy authentication errors:**

- Verify you're using the correct instance ID for each service:
  - `GRAFANA_CLOUD_TEMPO_INSTANCE_ID` for Tempo (get from Connections → Tempo)
  - `GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID` for Prometheus remote_write
  - `GRAFANA_CLOUD_LOKI_INSTANCE_ID` for Loki log forwarding
- Confirm API key has Metrics/Logs/Traces write permissions

**No traces appearing in Grafana Cloud:**

- Check Alloy logs: `docker compose logs grafana-alloy`
- Verify services are configured with `OTEL_EXPORTER_OTLP_ENDPOINT` pointing to
  Alloy
- Ensure Alloy container is running and healthy

**Multiple instance ID confusion:**

- Grafana Cloud uses THREE DIFFERENT instance IDs:
  - **OTLP Instance ID**: For OTLP Gateway (application telemetry)
  - **Prometheus Instance ID**: For Prometheus remote_write (infrastructure
    metrics)
  - **Loki Instance ID**: For Loki push API (log aggregation)
- Always use the correct instance ID for each integration
- The same API key works across all three services

For more troubleshooting guidance, see the research document:
`.copilot-tracking/research/20251206-opentelemetry-compatibility-research.md`
(Lines 1050-1200)
