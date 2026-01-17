# Docker Build Cache Optimization

## Changes Implemented

BuildKit cache mounts have been added to all Python-based Dockerfiles to eliminate duplicate package downloads across services and dramatically reduce build times.

## Files Modified

1. `docker/api.Dockerfile`
2. `docker/bot.Dockerfile`
3. `docker/test.Dockerfile`
4. `docker/init.Dockerfile`
5. `docker/notification-daemon.Dockerfile`
6. `docker/status-transition-daemon.Dockerfile`
7. `docker/retry.Dockerfile`

## What Changed

### 1. BuildKit Syntax Directive
Added to the top of each Dockerfile:
```dockerfile
# syntax=docker/dockerfile:1
```

### 2. Apt Package Cache Configuration
Added before apt-get commands:
```dockerfile
# Configure apt to keep downloaded packages for cache mount
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
```

### 3. Apt Package Cache Mounts
All `apt-get install` commands now use cache mounts:
```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y [packages]
```

### 4. Python Package Cache Mounts
All pip and uv commands now use cache mounts:
```dockerfile
# For pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir uv

# For uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .
```

## Expected Benefits

### Before
- Each service independently downloads packages from deb.debian.org (~11.4s per service)
- Total ~45+ seconds wasted across 5 services in parallel builds
- No cache sharing between services
- Python packages downloaded separately for each service

### After
- First build: Downloads packages once, stores in persistent cache
- Subsequent builds: Reuses cached packages across ALL services
- Only downloads new or changed packages
- Expected build time reduction: **50-70%** for incremental builds

## How It Works

### Cache Mount Behavior
- **Persistent**: Cache survives across builds and rebuilds
- **Shared**: Available to all services during parallel builds
- **Locked**: Apt uses `sharing=locked` to prevent concurrent access conflicts
- **Automatic**: BuildKit manages cache size and eviction

### Cache Locations
- `/var/cache/apt` - Downloaded .deb files
- `/var/lib/apt` - Package metadata
- `/root/.cache/pip` - pip cache
- `/root/.cache/uv` - uv cache

## Testing

To verify the optimization:

```bash
# Clean all Docker build cache
docker builder prune -af

# First build (will populate cache)
time docker compose build

# Second build (should be much faster)
time docker compose build

# Or build a single service
time docker compose build api
```

## Maintenance

### Clearing Cache
If needed, clear the cache mounts:
```bash
docker builder prune --filter type=exec.cachemount
```

### Monitoring Cache Size
```bash
docker system df -v
```

## Compatibility

- **Requires**: Docker BuildKit (enabled by default in Docker 23.0+)
- **Requires**: Dockerfile syntax version 1.2+ (specified in syntax directive)
- **No changes needed**: docker-compose.yaml
- **No functional changes**: Built images are identical

## References

- Research document: `.copilot-tracking/research/20260117-docker-build-cache-optimization-research.md`
- Docker BuildKit cache documentation: https://docs.docker.com/build/cache/
- Cache mount reference: https://docs.docker.com/reference/dockerfile/#run---mounttypecache
