<!-- markdownlint-disable-file -->
# Task Research Notes: Deployment Configuration Organization for Easier Deployments

## Research Executed

### File Analysis
- Not applicable (external research focus)

### Code Search Results
- #githubRepo:"traefik/traefik deployment config organization"
  - Traefik and similar projects use a dedicated config directory (e.g., `dynamic/`, `config/`) for all deployment-related files, and recommend mounting or copying this directory into the container or deployment environment. Compose files are often layered for environment-specific overrides.
- #githubRepo:"netbox-community/netbox deployment config organization"
  - NetBox uses a clear separation between code and configuration, with environment-specific settings (e.g., `configuration.py`, `.env`) and encourages externalizing secrets and per-site config.
- #githubRepo:"home-assistant/core deployment config organization"
  - Home Assistant uses a `config/` directory for all user and deployment-specific configuration, and supports mounting this directory or using it as a volume. Per-site or per-instance config is kept outside the main codebase.

### External Research
- #fetch:https://12factor.net/config
  - The Twelve-Factor App recommends storing all config in environment variables, not in code or checked-in config files. Config should be separated from code, and per-deploy values (e.g., credentials, hostnames) should be managed outside the codebase.
- #fetch:https://docs.docker.com/compose/production/
  - Docker Compose best practices recommend using a dedicated config directory and layering multiple Compose files (e.g., `compose.yaml`, `compose.prod.yaml`) for environment-specific overrides. Config files, secrets, and environment files should be grouped for each deployment.
- #fetch:https://martinfowler.com/bliki/ConfigurationAsCode.html
  - (Not found)

### Project Conventions
- Standards referenced: 12factor, Docker Compose, open source project patterns
- Instructions followed: N/A (external research)

## Key Discoveries

### Project Structure
- Leading projects (Traefik, Home Assistant, NetBox) separate code from configuration by:
  - Placing all deployment-specific config (env files, secrets, service configs) in a single directory (e.g., `config/`, `deploy/`, or `site-config/`).
  - Keeping this directory out of the main codebase, or managing it as a separate git repository or submodule for per-site customization.
  - Using Docker Compose layering for environment-specific overrides (e.g., `compose.yaml` + `compose.prod.yaml`).

### Implementation Patterns
- **Config Directory Pattern**: All deployment config (env files, RabbitMQ, Grafana, etc.) is placed in a single directory, which can be versioned separately or as a submodule.
- **Submodule/External Repo Pattern**: The main application code is a subdirectory or submodule, and the root repo contains only config and deployment files.
- **Environment Variable Pattern**: All sensitive and environment-specific config is managed via environment variables, with `.env` files or secret managers.
- **Compose Layering**: Use multiple Compose files for base and environment-specific overrides.

### Complete Examples
# Example directory structure (Config Directory Pattern)
#
# project-root/
#   config/
#     env.prod
#     env.staging
#     rabbitmq/
#       rabbitmq.conf
#     grafana-alloy/
#       config.alloy
#     ...
#   src/ (or app/ or game-scheduler/)
#     ... (main code as submodule or subdirectory)
#   compose.yaml
#   compose.prod.yaml
#
# Example directory structure (Submodule Pattern)
#
# site-deployment-repo/
#   config/
#     ...
#   game-scheduler/ (submodule)
#     ...
#   compose.yaml
#   ...

### API and Schema Documentation
- Not applicable

### Configuration Examples
# docker-compose layering
# $ docker compose -f compose.yaml -f compose.prod.yaml up -d

## Technical Requirements
- Must support per-site configuration in a single directory or repo
- Must allow easy updates to main codebase (e.g., via submodule)
- Must keep secrets and environment-specific config out of main code
- Should support Docker Compose layering for overrides

## Recommended Approach

**Config Directory with Optional Submodule Pattern**

- Create a top-level `config/` directory containing all deployment-specific files (env, RabbitMQ, Grafana, etc.).
- Optionally, manage this directory (or the whole deployment root) as a separate git repository for each site, with the main application code as a submodule (e.g., in `game-scheduler/`).
- Place all Docker Compose files at the root or in a `deploy/` directory, referencing config files from `config/`.
- Use `.env` files for environment variables, and keep secrets out of the main codebase.
- Document the structure and update process for deployments.

## Implementation Guidance

### Current Project Structure Analysis
- **Deployment config files currently distributed across:**
  - `env/` - Environment files (env.dev, env.prod, env.staging, env.e2e, env.int)
  - `rabbitmq/` - RabbitMQ configuration (rabbitmq.conf)
  - `grafana-alloy/` - Grafana Alloy configuration (config.alloy, dashboards/, docs)
  - Root-level Compose files (compose.yaml, compose.prod.yaml, compose.staging.yaml, compose.override.yaml, compose.e2e.yaml, compose.int.yaml)

- **Current volume mounts in compose.yaml:**
  - `${HOST_WORKSPACE_FOLDER:-.}/rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro`
  - Grafana Alloy mounts from `grafana-alloy/`

- **Current Compose override pattern:**
  - Base: `compose.yaml` (production-ready, complete service definitions)
  - Development: `compose.override.yaml` (auto-loaded, adds volume mounts for hot-reload)
  - Environment-specific: `compose.prod.yaml`, `compose.staging.yaml` (layered overrides)
  - Usage: `docker compose --env-file env/env.prod up -d`

### What Will Have to Change

**1. Directory Structure Reorganization**
- Create top-level `config/` directory
- Move files to new locations:
  - `env/` → `config/env/`
  - `rabbitmq/rabbitmq.conf` → `config/rabbitmq/rabbitmq.conf`
  - `grafana-alloy/config.alloy` → `config/grafana-alloy/config.alloy`
  - `grafana-alloy/dashboards/` → `config/grafana-alloy/dashboards/`
  - Optionally: Move Grafana docs or keep in project root

**2. Docker Compose File Updates**
- Update all volume mount paths in `compose.yaml`:
  - `${HOST_WORKSPACE_FOLDER:-.}/rabbitmq/rabbitmq.conf` → `${HOST_WORKSPACE_FOLDER:-.}/config/rabbitmq/rabbitmq.conf`
  - Update Grafana Alloy volume mounts similarly
- Update `--env-file` references in documentation:
  - `--env-file env/env.prod` → `--env-file config/env/env.prod`

**3. Scripts and Documentation Updates**
- Update any scripts in `scripts/` that reference config file paths
- Update deployment documentation (DEPLOYMENT_QUICKSTART.md, etc.)
- Update compose file comments to reflect new paths

**4. Git Configuration**
- Update `.gitignore` if needed to exclude sensitive config
- Consider making `config/` directory suitable for per-site customization

### How Docker Compose Overrides Help

**Current Override Pattern (Already in Use):**
The project already uses Compose layering effectively:
- **Base file** (`compose.yaml`): Complete production-ready definitions
- **Auto-loaded override** (`compose.override.yaml`): Development hot-reload volumes
- **Environment overrides** (`compose.prod.yaml`, `compose.staging.yaml`): Environment-specific settings

**Benefits for Config Directory Migration:**
1. **Base Compose stays generic**: `compose.yaml` references `config/` paths that work across all environments
2. **Environment-specific config overrides**: Each override file can mount different config subdirectories
3. **Per-site customization**: A site-specific repo can provide its own override file with custom config paths
4. **Clean separation**: Production uses layered files, development gets hot-reload automatically

**Example Usage After Migration:**
```bash
# Production with config directory
docker compose -f compose.yaml -f compose.prod.yaml --env-file config/env/env.prod up -d

# Staging with config directory
docker compose -f compose.yaml -f compose.staging.yaml --env-file config/env/env.staging up -d

# Development (compose.override.yaml auto-loaded)
docker compose --env-file config/env/env.dev up
```

**Advanced Pattern for Per-Site Deployments:**
```
site-specific-repo/
  config/
    env/
      env.prod (site-specific values)
    rabbitmq/
      rabbitmq.conf (site-specific tuning)
    grafana-alloy/
      config.alloy (site-specific endpoints)
  game-scheduler/ (submodule of main repo)
  compose.site-override.yaml (optional site-specific overrides)
```

### Implementation Steps

- **Objectives**: Simplify deployment, enable per-site config management, support git-based config versioning, and keep code/config separation.

- **Key Tasks**:
  1. Create `config/` directory structure
  2. Move existing config files:
     - `env/` → `config/env/`
     - `rabbitmq/` → `config/rabbitmq/`
     - `grafana-alloy/` → `config/grafana-alloy/`
  3. Update all Compose files to reference new `config/` paths:
     - `compose.yaml` (base volume mounts)
     - `compose.override.yaml` (development mounts)
     - `compose.prod.yaml`, `compose.staging.yaml` (environment overrides)
  4. Update scripts and documentation
  5. Test all environments (dev, staging, prod) with new paths
  6. (Optional) Create template for per-site config repo with submodule pattern

- **Dependencies**: None (Git submodule support if using external config repo pattern)

- **Success Criteria**:
  - All deployment config is in `config/` directory
  - All environments work with new paths
  - Deployments are reproducible
  - Per-site customization is easy via separate config repo
  - Documentation reflects new structure
