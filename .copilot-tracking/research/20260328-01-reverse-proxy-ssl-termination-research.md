<!-- markdownlint-disable-file -->

# Task Research Notes: Reverse Proxy with SSL Termination and Let's Encrypt

## Research Executed

### File Analysis

- [compose.yaml](../../../compose.yaml)
  - Production config comment: "No port mappings (reverse proxy handles external access)" — confirms an external reverse proxy is expected but not yet in the compose stack
  - A `cloudflared` service already exists under a `profiles: cloudflare` gate, showing at least one approach was considered but not fully committed to
  - `app-network` is declared as `external: true` in compose.prod.yaml — the reverse proxy must join this network
- [compose.prod.yaml](../../../compose.prod.yaml)
  - No port mappings — `external: true` network confirms a proxy on the same Docker host
- [docker/frontend.Dockerfile](../../../docker/frontend.Dockerfile)
  - Production stage: `FROM nginx:1.28-alpine AS production` — the frontend IS nginx, serving static files and proxying `/api/` to the api container
- [docker/frontend-nginx.conf](../../../docker/frontend-nginx.conf)
  - Serves React SPA on port 80
  - Reverse proxies `/api/` → `http://api:8000/api/`
  - Has special SSE handling (`proxy_buffering off`, `proxy_read_timeout 86400s`)
  - Serves `config.js` with `no-cache` headers
  - Gzip, security headers, static asset caching

### Code Search Results

- `cloudflared` in compose.yaml
  - Present as a Cloudflare Tunnel option (profiles: cloudflare) — currently opt-in, not default
- Port 80/443 mappings in compose files
  - None in compose.yaml or compose.prod.yaml; compose.override.yaml not checked but dev only

### External Research

- #fetch:https://caddyserver.com/docs/automatic-https
  - Caddy has automatic HTTPS by default — it handles Let's Encrypt (and ZeroSSL as fallback), HTTP→HTTPS redirects, ACME HTTP-01, TLS-ALPN, and DNS-01 challenges automatically
  - Simply naming the domain in the Caddyfile activates certificate provisioning with no extra config
  - Certificates stored in configurable data directory; persistent volume required
  - Supports wildcard certs (DNS-01 only), failover between Let's Encrypt and ZeroSSL
  - Can serve static files AND reverse proxy — can fully replace an nginx frontend+proxy container
  - Latest stable: Caddy 2.x (v2.10 as of search date)

- #fetch:https://github.com/linuxserver/docker-swag
  - SWAG = nginx + Certbot (Let's Encrypt/ZeroSSL) + fail2ban in one container
  - Supports HTTP-01 and DNS-01 validation with a large library of pre-built DNS plugins
  - Nginx-based: existing nginx configurations (proxy_pass, headers, etc.) are directly portable
  - Extensive pre-built reverse proxy confs for popular apps
  - Certs checked nightly; renewal attempted when < 30 days to expiry
  - Current: v5.4.0-ls448 (updated continuously on Alpine base)
  - Requires `cap_add: NET_ADMIN` for fail2ban
  - Can serve static files from a volume; could replace the nginx frontend container if static assets are volume-mounted

- #fetch:https://traefik.io/traefik/
  - Traefik is a Docker-aware reverse proxy that auto-discovers containers via Docker labels
  - Built-in Let's Encrypt ACME support (HTTP-01, TLS-ALPN, DNS-01)
  - Does NOT serve static files — purely a reverse/load-balancing proxy
  - Would be an ADDITIONAL container, not a replacement for the nginx frontend
  - Current: Traefik Proxy v3.6 (2026)
  - Requires Docker socket access; excellent for multi-service ingress

- #fetch:https://github.com/nginx-proxy/acme-companion
  - Two-container solution: `nginxproxy/nginx-proxy` (nginx + docker-gen) + `acme-companion`
  - nginx-proxy auto-generates nginx reverse proxy configs from container env vars (`VIRTUAL_HOST`, `LETSENCRYPT_HOST`)
  - acme-companion handles ACME cert issuance via acme.sh
  - Requires Docker socket in both containers
  - Does NOT serve static files — still needs the existing nginx frontend container behind it
  - Latest: acme-companion v2.6.3; nginx-proxy v1.10

### Project Conventions

- Standards referenced: Docker Compose multi-file overlay pattern (compose.yaml + compose.prod.yaml)
- Instructions followed: containerization-docker-best-practices.instructions.md (multi-stage builds, minimal images)

## Key Discoveries

### Project Structure

The frontend container (`nginx:1.28-alpine`) currently:

1. Serves the built React SPA from `/usr/share/nginx/html`
2. Acts as reverse proxy for `/api/` and `/api/v1/sse/` to `http://api:8000`
3. Has no SSL — it is designed to sit behind a reverse proxy

The `cloudflare` profile shows the project already anticipates a choice between self-hosted SSL termination and Cloudflare Tunnel. No traditional SSL-terminating reverse proxy is currently implemented.

### Implementation Patterns

Three patterns are possible for this project:

**Pattern A — Replace frontend container** (Caddy or SWAG serving static files)

- The new proxy container takes over ALL duties: static file serving, `/api/` proxying, SSL termination, cert renewal
- Net change: `-frontend` container + `+proxy` container = same total count

**Pattern B — Add proxy in front of existing nginx** (Traefik, nginx-proxy+companion, or SWAG in pure proxy mode)

- The existing nginx frontend stays unchanged; new proxy terminates SSL and forwards to it
- Net change: adds 1 (or 2 for nginx-proxy+companion) containers

**Pattern C — Use Cloudflare Tunnel** (already partially implemented)

- Zero SSL management on the host, fully handled by Cloudflare edge
- The `cloudflared` service in compose.yaml supports this today

### Complete Examples

```yaml
# Caddy as frontend replacement (Pattern A)
# Replaces docker/frontend.Dockerfile production stage + frontend service in compose
services:
  frontend:
    image: caddy:2-alpine
    container_name: ${CONTAINER_PREFIX:-gamebot}-frontend
    restart: always
    ports:
      - '80:80'
      - '443:443'
      - '443:443/udp' # HTTP/3
    volumes:
      - /path/to/built/dist:/srv # static assets
      - ./docker/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data # persists certs
      - caddy_config:/config
    networks:
      - app-network
```

```
# docker/Caddyfile — roughly equivalent to frontend-nginx.conf
example.com {
    root * /srv
    encode gzip

    # SSE endpoint — streaming, no buffers
    handle /api/v1/sse/* {
        reverse_proxy api:8000 {
            flush_interval -1
            transport http {
                read_buffer_size 0
            }
        }
    }

    # API proxy
    handle /api/* {
        reverse_proxy api:8000
    }

    # React Router — serve index.html for unknown paths
    handle {
        try_files {path} {path}/ /index.html
        file_server
    }
}
```

```yaml
# SWAG replacing frontend container (Pattern A)
services:
  frontend:
    image: lscr.io/linuxserver/swag:latest
    container_name: ${CONTAINER_PREFIX:-gamebot}-frontend
    cap_add:
      - NET_ADMIN
    environment:
      - PUID=1000
      - PGID=1000
      - URL=example.com
      - VALIDATION=http # or dns with DNSPLUGIN=cloudflare
      - EMAIL=admin@example.com
    volumes:
      - swag_config:/config # nginx confs, certs, fail2ban state
    ports:
      - '80:80'
      - '443:443'
    networks:
      - app-network
    restart: always
```

```yaml
# Traefik in front of existing frontend nginx (Pattern B — adds a container)
services:
  traefik:
    image: traefik:v3.3
    container_name: ${CONTAINER_PREFIX:-gamebot}-traefik
    command:
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.le.acme.httpchallenge=true
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
      - --certificatesresolvers.le.acme.email=admin@example.com
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt
    networks:
      - app-network
    restart: always

  frontend:
    # existing nginx frontend unchanged
    labels:
      - 'traefik.enable=true'
      - 'traefik.http.routers.frontend.rule=Host(`example.com`)'
      - 'traefik.http.routers.frontend.entrypoints=websecure'
      - 'traefik.http.routers.frontend.tls.certresolver=le'
      - 'traefik.http.services.frontend.loadbalancer.server.port=80'
```

### API and Schema Documentation

- Let's Encrypt rate limits: 50 certificates per registered domain per week (does not apply to renewals)
- ACME HTTP-01 requires ports 80 and 443 accessible publicly
- ACME DNS-01 does not require public port access — useful for internal/staging hosts
- Let's Encrypt cert lifetime: 90 days; all tools above auto-renew at ~30 days remaining

### Configuration Examples

The existing `docker/frontend-nginx.conf` has these requirements that any replacement must handle:

1. `location = /config.js` — served with no-cache headers
2. `location /api/v1/sse/` — SSE: `proxy_buffering off`, `proxy_cache off`, long timeouts (86400s), `tcp_nodelay on`
3. `location /api/` — standard reverse proxy with WebSocket upgrade headers
4. React Router catch-all: `try_files $uri $uri/ /index.html`
5. Security headers: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`
6. Static asset caching: 1-year expires for `.js`, `.css`, fonts, images

**Caddy note on SSE**: Caddy handles SSE well — `flush_interval -1` disables buffering (equivalent to `proxy_buffering off`).

### Staging vs. Production Caddy Configuration

Caddy's **address syntax** is the on/off switch for automatic HTTPS:

| Address form             | HTTPS?                        | Use case                        |
| ------------------------ | ----------------------------- | ------------------------------- |
| `example.com { }`        | ✅ Auto TLS via Let's Encrypt | Production                      |
| `http://example.com { }` | ❌ HTTP only                  | Staging (behind existing proxy) |
| `:80 { }`                | ❌ HTTP only                  | Staging (domain not specified)  |

This maps cleanly onto the project's existing compose overlay pattern — two Caddyfiles, each mounted by the appropriate compose override:

```
docker/
  Caddyfile.staging   # :80 { ... }  — plain web server, no TLS
  Caddyfile.prod      # example.com { ... }  — full TLS via Let's Encrypt
```

**compose.staging.yaml** mounts the staging file:

```yaml
services:
  frontend:
    volumes:
      - ./docker/Caddyfile.staging:/etc/caddy/Caddyfile:ro
    # No ports — existing staging reverse proxy handles external access
    # Also remove caddy_data volume mount (no certs to store)
```

**compose.prod.yaml** mounts the prod file and adds port exposure:

```yaml
services:
  frontend:
    volumes:
      - ./docker/Caddyfile.prod:/etc/caddy/Caddyfile:ro
      - caddy_data:/data # Persists Let's Encrypt certs
      - caddy_config:/config
    ports:
      - '80:80'
      - '443:443'
      - '443:443/udp' # HTTP/3

volumes:
  caddy_data:
  caddy_config:
```

The staging Caddyfile (`:80`) behaves identically to the current `nginx:1.28-alpine` container from the perspective of the pre-existing staging reverse proxy. No staging infrastructure changes needed.

**Note on `compose.staging.yaml`**: Currently sets `NGINX_LOG_LEVEL: debug` for the frontend — this env var would be replaced with the equivalent Caddy log level env var (`LOG_LEVEL: DEBUG`).

### Technical Requirements

- Must handle SSE (Server-Sent Events) with long-lived connections without buffering
- Must support WebSocket upgrade for `/api/` endpoints
- Must serve `config.js` with no-cache headers
- Production network is `external: true` — the proxy must join `gamebot-network` (or similar)
- Staging network is an internal bridge (no `external: true`); existing reverse proxy accesses container on port 80
- Certs must be persisted on a named volume across container restarts/updates (prod only)
- Port 80 and 443 must be exposed in prod only (staging relies on existing reverse proxy)

## Recommended Approach

**Caddy** replacing the existing frontend container (Pattern A).

### Reasoning

| Criterion                                     | Caddy                  | SWAG                                 | Traefik            | nginx-proxy+companion        |
| --------------------------------------------- | ---------------------- | ------------------------------------ | ------------------ | ---------------------------- |
| Replaces existing container (no net addition) | ✅                     | ✅                                   | ❌                 | ❌                           |
| Zero-config HTTPS / Let's Encrypt             | ✅ Best-in-class       | ✅ Good                              | ✅ Good            | ✅ Good                      |
| Serves static files                           | ✅                     | ✅ (nginx)                           | ❌                 | ❌                           |
| SSE / WebSocket support                       | ✅                     | ✅                                   | ✅                 | ✅                           |
| Config simplicity                             | ✅ Caddyfile (minimal) | ⚠️ nginx conf (familiar but verbose) | ⚠️ Labels/TOML     | ⚠️ Two containers + env vars |
| Docker socket required                        | ❌ Not needed          | ❌ Not needed                        | ✅ Required        | ✅ Required                  |
| Fail2ban / intrusion prevention               | ❌ (not built-in)      | ✅                                   | ❌ (plugin needed) | ❌                           |
| Nginx config portability                      | ❌ New config format   | ✅ Existing conf reusable            | ❌                 | ✅ nginx-based               |
| User familiarity                              | Low                    | High (user uses SWAG)                | Medium             | Low                          |

**Caddy wins** on: simplicity, automatic HTTPS with zero config, no Docker socket dependency, replaces the existing container 1-for-1, and requires the fewest lines of configuration for this specific use case.

**SWAG is the strongest alternative** because:

- The user is already familiar with SWAG and knows how to configure it
- The nginx-based configuration is directly portable from `frontend-nginx.conf`
- Can also replace the existing frontend container (serves static files + proxy + SSL)
- fail2ban is a bonus if desired

**Key consideration**: Caddy's Caddyfile for this use case is ~15 lines vs. SWAG's nginx conf which would be nearly identical to the existing `frontend-nginx.conf`. Neither adds a container. Traefik and nginx-proxy+companion would both ADD containers.

### Recommended Version

**Software**: Caddy
**Recommended Version**: 2.x (latest stable)
**Type**: Latest Release
**Support Until**: Actively maintained; project follows semantic versioning with no fixed end-of-life
**Reasoning**: Caddy 2.x is the current major stable release; no LTS track exists — the latest release IS the stable recommendation
**Source**: https://caddyserver.com/docs/install

**Alternative Considered**:

- SWAG (linuxserver/swag): v5.4.0 (current, continuously updated on Alpine base) — strong alternative if familiarity and nginx config portability matter more than simplicity

## Implementation Guidance

- **Objectives**:
  1. Add SSL termination with automatic Let's Encrypt certificate renewal
  2. Replace (not add) the existing nginx frontend container where possible
  3. Preserve all existing nginx behavior: SSE streaming, API proxy, React Router catch-all, security headers, static asset caching

- **Key Tasks** (if Caddy selected):
  1. Remove `nginx:1.28-alpine` production stage from `docker/frontend.Dockerfile`, or replace the entire build with a Caddy-based multi-stage image (`FROM caddy:2-alpine` as final stage with built assets copied in)
  2. Create `docker/Caddyfile.staging` — `:80 { ... }` block, no TLS, mirrors current nginx behavior for the existing staging proxy
  3. Create `docker/Caddyfile.prod` — `{$DOMAIN} { ... }` block, automatic HTTPS
  4. Update `compose.yaml` frontend service: use `caddy:2-alpine`, mount `docker/Caddyfile.staging` as default (matches staging-first compose conventions), no ports in base
  5. Update `compose.staging.yaml`: replace `NGINX_LOG_LEVEL: debug` with Caddy equivalent (`LOG_LEVEL: DEBUG`); mount `Caddyfile.staging`
  6. Update `compose.prod.yaml`: mount `Caddyfile.prod`, add `ports: [80:80, 443:443, 443:443/udp]`, add `caddy_data` and `caddy_config` volumes
  7. Add `DOMAIN` env var to `config/env/env.prod` (e.g. `DOMAIN=example.com`)
  8. Add `caddy_data` and `caddy_config` named volumes to `compose.yaml`

- **Key Tasks** (if SWAG selected):
  1. Keep the multi-stage `frontend.Dockerfile`; the built React assets in `/app/dist` need to be volume-mounted or baked into a SWAG-based image
  2. Create nginx site config under `/config/nginx/site-confs/` (directly transplant `frontend-nginx.conf` with SSL additions)
  3. Update `compose.yaml` frontend service: use `lscr.io/linuxserver/swag:latest`, add required env vars, `cap_add: NET_ADMIN`, persistent `/config` volume, ports
  4. The SWAG approach requires either (a) a custom SWAG-based Docker image that bakes in the React build, or (b) a separate volume with the dist/ files (adds build complexity)

- **Dependencies**:
  - Domain DNS A/AAAA records must point to the host before cert issuance
  - Ports 80 and 443 must be open on the host firewall
  - `caddy_data` volume must be persistent (survives container recreation)
  - The `app-network` (external in prod) must be accessible to the new frontend container

- **Success Criteria**:
  - HTTPS works with a valid Let's Encrypt certificate
  - HTTP redirects to HTTPS automatically
  - `/api/` and `/api/v1/sse/` work correctly through the proxy
  - React SPA routing works (`/dashboard`, `/login`, etc. all return `index.html`)
  - `config.js` is served without caching
  - Certificate renews automatically without downtime
