# Deployment Documentation

Documentation for deploying and operating Game Scheduler in production environments.

## Quick Links

- **[Quick Start](quickstart.md)** - Rapid deployment guide for new servers
- **[Configuration](configuration.md)** - Runtime configuration and environment variables
- **[Docker Guide](docker.md)** - Container deployment, port strategy, and build optimization
- **[Version Management](version-management.md)** - Automatic versioning with setuptools-scm

## Overview

Game Scheduler is a containerized Discord bot application built with Docker Compose. This documentation covers self-hosting for guild administrators or organizations who want to run their own instance.

## System Requirements

### Minimum Requirements

- **OS**: Linux (Ubuntu 22.04+, Debian 12+) or macOS with Docker Desktop
- **CPU**: 2 cores (4 recommended for production)
- **RAM**: 2GB minimum (4GB recommended)
- **Disk**: 10GB minimum (20GB recommended for logs and database growth)
- **Docker**: 24.0+ with BuildKit enabled
- **Docker Compose**: 2.20+

### Network Requirements

- **Ports**: 3000 (frontend), 8000 (API) exposed to host in staging/test
- **Production**: Reverse proxy recommended (no direct port exposure)
- **Outbound**: HTTPS (443) access to Discord API
- **Optional**: Grafana Cloud access for observability

## Prerequisites

Before deploying, you need:

1. **Discord Bot Application**
   - Created via [Discord Developer Portal](https://discord.com/developers/applications)
   - Bot token, client ID, and client secret
   - See [Developer Setup Guide](../developer/SETUP.md) for bot creation steps

2. **Server Access**
   - SSH access to deployment server
   - Sudo privileges for Docker installation
   - Git installed for code checkout

3. **Domain/IP** (optional but recommended)
   - Domain name with DNS configured
   - SSL certificate for HTTPS (Let's Encrypt recommended)

## Deployment Workflow

```
1. Clone repository
   ↓
2. Configure environment (config/env/env.prod.local)
   ↓
3. Build Docker images
   ↓
4. Start services with docker compose
   ↓
5. Verify services are healthy
   ↓
6. Configure Discord bot invite URL
   ↓
7. Add bot to Discord server
```

## Security Considerations

### Required Security Steps

1. **Change default passwords** in environment file:
   - `POSTGRES_PASSWORD`
   - `RABBITMQ_DEFAULT_PASS`
   - Update `RABBITMQ_URL` with new password

2. **Protect environment files**:
   ```bash
   chmod 600 config/env/env.prod.local
   ```

3. **Use HTTPS** in production:
   - Set `BACKEND_URL=https://your-domain.com`
   - Configure reverse proxy (nginx, Caddy, Traefik)
   - Obtain SSL certificate (Let's Encrypt recommended)

4. **Restrict Discord OAuth redirect**:
   - In Discord Developer Portal, set redirect URI to your domain
   - Example: `https://your-domain.com/auth/callback`

5. **Network isolation**:
   - Production deployment exposes NO ports to host
   - All external access via reverse proxy
   - Infrastructure services (postgres, rabbitmq, redis) never exposed

### Security Best Practices

- Keep Docker images updated with security patches
- Use strong, unique passwords for all services
- Enable firewall (ufw, firewalld) to restrict access
- Monitor logs for suspicious activity
- Regular database backups
- Consider using secrets management (Docker secrets, Vault)

## Environment Configuration Files

Game Scheduler uses environment files in `config/env/` to configure different deployment modes:

- **`env.prod`** - Production template (no ports exposed, production builds)
- **`env.staging`** - Staging template (ports exposed, production builds, debug logging)
- **`env.dev`** - Development template (all ports exposed, dev builds, hot-reload)

Copy the appropriate template to `*.local` and customize:

```bash
cp config/env/env.prod config/env/env.prod.local
# Edit env.prod.local with your configuration
```

**Note**: `*.local` files are gitignored to prevent committing secrets.

## Version Management

Game Scheduler uses `setuptools-scm` for automatic versioning from git tags. No manual version configuration required!

**Access version information:**
- API endpoint: `/api/v1/version`
- Health endpoint: `/health`
- Web interface: About page

See [Version Management Guide](version-management.md) for detailed information.

## Observability (Optional)

Game Scheduler includes OpenTelemetry instrumentation for traces, metrics, and logs.

**Grafana Cloud integration** (optional):
- Configure `GRAFANA_CLOUD_*` environment variables
- Grafana Alloy forwards telemetry to Grafana Cloud
- Free tier: 50GB traces/logs, 10K active metrics

See [Configuration Guide](configuration.md#opentelemetry-and-observability-configuration) for setup instructions.

## Support Resources

- **Developer Documentation**: [../developer/README.md](../developer/README.md)
- **Guild Admin Guide**: [../GUILD-ADMIN.md](../GUILD-ADMIN.md) - Adding bot to Discord servers
- **GitHub Issues**: Report bugs or request features
- **Discord Server**: (Add your support server invite if available)

## Next Steps

1. **New deployment**: Start with [Quick Start Guide](quickstart.md)
2. **Configuration questions**: See [Configuration Guide](configuration.md)
3. **Docker questions**: See [Docker Guide](docker.md)
4. **Contributing to project**: See [Developer Documentation](../developer/README.md)
