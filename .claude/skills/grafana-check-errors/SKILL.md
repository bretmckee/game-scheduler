---
name: grafana-check-errors
description: Check whether any errors were logged in a given time window, using the grafana MCP server's Loki logs. Invoke for requests like "were there any errors in the last hour", "check for errors since yesterday", "any error spikes today", or general error/incident triage over a time range.
---

# Grafana Error Check

Answers "did anything error in this time window?" using Loki logs via the `grafana` MCP
server. Produces a per-service error count, sample error lines, and a Grafana Explore
deeplink — not a full incident investigation.

## Step 0: Confirm the stack

Read `.github/instructions/grafana-observability-debugging.instructions.md` first if you
haven't already this session. This project has **three separate Grafana Cloud stacks**
(dev/staging/prod) and the wrong one gives plausible-looking but wrong (empty or stale)
results with no error. Confirm which stack `.mcp.json` currently points at via
`mcp__grafana__list_datasources` (the datasource names embed the stack, e.g.
`grafanacloud-gameschedulerprod-logs` vs `grafanacloud-gamescheduler-logs`) before trusting
any result. If the user asked about an environment other than the connected one, say so
rather than silently reporting the wrong stack's data.

The Loki datasource to query is the one named `grafanacloud-<stack>-logs` — its UID is
`grafanacloud-logs` regardless of which stack is connected. Don't use the plain `loki`
datasource (a different UID) unless the user is specifically asking about the local
devcontainer's docker-compose stack rather than a deployed environment — see the
"Log label gotchas" section of the instructions file for what that stream contains.

## Step 1: Resolve the time window

Convert whatever the user said into `startRfc3339`/`endRfc3339` values (or Loki's relative
syntax, e.g. `now-1h`, `now-24h`, `now/d`). If the user gave a vague window ("today",
"since the deploy"), pick a concrete interpretation and state it back in the summary rather
than asking — the interval is easy to re-run if wrong.

## Step 2: Cheap aggregate pass across all services

Run one instant metric query to get error counts broken out by service for the whole
window, rather than pulling raw lines per service:

```
mcp__grafana__query_loki_logs
  datasourceUid: grafanacloud-logs
  logql: sum by (service_name) (count_over_time({service_name=~".+"} | detected_level="error" [<duration>]))
  queryType: instant
  endRfc3339: <end of window>
```

`detected_level` is a field Loki auto-derives from the OTLP `severity_text` on every log
line in this project (all services ship via OpenTelemetry — see `shared/telemetry.py`), so
it works uniformly across every current service without needing per-service label
knowledge. `<duration>` must match the requested window (e.g. `[1h]`, `[24h]`, `[7d]`) —
the range vector, not `startRfc3339`, determines how far back an instant query looks.

**Don't hardcode which services to expect.** `service_name` label values returned by Loki
(via `mcp__grafana__list_loki_label_values`) can include names from services that have
since been removed in a refactor — their old log lines are still inside Loki's retention
window even though the code is gone. `compose.yaml` (top-level service keys and their
`OTEL_SERVICE_NAME` env vars) is the source of truth for what's _currently_ deployed. If a
`service_name` shows up in query results that isn't in `compose.yaml`, say so in the report
rather than silently treating it as an active service to monitor.

If the result set is empty, don't report "no errors" yet — confirm the streams actually
have data in this window first (`mcp__grafana__query_loki_stats` with
`{service_name=~".+"}`) so a silent empty result from the wrong stack or a label typo isn't
mistaken for a clean bill of health.

## Step 3: Drill into any service with a nonzero count

For each service that showed errors, pull sample lines:

```
mcp__grafana__query_loki_logs
  datasourceUid: grafanacloud-logs
  logql: {service_name="<service>"} | detected_level="error"
  startRfc3339 / endRfc3339: <window>
  limit: 10-20
```

Each line's `labels`/`structuredMetadata` carries `code_filepath`, `code_function`,
`code_lineno`, `trace_id`, and `scope_name` — pull these into the summary, they're usually
enough to point at the offending code without opening a trace. If lines cluster into a
handful of repeated messages, prefer `mcp__grafana__query_loki_patterns` on that service to
report pattern + count instead of dumping every raw line.

## Step 4 (optional, for "did we have an incident" style asks)

`mcp__grafana__find_error_pattern_logs` runs a Sift analysis comparing the window against
the prior day's baseline and flags _elevated_ error patterns, not just presence of errors —
useful when the user wants to know if something is unusually broken, not just whether any
ERROR line exists (some background error rate may be normal). Pass `labels: {service_name:
"<service>"}` to scope it; omit to scan everything.

## When log content looks surprising, check the code before blaming the stack

Step 0's "confirm the stack" guidance cuts both ways. If a service's logs contain something
that looks like evidence of a wrong environment (e.g. `bot-service` logging
`"Environment: development"` or a log line naming a guild/tenant that sounds like a test
fixture), don't jump to "this must be dev/local telemetry leaking into this stack" — verify
against `list_datasources` first (per Step 0), and if that confirms you're on the expected
stack, the surprising content is more likely a real bug in the deployed service (e.g. an env
var not wired through in `compose.yaml`, or a wrong default in a `Field(default=...)`) than
proof of cross-environment contamination. Read the relevant service's config/startup code
(how it reads the field in question, and how `compose.yaml` passes — or fails to pass — the
matching env var) before concluding the data itself is untrustworthy. Report what you
actually verified, not the first plausible-sounding explanation.

## Step 5: Report

State the confirmed stack and resolved time window, then:

- A per-service error count table (zero-count services can be omitted or shown as "clean").
- For each nonzero service: 2-5 representative sample messages with `code_filepath:code_lineno`
  and `trace_id`, not a raw dump of every line.
- If truly nothing was found: say so plainly, and note the stats check that confirms the
  streams weren't just empty.
- A deeplink so the user can open it themselves:

```
mcp__grafana__generate_deeplink
  resourceType: explore
  datasourceUid: grafanacloud-logs
  queries: [{"refId":"A","expr":"{service_name=~\".+\"} | detected_level=\"error\""}]
  timeRange: {from: <start>, to: <end>}
  shorten: true
```
