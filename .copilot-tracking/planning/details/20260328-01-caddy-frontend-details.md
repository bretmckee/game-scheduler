<!-- markdownlint-disable-file -->

# Task Details: Replace nginx Frontend with Caddy (SSL Termination)

## Research Reference

**Source Research**: #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md

---

## Phase 1: Update frontend.Dockerfile

### Task 1.1: Replace `nginx:1.28-alpine` production stage with `caddy:2-alpine`

Replace only the final `production` stage of the multi-stage Dockerfile. The `base` and `builder` stages are unchanged. The Caddy final stage copies the built React assets to `/srv` (Caddy's default file server root) instead of `/usr/share/nginx/html`, and removes the nginx config copy.

- **Files**:
  - `docker/frontend.Dockerfile` — replace `production` stage (currently lines 38-end)
- **Exact change** — replace the production stage block:

  ```dockerfile
  # Remove this entire block:
  # Production stage using nginx
  FROM nginx:1.28-alpine AS production
  RUN apk add --no-cache curl
  COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf
  COPY --from=builder /app/dist /usr/share/nginx/html

  # Replace with:
  # Production stage using Caddy
  FROM caddy:2-alpine AS production
  RUN apk add --no-cache curl
  COPY --from=builder /app/dist /srv
  ```

  The `EXPOSE` directive is not needed (Caddy exposes 80/443 by default; Docker does not require it). The Caddyfile is mounted as a volume by the compose overlays, not baked into the image.

- **Success**:
  - `docker compose build frontend` succeeds
  - The production image runs `caddy` as its entrypoint (default for the official Caddy image)
  - The `/srv` directory in the built image contains the React assets
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 99-115) — Caddy Pattern A: replace frontend container
- **Dependencies**:
  - None (first task)

---

## Phase 2: Create Caddyfiles

### Task 2.1: Create `docker/Caddyfile.staging` — HTTP-only server

Create a new file `docker/Caddyfile.staging`. The `:80` address tells Caddy to serve plain HTTP with no ACME/TLS activity, which is exactly what is needed behind the existing staging reverse proxy.

The config must replicate all behavior from `docker/frontend-nginx.conf`:

- **Files**:
  - `docker/Caddyfile.staging` — create new file
- **Full file content**:

  ```caddyfile
  {
      log {
          level {$LOG_LEVEL:info}
      }
  }

  :80 {
      root * /srv
      encode gzip

      # No-cache for runtime config injected at startup
      @config_js path /config.js
      header @config_js Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
      header @config_js Expires "0"

      # Security headers
      header X-Frame-Options "SAMEORIGIN"
      header X-Content-Type-Options "nosniff"
      header X-XSS-Protection "1; mode=block"

      # SSE endpoint — must not buffer; long-lived connections
      handle /api/v1/sse/* {
          reverse_proxy api:8000 {
              flush_interval -1
              header_up Host {host}
              header_up X-Real-IP {remote_host}
              header_up X-Forwarded-For {remote_host}
              header_up X-Forwarded-Proto {scheme}
          }
      }

      # API proxy with WebSocket upgrade support
      handle /api/* {
          reverse_proxy api:8000 {
              header_up Host {host}
              header_up X-Real-IP {remote_host}
              header_up X-Forwarded-For {remote_host}
              header_up X-Forwarded-Proto {scheme}
              header_up Upgrade {http.request.header.Upgrade}
              header_up Connection {http.request.header.Connection}
          }
      }

      # Static assets — 1-year immutable cache
      @static_assets path_regexp \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$
      header @static_assets Cache-Control "public, max-age=31536000, immutable"

      # React Router — serve index.html for all unmatched paths
      handle {
          try_files {path} {path}/ /index.html
          file_server
      }
  }
  ```

- **Success**:
  - Caddy starts with this file and serves the SPA on port 80
  - `/api/...` requests are proxied to `api:8000`
  - No TLS certificate requests are made
  - `LOG_LEVEL` env var controls log verbosity
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 99-140) — Caddyfile example
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 217-228) — nginx behavior requirements to replicate
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 229-277) — staging vs. production pattern, `:80` syntax
- **Dependencies**:
  - Task 1.1 (Dockerfile update) should be complete first, but this file can be created independently

### Task 2.2: Create `docker/Caddyfile.prod` — automatic HTTPS

Create a new file `docker/Caddyfile.prod`. Using `{$DOMAIN}` as the site address (no scheme prefix) activates Caddy's automatic HTTPS: it obtains and renews a Let's Encrypt certificate and redirects HTTP to HTTPS automatically.

- **Files**:
  - `docker/Caddyfile.prod` — create new file
- **Full file content**:

  ```caddyfile
  {
      log {
          level {$LOG_LEVEL:info}
      }
      email {$ACME_EMAIL}
  }

  {$DOMAIN} {
      root * /srv
      encode gzip

      # No-cache for runtime config injected at startup
      @config_js path /config.js
      header @config_js Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
      header @config_js Expires "0"

      # Security headers
      header X-Frame-Options "SAMEORIGIN"
      header X-Content-Type-Options "nosniff"
      header X-XSS-Protection "1; mode=block"

      # SSE endpoint — must not buffer; long-lived connections
      handle /api/v1/sse/* {
          reverse_proxy api:8000 {
              flush_interval -1
              header_up Host {host}
              header_up X-Real-IP {remote_host}
              header_up X-Forwarded-For {remote_host}
              header_up X-Forwarded-Proto {scheme}
          }
      }

      # API proxy with WebSocket upgrade support
      handle /api/* {
          reverse_proxy api:8000 {
              header_up Host {host}
              header_up X-Real-IP {remote_host}
              header_up X-Forwarded-For {remote_host}
              header_up X-Forwarded-Proto {scheme}
              header_up Upgrade {http.request.header.Upgrade}
              header_up Connection {http.request.header.Connection}
          }
      }

      # Static assets — 1-year immutable cache
      @static_assets path_regexp \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$
      header @static_assets Cache-Control "public, max-age=31536000, immutable"

      # React Router — serve index.html for all unmatched paths
      handle {
          try_files {path} {path}/ /index.html
          file_server
      }
  }
  ```

- **Notes**:
  - `{$DOMAIN}` — expanded from the `DOMAIN` env var at runtime
  - `{$ACME_EMAIL}` — Let's Encrypt registration email (required to receive expiry notifications); set in `config/env/env.prod`
  - HTTP→HTTPS redirect is automatic; no extra config needed
  - `caddy_data` volume on `/data` persists certificates across container restarts
- **Success**:
  - Caddy starts and requests a certificate from Let's Encrypt for `$DOMAIN`
  - HTTPS is served on port 443
  - HTTP on port 80 redirects to HTTPS
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 31-66) — Caddy automatic HTTPS research
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 229-277) — staging/prod Caddyfile pattern
- **Dependencies**:
  - Task 2.1 complete (share common structure)

---

## Phase 3: Update Compose Files

### Task 3.1: Update `compose.yaml` frontend service

The base `compose.yaml` drives development and is the foundation for all overlays. Changes:

1. Change the `build` target reference: the build section stays (needed for the Caddy-based image), but `frontend-nginx.conf` is no longer referenced there
2. Replace `NGINX_LOG_LEVEL` env var with `LOG_LEVEL` (used by the Caddyfile's `{$LOG_LEVEL}` placeholder)
3. Add a volume mount for `docker/Caddyfile.staging` as the default Caddyfile (safe default — no TLS)
4. Update the healthcheck: Caddy still responds on port 80, so `curl -f http://localhost:80/` remains valid; no change needed

- **Files**:
  - `compose.yaml` — modify `frontend` service `environment` and `volumes` sections
- **Changes**:
  - In `environment`: rename `NGINX_LOG_LEVEL` → `LOG_LEVEL`
  - In `volumes`: add `- ${HOST_WORKSPACE_FOLDER:-.}/docker/Caddyfile.staging:/etc/caddy/Caddyfile:ro`
- **Success**:
  - `docker compose config` shows `LOG_LEVEL` in the frontend environment
  - `docker compose config` shows the Caddyfile.staging volume mount on the frontend service
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 229-277) — compose overlay pattern for Caddyfiles
- **Dependencies**:
  - Tasks 2.1 and 2.2 complete (Caddyfiles must exist before mounting)

### Task 3.2: Update `compose.staging.yaml` frontend service

Replace the `NGINX_LOG_LEVEL: debug` environment variable with `LOG_LEVEL: debug` (used by `{$LOG_LEVEL}` in `Caddyfile.staging`). Explicitly mount `Caddyfile.staging` to make the staging overlay self-documenting (even though it matches the base default).

- **Files**:
  - `compose.staging.yaml` — modify `frontend` service `environment` section; add `volumes`
- **Changes**:
  - In `environment`: replace `NGINX_LOG_LEVEL: debug` with `LOG_LEVEL: debug`
  - In `volumes`: add `- ${HOST_WORKSPACE_FOLDER:-.}/docker/Caddyfile.staging:/etc/caddy/Caddyfile:ro`
- **Success**:
  - `docker compose -f compose.yaml -f compose.staging.yaml config` shows `LOG_LEVEL: debug` on the frontend service
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 229-277) — compose.staging.yaml pattern
- **Dependencies**:
  - Task 3.1 complete

### Task 3.3: Update `compose.prod.yaml` frontend service and volumes

Add Caddyfile.prod volume mount, expose ports 80/443, and add the persistent `caddy_data` and `caddy_config` named volumes needed for cert storage.

- **Files**:
  - `compose.prod.yaml` — modify `frontend` service; add `volumes` top-level section
- **Changes to frontend service**:
  ```yaml
  frontend:
    build:
      target: production
    volumes:
      - caddy_data:/data
      - caddy_config:/config
      - ${HOST_WORKSPACE_FOLDER:-.}/docker/Caddyfile.prod:/etc/caddy/Caddyfile:ro
    ports:
      - '80:80'
      - '443:443'
      - '443:443/udp'
    depends_on:
      api:
        condition: service_healthy
      scheduler:
        condition: service_healthy
      retry-daemon:
        condition: service_healthy
  ```
- **Add top-level volumes section** (after `networks`):
  ```yaml
  volumes:
    caddy_data:
    caddy_config:
  ```
- **Success**:
  - `docker compose -f compose.yaml -f compose.prod.yaml config` shows ports 80, 443, and 443/udp on the frontend service
  - `docker compose -f compose.yaml -f compose.prod.yaml config` shows `caddy_data` and `caddy_config` volumes
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 247-265) — compose.prod.yaml volumes/ports pattern
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 279-288) — technical requirements: certs must persist, prod must expose ports
- **Dependencies**:
  - Task 3.1 and 3.2 complete

### Task 3.4: Add `DOMAIN` and `ACME_EMAIL` to `config/env/env.prod`

Add placeholders for the two new production env vars consumed by `Caddyfile.prod`. Also check `config.template/env.template` and add the same variables there so new deployments get the template.

- **Files**:
  - `config/env/env.prod` — add two entries
  - `config.template/env.template` — add same two entries with placeholder values
- **Entries to add**:
  ```
  DOMAIN=your.domain.example.com
  ACME_EMAIL=admin@your.domain.example.com
  ```
- **Success**:
  - Both vars present in `env.prod` and `env.template`
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 329-364) — implementation guidance: add DOMAIN to env.prod
- **Dependencies**:
  - Task 3.3 complete

---

## Phase 4: Cleanup

### Task 4.1: Remove `docker/frontend-nginx.conf`

Once the Dockerfile no longer references it, `docker/frontend-nginx.conf` is an unused artifact. Delete it and verify no remaining references exist in the codebase.

- **Files**:
  - `docker/frontend-nginx.conf` — delete
- **Verification**: run `grep -r "frontend-nginx.conf" .` — should return no results
- **Success**:
  - File deleted
  - `grep -r "frontend-nginx.conf" .` returns no output
- **Research References**:
  - #file:../research/20260328-01-reverse-proxy-ssl-termination-research.md (Lines 7-23) — file analysis: confirms `frontend-nginx.conf` is only referenced from `frontend.Dockerfile`
- **Dependencies**:
  - Task 1.1 complete (nginx conf no longer referenced in Dockerfile)

---

## Dependencies

- `caddy:2-alpine` official Docker image
- Compose overlay pattern (`compose.yaml` + environment-specific file) — already established in this project

## Success Criteria

- `docker compose build frontend` completes without error
- Staging: `docker compose --env-file config/env/env.staging up -d frontend` serves HTTP on port 80; no cert issuance attempted
- Production: `docker compose --env-file config/env/env.prod up -d frontend` exposes 80/443, obtains Let's Encrypt cert, redirects HTTP to HTTPS
- All API and SSE proxy paths functional
- React SPA deep-link routing functional
- `docker/frontend-nginx.conf` removed, no dangling references
