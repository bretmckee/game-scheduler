---
name: remote-psql
description: Build copy-pasteable commands to run psql queries against a deployed environment's Postgres (dev/staging/prod/tal), via docker exec on the remote host. Invoke when the user wants to inspect or fix data on a deployed database, or asks for "psql commands" / "a query I can run on the server" for dev, staging, prod, or tal.
---

# Remote psql

This project's databases only exist inside `docker exec`-reachable Postgres containers on
each deployed host — there is no direct network access to them from here, and this agent has
no shell on the remote host. The workflow is always: **generate a copy-pasteable command,
the user runs it on the remote host, they paste the output back.** Never claim to have run a
remote query yourself.

## Step 1: Identify the environment and its env file path

Ask (or infer from context) which environment: `dev`, `staging`, `prod`, or `tal`. Each has a
`config/env.<name>` file in this repo that documents the _shape_ of the variables
(`CONTAINER_PREFIX`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, ...), but the file
actually used is on the remote host and its path there is whatever the user tells you — it
does not necessarily match this repo's layout (e.g. one host keeps it at
`bot/config/env.tal`, not `config/env.tal`). Don't assume; ask if it's not already stated in
the conversation.

Note `tal` and `prod` currently share `CONTAINER_PREFIX=gamebot-prod` (see `config/env.tal`
and `config/env.prod`) — that's fine, they're separate physical hosts, but it means the
container name alone doesn't disambiguate environment. What matters is which host/env file
the user is sourcing.

## Step 2: Build the command

Container naming comes from `compose.yaml`: `container_name: ${CONTAINER_PREFIX:-gamebot}-postgres`.
Source the env file with `set -a`/`set +a` so plain `KEY=VALUE` lines (no `export` prefix) get
exported into the shell that `docker exec` reads from, then reference `$CONTAINER_PREFIX`
dynamically rather than hardcoding the container name:

```bash
set -a && source <path-to-env-file> && set +a && docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "${CONTAINER_PREFIX}-postgres" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '<SQL>'
```

- Use `$POSTGRES_USER`/`$POSTGRES_PASSWORD` (the superuser) for ad hoc queries unless the
  user asks for a scoped role — `$POSTGRES_APP_USER`/`$POSTGRES_APP_PASSWORD` or
  `$POSTGRES_BOT_USER`/`$POSTGRES_BOT_PASSWORD` also exist in the env file if least-privilege
  matters.
- Single-quote the `-c` payload and write the SQL with normal double-quoted identifiers
  inside it (e.g. `"where"`) — avoids the backslash-escaping mess of putting double-quoted
  SQL inside a double-quoted shell string.
- Keep it one line so it's a single copy-paste block for the user.

## Step 3: Start read-only and low-risk

Before handing over the real query, confirm connectivity and permissions with something
trivial and non-destructive — `\dt`, `\d <table>`, or a `SELECT ... LIMIT ...`. Only move on
to the actual query once that's confirmed working. This matters more here than usual because
these commands typically target production-like data with no dry-run.

## Step 4: Get the schema right before writing SQL

Never guess table or column names. This project's schema is SQLAlchemy models under
`shared/models/*.py` (e.g. `game_templates`, `guild_configurations`) — read the relevant
model file first to confirm table name (`__tablename__`), column names, and types (quoting
matters: reserved words like `where` need double quotes in the SQL).

## Step 5: Mutations need explicit sign-off

For `UPDATE`/`DELETE`/`DROP`/anything destructive: hand it over as its own clearly-labeled
command, separate from the read-only exploration commands, and say plainly what it will
change and on which environment. Don't bundle a mutation into the same breath as a SELECT
without the user having seen the SELECT's output first — the whole point of Step 3/4 is to
confirm you're targeting the right row before changing it. If the user hasn't yet confirmed
the query results identify the right target, ask before producing the mutating command.
