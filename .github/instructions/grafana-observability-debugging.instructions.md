---
description: 'How to find and query the correct Grafana Cloud stack when debugging via the grafana MCP server'
applyTo: '**'
---

# Grafana Observability Debugging

This project pushes telemetry (logs, metrics, traces) to **three separate Grafana Cloud stacks** —
one per environment. Picking the wrong stack silently produces plausible-looking but wrong data;
there is no error, just logs from the wrong bot instance.

## Known stacks

| env     | Grafana URL                                  | Loki instance ID | OTLP instance ID |
| ------- | -------------------------------------------- | ---------------- | ---------------- |
| dev     | `https://gamescheduler.grafana.net`          | 1419296          | 1461503          |
| staging | _(not yet documented — ask before assuming)_ | 1426352          | 1468559          |
| prod    | `https://gameschedulerprod.grafana.net`      | 1570477          | 3149604          |

Source of truth for instance IDs: `config/env.dev`, `config/env.staging`, `config/env.prod`
(`GRAFANA_CLOUD_LOKI_INSTANCE_ID`, `GRAFANA_CLOUD_OTLP_INSTANCE_ID`).

The active stack is configured in `.mcp.json` under `mcpServers.grafana.env.GRAFANA_URL`, with the
matching `GRAFANA_SERVICE_ACCOUNT_TOKEN` read from `~/.tokens`. **Service account tokens are scoped
to a single stack** — switching `GRAFANA_URL` requires generating a new token from that stack's
Administration → Service accounts page, and restarting the MCP server for the change to take effect.

## Verify which stack you're actually connected to

Before trusting any query result, confirm the stack:

1. `mcp__grafana__list_datasources` — the datasource names embed the stack name
   (e.g. `grafanacloud-gameschedulerprod-logs` vs `grafanacloud-gamescheduler-logs`).
2. `mcp__grafana__get_datasource` on the Loki datasource (uid `grafanacloud-logs`) and check
   `basicAuthUser` — it equals the Loki instance ID, which you can match against the table above.

If a diagnosis based on log contents seems to contradict known facts about what's deployed (wrong
code version, missing expected log lines, activity that doesn't match reality), suspect the wrong
stack before suspecting the deployment.

## Log label gotchas for this project

- `bot-service` logs ship directly via OTLP (no Alloy/container scraping), so its log streams have
  labels like `service_name`, `code_filepath`, `code_function`, `scope_name`, `trace_id` — but
  **no** `environment` or `container` label. Don't add `environment="production"` to a
  `bot-service` query; it will silently match zero lines.
- `frontend`, `postgres`, `redis`, `grafana-alloy` under the `service` / `container` labels
  (container names like `gamebot-test-*`) come from the **local devcontainer's Alloy**, scraping
  the local test docker-compose stack — not the cloud-deployed services. Don't confuse these with
  the real environment's data.

## Don't assume checked-out code == deployed code

Git HEAD in this working directory is not a reliable indicator of what's actually running in any
environment. To confirm what's deployed:

- Look for a log message that's unique to a specific commit/feature (e.g. a log string introduced
  by a specific migration) and check whether it appears at all in the target stack's logs.
- Cross-reference `git log` timestamps/commit hashes for the suspect file against tags
  (`git describe --tags`, `git log -1 <tag>`) rather than assuming the tag name matches what's live.
- When in doubt, ask — deploy state is operational knowledge the repo can't fully encode.
