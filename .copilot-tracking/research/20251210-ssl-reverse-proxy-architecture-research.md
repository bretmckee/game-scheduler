<!-- markdownlint-disable-file -->
# Task Research Notes: SSL Reverse Proxy Architecture

## Research Executed

### File Analysis
- `docker/frontend-nginx.conf`
  - Currently configured as HTTP-only (port 80)
  - Already includes reverse proxy for `/api/` → `http://api:8000/api/`
  - Includes security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
  - Handles React Router with `try_files` directive
  - Serves runtime configuration from `/config.js`

- `docker/frontend.Dockerfile`
  - Production stage uses `nginx:1.28-alpine`
  - Exposes port 80 only
  - Includes curl for healthchecks
  - Runtime configuration via entrypoint script

- `docker-compose.base.yml`
  - Frontend service ports: `${FRONTEND_HOST_PORT:-3000}:80`
  - API service ports: `${API_HOST_PORT:-8000}:8000`
  - Both services in same Docker network (`app-network`)
  - No SSL/TLS configuration present

### External Research
- #fetch:https://nginx.org/en/docs/http/configuring_https_servers.html
  - SSL configuration requires `listen 443 ssl;` directive
  - Certificate files: `ssl_certificate` and `ssl_certificate_key`
  - Best practices: SSL session cache, keepalive connections
  - Default protocols: TLSv1.2 and TLSv1.3
  - Recommended ciphers: `HIGH:!aNULL:!MD5`
  - Single server can handle both HTTP (80) and HTTPS (443)

- #fetch:https://docs.docker.com/compose/production/
  - Production modifications via additional compose files
  - Use `-f` option to layer configurations
  - Keep production-specific settings separate

### Project Conventions
- Multi-stage Dockerfiles with development/production targets
- Runtime configuration via environment variables
- Production deploys use `compose.production.yaml` overlay
- Nginx already serving as static file server + reverse proxy

## Key Discoveries

### Current Architecture
Your project uses nginx in the frontend container for:
1. **Static file serving**: Built React app from `/usr/share/nginx/html`
2. **Reverse proxy**: `/api/*` requests → `http://api:8000/api/*` (internal network)
3. **Runtime configuration**: Dynamic `config.js` generation at container startup
4. **React Router support**: `try_files` for client-side routing

### SSL Termination Placement Options

#### Option 1: Extend Existing Nginx (Single Container)
**Architecture**: Frontend nginx container handles both static files AND SSL termination

**Benefits**:
- **Simplicity**: One less container to manage
- **Resource efficiency**: No additional container overhead
- **Existing infrastructure**: Already proxying API requests
- **Single point of configuration**: All HTTP/HTTPS/proxy rules in one place
- **Easier certificate management**: Only one container needs cert files
- **Consistent with current design**: nginx already serving dual role

**Limitations**:
- **Mixed responsibilities**: Frontend container does both static files and SSL
- **Harder to scale frontend independently**: SSL and static serving coupled
- **Certificate updates require frontend restart**: Not ideal if frequent cert rotation

**Implementation**:
```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Redirect HTTP to HTTPS
    if ($scheme = http) {
        return 301 https://$server_name$request_uri;
    }

    # Existing proxy and static file rules...
}
```

**Volume mounts needed**:
```yaml
frontend:
  volumes:
    - ./certs:/etc/nginx/certs:ro
  ports:
    - "80:80"
    - "443:443"
```

#### Option 2: Dedicated Reverse Proxy Container
**Architecture**: Separate nginx/traefik/caddy container for SSL, proxies to frontend nginx

**Benefits**:
- **Separation of concerns**: SSL termination separate from application serving
- **Easier certificate management**: Dedicated container with automatic renewal (Traefik/Caddy)
- **Better for microservices**: Can proxy to multiple backend services
- **Independent scaling**: SSL layer scales separately from frontend
- **Zero-downtime cert rotation**: Reload proxy without touching frontend
- **Production-grade pattern**: Common in enterprise deployments

**Limitations**:
- **Additional complexity**: One more container to configure/monitor
- **Extra network hop**: Request → SSL proxy → frontend nginx → static files/API
- **Resource overhead**: Additional container memory/CPU
- **Duplicate functionality**: Two nginx instances doing different things
- **More configuration**: Need to coordinate between proxy and frontend configs

**Implementation with Traefik** (automatic Let's Encrypt):
```yaml
# docker-compose.ssl.yaml
services:
  traefik:
    image: traefik:v3.2
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-certs:/letsencrypt
    networks:
      - app-network

  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`your-domain.com`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
    # Remove ports - Traefik handles external access
```

**Implementation with Caddy** (automatic HTTPS):
```yaml
# docker-compose.ssl.yaml
services:
  caddy:
    image: caddy:2.8-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - app-network
```

```Caddyfile
your-domain.com {
    reverse_proxy frontend:80
}
```

#### Option 3: Cloud Load Balancer (External)
**Architecture**: Cloud provider handles SSL (AWS ALB, GCP Load Balancer, Azure App Gateway)

**Benefits**:
- **Zero container overhead**: SSL handled before reaching your stack
- **Managed certificates**: Auto-renewal by cloud provider
- **Advanced features**: WAF, DDoS protection, global load balancing
- **Scalability**: Cloud-native autoscaling
- **High availability**: Built-in redundancy

**Limitations**:
- **Cloud vendor lock-in**: Requires specific cloud platform
- **Additional cost**: Load balancer billing separate from compute
- **Configuration outside Docker Compose**: Not in your repository
- **Less portable**: Can't run same config locally/on-prem

## Recommended Approach

**For your project, I recommend Option 1: Extend Existing Nginx Container**

**Rationale**:
1. **You already have nginx proxying API requests** - adding SSL is natural extension
2. **Simplest to implement** - modify existing `frontend-nginx.conf` and mount certificates
3. **Least resource overhead** - no additional containers
4. **Consistent with your architecture** - single-server deployment, not microservices cluster
5. **Production-ready** - nginx SSL performance is excellent
6. **Easier debugging** - fewer moving parts to troubleshoot
7. **Your current pattern** - you already use nginx for dual-purpose (static + proxy)

**When to choose Option 2 (Dedicated Proxy)**:
- You need automatic certificate renewal (use Traefik/Caddy)
- You plan to add more services that need SSL (not just frontend/api)
- You want to separate SSL responsibility from application layer
- You're moving toward microservices architecture
- You need advanced routing (path-based routing to different services)

**When to choose Option 3 (Cloud LB)**:
- You're deploying to AWS/GCP/Azure
- You need WAF/DDoS protection
- You require multi-region high availability
- You want managed certificate lifecycle

## Implementation Guidance

### Objectives
- Add SSL/TLS support to existing nginx container
- Terminate SSL at nginx frontend container
- Redirect HTTP to HTTPS
- Maintain existing proxy functionality for API

### Key Tasks
1. Update `docker/frontend-nginx.conf` to listen on port 443
2. Add SSL certificate configuration directives
3. Configure HTTP to HTTPS redirect
4. Update `docker-compose.base.yml` to expose port 443
5. Mount certificate files into container
6. Update environment variables (FRONTEND_URL, API_URL to use https://)
7. Test SSL configuration and certificate chain

### Certificate Management Options

**Option A: Manual Certificates** (self-signed or purchased)
```yaml
frontend:
  volumes:
    - ./certs/fullchain.pem:/etc/nginx/certs/fullchain.pem:ro
    - ./certs/privkey.pem:/etc/nginx/certs/privkey.pem:ro
  ports:
    - "443:443"
    - "80:80"
```

**Option B: Let's Encrypt with Certbot** (separate renewal container)
```yaml
certbot:
  image: certbot/certbot
  volumes:
    - ./certs:/etc/letsencrypt
  entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

frontend:
  volumes:
    - ./certs/live/your-domain.com/fullchain.pem:/etc/nginx/certs/fullchain.pem:ro
    - ./certs/live/your-domain.com/privkey.pem:/etc/nginx/certs/privkey.pem:ro
```

**Option C: Switch to dedicated proxy with auto-certs** (Traefik/Caddy)
- This is essentially Option 2 from alternatives

### Success Criteria
- HTTPS connections work on port 443
- HTTP requests on port 80 redirect to HTTPS
- SSL certificate chain validates correctly
- API proxy continues to work under HTTPS
- Frontend static files serve correctly under HTTPS
- No mixed content warnings (all resources loaded via HTTPS)

## SWAG (Secure Web Application Gateway) Analysis

### What is SWAG?

SWAG is a LinuxServer.io Docker image that bundles:
- **Nginx** as the web server and reverse proxy
- **Certbot** with support for Let's Encrypt and ZeroSSL
- **Automatic certificate management** (generation and renewal)
- **Fail2ban** for intrusion prevention
- **PHP 8.4** support
- **Pre-configured proxy templates** for popular applications

### How SWAG Compares to Your Options

**SWAG is essentially "Option 2 (Dedicated Reverse Proxy) with batteries included"**

**Benefits of SWAG**:
- ✅ **Automatic Let's Encrypt/ZeroSSL certificates** - Handles DNS or HTTP validation automatically
- ✅ **Zero-touch renewal** - Checks certificates nightly and renews within 30 days of expiration
- ✅ **Built-in intrusion prevention** - Fail2ban configured out of the box
- ✅ **Pre-made proxy configs** - Comes with templates for hundreds of popular apps
- ✅ **Supports both HTTP and DNS validation** - Including 50+ DNS providers
- ✅ **Wildcard certificate support** - Via DNS validation
- ✅ **Active maintenance** - LinuxServer.io regularly updates the image

**Limitations of SWAG**:
- ❌ **Replaces your frontend nginx entirely** - Can't just "add" it to existing setup
- ❌ **Opinionated structure** - Uses LinuxServer.io's configuration patterns
- ❌ **Heavier image** - Includes PHP, Fail2ban, many Certbot plugins you may not need
- ❌ **Requires migration** - Would need to move your existing nginx config into SWAG's structure

### What Switching to SWAG Would Involve

**Current State**:
```yaml
frontend:
  image: nginx:1.28-alpine
  # Your custom nginx.conf
  # Serves React app + proxies API
```

**With SWAG**:
```yaml
swag:
  image: lscr.io/linuxserver/swag:latest
  cap_add:
    - NET_ADMIN  # Required for Fail2ban
  environment:
    - URL=your-domain.com
    - VALIDATION=dns  # or http
    - DNSPLUGIN=cloudflare  # if using DNS validation
    - EMAIL=your@email.com
    - SUBDOMAINS=wildcard  # or specific subdomains
  ports:
    - "443:443"
    - "80:80"
  volumes:
    - ./swag-config:/config

# Your existing frontend container would be removed
# React app would be served FROM SWAG's /config/www
```

**Migration Steps**:
1. **Move React build to SWAG** - Copy built assets to `/config/www`
2. **Migrate nginx config** - Adapt your `frontend-nginx.conf` to SWAG's `/config/nginx/site-confs/default.conf` structure
3. **Configure API proxy** - Use SWAG's proxy config pattern for your API
4. **Set up DNS validation** - Add credentials to `/config/dns-conf/cloudflare.ini` (or other provider)
5. **Test certificate generation** - Use `STAGING=true` first to avoid rate limits
6. **Remove frontend container** - SWAG replaces it entirely

### Does SWAG "Solve All These Issues"?

**It solves**:
- ✅ **Automatic certificate management** - No manual cert handling ever
- ✅ **Certificate renewal** - Automatic with monitoring
- ✅ **SSL configuration** - Pre-configured with modern security settings
- ✅ **Intrusion prevention** - Fail2ban included

**It does NOT solve**:
- ❌ **Complexity** - SWAG is MORE complex than adding SSL to existing nginx
- ❌ **Migration effort** - Requires reworking your current setup
- ❌ **Resource overhead** - Heavier image with features you may not need
- ❌ **Learning curve** - LinuxServer.io patterns differ from your current approach

### Recommendation

**SWAG is overkill for your use case** if you're just adding SSL. Here's why:

**Your Current Architecture**:
- Single-server deployment
- One frontend, one API
- Already using nginx successfully
- Just need to add SSL

**SWAG Makes Sense When**:
- You're starting from scratch
- You need to reverse proxy MANY services (Plex, Sonarr, Radarr, etc.)
- You want pre-made configs for popular self-hosted apps
- You need advanced features like Fail2ban
- You're okay with LinuxServer.io's opinionated structure

**For Your Project**:
**Stick with Option 1 (Extend Existing Nginx)**:
1. Add SSL directives to your existing `frontend-nginx.conf`
2. Mount certificate files into your frontend container
3. Use Certbot as a separate container OR simple certbot Docker run for renewals

**OR, if you want automatic renewal without SWAG**:
**Use Traefik or Caddy (Option 2, but simpler)**:
- Traefik: Automatic Let's Encrypt, lighter than SWAG, uses labels for routing
- Caddy: Automatic HTTPS, even simpler than Traefik, minimal config

### SWAG vs Traefik vs Caddy vs Manual nginx+SSL

| Feature | SWAG | Traefik | Caddy | Your nginx + SSL |
|---------|------|---------|-------|------------------|
| **Automatic certs** | ✅ | ✅ | ✅ | ❌ (manual) |
| **Renewal** | ✅ Auto | ✅ Auto | ✅ Auto | Manual |
| **Resource usage** | High | Medium | Low | Lowest |
| **Complexity** | High | Medium | Low | Lowest |
| **Migration effort** | High | Medium | Low | Lowest |
| **Fail2ban** | ✅ Built-in | ❌ | ❌ | ❌ |
| **Pre-made configs** | ✅ 100+ | Limited | Limited | ❌ |
| **Your existing setup** | Must replace | Add separate | Add separate | Extend |

### Final Answer

**Does SWAG solve all issues? Technically yes, but...**

SWAG would give you automatic SSL certificates and renewal, BUT:
- It requires **completely reworking** your frontend setup
- It's **heavier and more complex** than you need
- It's designed for **multi-service home servers**, not single-app deployments
- You'd lose your current clean architecture

**Better options for you**:
1. **Simplest**: Extend your existing nginx with SSL + manual Certbot renewal (5 minute setup)
2. **Automatic certs**: Add Caddy as reverse proxy (30 minute setup, minimal config)
3. **Production-grade**: Add Traefik as reverse proxy (60 minute setup, more features)
4. **Nuclear option**: Switch to SWAG (3+ hours migration, total rework)

Choose based on how much you value automatic certificate renewal vs. keeping your current simple architecture.
