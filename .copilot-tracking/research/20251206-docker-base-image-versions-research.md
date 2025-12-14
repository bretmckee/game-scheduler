<!-- markdownlint-disable-file -->
# Task Research Notes: Docker Base Image Version Currency Audit

## Research Executed

### File Analysis
- `docker-compose.base.yml`
  - Found all service image specifications with versions
  - PostgreSQL: `postgres:15-alpine`
  - RabbitMQ: `rabbitmq:4.2-management-alpine`
  - Redis: `redis:7-alpine`

- `docker/frontend.Dockerfile`
  - Builder stage: `node:20-alpine`
  - Production stage: `nginx:1.25-alpine`

- `docker/api.Dockerfile`, `docker/bot.Dockerfile`, `docker/notification-daemon.Dockerfile`, `docker/status-transition-daemon.Dockerfile`, `docker/init.Dockerfile`, `docker/test.Dockerfile`
  - All use: `python:3.11-slim`

### External Research
- #fetch:https://hub.docker.com/_/python
  - Current versions: 3.14 (latest), 3.13, 3.12, 3.11
  - 3.11.14 is latest patch version

- #fetch:https://hub.docker.com/_/node
  - Current LTS versions: Node 24 (Krypton - Active LTS), Node 22 (Jod - Maintenance LTS), Node 20 (Iron - Maintenance LTS)
  - Node 20 is in Maintenance LTS phase until April 2026

- #fetch:https://hub.docker.com/_/postgres
  - Current versions: 18 (latest), 17, 16, 15, 14
  - PostgreSQL 15 supported until November 2027

- #fetch:https://hub.docker.com/_/rabbitmq
  - Current versions: 4.2 (latest), 4.1, 4.0, 3.13
  - RabbitMQ 4.2 is most recent

- #fetch:https://hub.docker.com/_/redis
  - Current versions: 8.4 (latest), 8.2, 8.0, 7.4, 7.2
  - Redis 7.4 is most recent in version 7 line

- #fetch:https://hub.docker.com/_/nginx
  - Current versions: 1.29 (mainline), 1.28 (stable)
  - Nginx 1.28 is stable branch

### Project Conventions
- Standards referenced: `.github/instructions/containerization-docker-best-practices.instructions.md`
- Instructions followed: Use official Docker images, pin to specific versions, prefer Alpine variants for smaller size

## Key Discoveries

### Current Base Image Versions Used

| Service | Current Version | Component Files |
|---------|----------------|-----------------|
| Python | `3.11-slim` | All Python services (API, Bot, Init, Notification Daemon, Status Daemon, Test) |
| Node.js | `20-alpine` | Frontend builder |
| Nginx | `1.25-alpine` | Frontend production |
| PostgreSQL | `15-alpine` | Database service |
| RabbitMQ | `4.2-management-alpine` | Message queue |
| Redis | `7-alpine` | Cache service |

### Version Support Lifecycle

**Python Versions:**
- Python 3.11: Security support until October 2027 (currently in security phase)
- Python 3.12: Security support until October 2028 (currently in security phase)
- Python 3.13: Bugfix support until October 2029 (currently in bugfix phase)
- Python 3.14: Bugfix support until October 2030 (currently in bugfix phase)

**Node.js Versions:**
- Node 20 (Iron): Maintenance LTS until April 2026
- Node 22 (Jod): Maintenance LTS until April 2027
- Node 24 (Krypton): Active LTS until April 2028

**PostgreSQL Versions:**
- PostgreSQL 14: Supported until November 2026
- PostgreSQL 15: Supported until November 2027
- PostgreSQL 16: Supported until November 2028
- PostgreSQL 17: Supported until November 2029
- PostgreSQL 18: Supported until November 2030

**RabbitMQ Versions:**
- RabbitMQ 3.13: Older major version
- RabbitMQ 4.0, 4.1, 4.2: Current major version (4.x line)
- RabbitMQ 4.2 is the latest stable release

**Redis Versions:**
- Redis 7.x line: Stable and widely deployed
- Redis 8.x line: Latest with new tri-licensing model (RSALv2/SSPLv1/AGPLv3)
- Redis 7.4 is latest in 7.x line

**Nginx Versions:**
- Nginx 1.28: Stable branch
- Nginx 1.29: Mainline (development) branch
- Nginx 1.25: Older stable release

### Images Requiring Updates

1. **Python 3.11 → 3.13**: Currently using Python 3.11 which is in security-only support. Python 3.13 is in active bugfix support and represents the most recent LTS-equivalent version.

2. **Nginx 1.25 → 1.28**: Currently using Nginx 1.25 which is an older stable release. Nginx 1.28 is the current stable branch.

3. **PostgreSQL 15 → 17**: Currently using PostgreSQL 15 which has 3 years remaining support. PostgreSQL 17 is the latest stable with 5 years of support remaining.

4. **Redis 7 → 7.4**: Currently using generic Redis 7, should specify 7.4 for latest patches in the 7.x line.

### Images Already Current

1. **Node.js 20**: Still in Maintenance LTS (supported until April 2026) - acceptable but could upgrade to Node 22 LTS
2. **RabbitMQ 4.2**: Already using the latest stable version - no update needed

## Recommended Approach

Update all Docker base images to their most recent stable LTS versions:

1. **Python Services**: Update from `python:3.11-slim` to `python:3.13-slim`
   - Latest LTS version with active bugfix support
   - 5 years of support remaining
   - Minimal breaking changes from 3.11

2. **Frontend (Node.js)**: Consider updating from `node:20-alpine` to `node:22-alpine`
   - Node 20 still supported but Node 22 has longer support window
   - Optional upgrade, not critical

3. **Frontend (Nginx)**: Update from `nginx:1.25-alpine` to `nginx:1.28-alpine`
   - Current stable branch
   - Better long-term stability

4. **PostgreSQL**: Update from `postgres:15-alpine` to `postgres:17-alpine`
   - Latest stable major version
   - 2 years additional support
   - Will require database migration planning

5. **Redis**: Update from `redis:7-alpine` to `redis:7.4-alpine`
   - Latest in 7.x line
   - Avoids Redis 8.x licensing changes
   - Minimal migration risk

6. **RabbitMQ**: Keep `rabbitmq:4.2-management-alpine`
   - Already latest stable version
   - No changes needed

## Implementation Guidance

### Objectives
- Update all Docker base images to most recent stable LTS versions
- Maintain backward compatibility where possible
- Minimize breaking changes
- Ensure all versions have long-term support

### Key Tasks
1. Update Python version in all Dockerfiles
2. Update Nginx version in frontend Dockerfile
3. Update Redis version to specific 7.4 tag
4. Plan PostgreSQL migration path (major version upgrade)
5. Optionally update Node.js version
6. Update docker-compose.base.yml with new versions
7. Test all services with updated images
8. Update documentation with version changes

### Dependencies
- Python 3.13 compatibility testing for all services
- PostgreSQL 15 to 17 migration strategy
- Redis 7 to 7.4 compatibility verification
- Nginx 1.25 to 1.28 configuration compatibility

### Success Criteria
- All Docker images use actively supported LTS versions
- All services start and run correctly with updated images
- No breaking changes in application functionality
- Database migrations complete successfully
- Documentation reflects new versions
