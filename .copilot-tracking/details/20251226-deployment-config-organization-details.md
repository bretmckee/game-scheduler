<!-- markdownlint-disable-file -->

# Task Details: Deployment Configuration Organization

## Research Reference

**Source Research**: #file:../research/20251226-deployment-config-organization-research.md

## Phase 1: Create Config Directory Structure

### Task 1.1: Create config directory hierarchy

Create the new `config/` directory structure to consolidate all deployment configuration files.

- **Files**:
  - config/ (new directory)
  - config/env/ (new directory)
  - config/rabbitmq/ (new directory)
  - config/grafana-alloy/ (new directory)
  - config/grafana-alloy/dashboards/ (new directory)
- **Success**:
  - All new directories exist
  - Directory structure matches intended layout
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 90-96) - Current project structure
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 113-122) - Directory reorganization plan
- **Dependencies**:
  - None

### Task 1.2: Move environment files

Move all environment variable files from `env/` to `config/env/` directory.

- **Files**:
  - env/env.dev → config/env/env.dev
  - env/env.prod → config/env/env.prod
  - env/env.staging → config/env/env.staging
  - env/env.e2e → config/env/env.e2e
  - env/env.int → config/env/env.int
- **Success**:
  - All env files exist in config/env/
  - Old env/ directory can be removed
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 115-117) - File move specifications
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Move RabbitMQ configuration

Move RabbitMQ configuration from `rabbitmq/` to `config/rabbitmq/` directory.

- **Files**:
  - rabbitmq/rabbitmq.conf → config/rabbitmq/rabbitmq.conf
- **Success**:
  - RabbitMQ config exists in config/rabbitmq/
  - Old rabbitmq/ directory can be removed
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 117-118) - RabbitMQ file move
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 103-104) - Current volume mount paths
- **Dependencies**:
  - Task 1.1 completion

### Task 1.4: Move Grafana Alloy configuration

Move Grafana Alloy configuration from `grafana-alloy/` to `config/grafana-alloy/` directory.

- **Files**:
  - grafana-alloy/config.alloy → config/grafana-alloy/config.alloy
  - grafana-alloy/dashboards/ → config/grafana-alloy/dashboards/
- **Success**:
  - Grafana Alloy config exists in config/grafana-alloy/
  - Dashboards directory exists in config/grafana-alloy/dashboards/
  - Grafana documentation can remain in project root or move to config/
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 118-120) - Grafana file move
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 104-105) - Current volume mounts
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Update Docker Compose Files

### Task 2.1: Update compose.yaml volume mounts

Update all volume mount paths in the base compose.yaml to reference the new `config/` directory structure.

- **Files**:
  - compose.yaml - Update RabbitMQ and Grafana Alloy volume mount paths
- **Success**:
  - All volume mounts reference config/ paths
  - Compose file syntax is valid
  - No broken path references
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 124-128) - Compose file update requirements
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 103-105) - Current volume mount paths
- **Dependencies**:
  - Phase 1 completion (all files moved)

### Task 2.2: Update compose.override.yaml volume mounts

Update development override file to reference new config paths for hot-reload volumes.

- **Files**:
  - compose.override.yaml - Update any config-related volume mounts
- **Success**:
  - All config volume mounts use config/ paths
  - Development hot-reload still works
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 106-110) - Current override pattern
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 142-152) - Compose override benefits
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update environment-specific compose files

Update production and staging compose files to reference new env file paths.

- **Files**:
  - compose.prod.yaml - Update any config references
  - compose.staging.yaml - Update any config references
  - compose.e2e.yaml - Update any config references
  - compose.int.yaml - Update any config references
- **Success**:
  - All environment-specific overrides reference config/ paths
  - Environment files load correctly with new paths
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 127-128) - Env file documentation updates
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 154-162) - Example usage after migration
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Update Scripts and Documentation

### Task 3.1: Update scripts with config file references

Update all scripts that reference config files to use new config/ paths.

- **Files**:
  - scripts/ directory - Any scripts referencing env/, rabbitmq/, or grafana-alloy/
  - Potentially: scripts/init_rabbitmq.py or other config-dependent scripts
- **Success**:
  - All scripts reference correct config/ paths
  - Scripts execute without path errors
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 130-131) - Script update requirements
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Update deployment documentation

Update all deployment and configuration documentation to reflect new config directory structure.

- **Files**:
  - DEPLOYMENT_QUICKSTART.md - Update env file paths and deployment commands
  - RUNTIME_CONFIG.md - Update config file locations
  - README.md - Update any config references
  - docker/*/README.md - Update any config references
  - grafana-alloy/SETUP_GRAFANA_CLOUD.md - Update config file paths
- **Success**:
  - All documentation reflects new config/ structure
  - Command examples use correct paths
  - No references to old env/, rabbitmq/, grafana-alloy/ locations for config
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 132-133) - Documentation update requirements
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 154-162) - Example usage patterns
- **Dependencies**:
  - Phase 2 completion

### Task 3.3: Update .gitignore if needed

Review and update .gitignore to handle the new config/ directory appropriately for sensitive files.

- **Files**:
  - .gitignore - Update patterns for config directory
- **Success**:
  - Sensitive config files are excluded from git
  - Template or example config files can be tracked
  - Config directory structure is appropriately managed
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 135-137) - Git configuration notes
- **Dependencies**:
  - Phase 1 completion

## Phase 4: Testing and Validation

### Task 4.1: Test development environment

Verify that the development environment works correctly with the new config structure.

- **Files**:
  - All config files in config/ directory
  - compose.yaml + compose.override.yaml (auto-loaded)
- **Success**:
  - `docker compose up` starts all services successfully
  - Services read config from new config/ paths
  - Hot-reload and development features work
  - No path-related errors in logs
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 160-162) - Development usage example
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 200-202) - Testing requirements
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Test staging environment

Verify that the staging environment configuration works with new config structure.

- **Files**:
  - config/env/env.staging
  - compose.yaml + compose.staging.yaml
- **Success**:
  - `docker compose -f compose.yaml -f compose.staging.yaml --env-file config/env/env.staging up` works
  - Staging-specific configuration loads correctly
  - Services start and operate normally
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 157-159) - Staging usage example
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 200-202) - Testing requirements
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Test production environment configuration

Verify that the production environment configuration is correct (without actually running prod).

- **Files**:
  - config/env/env.prod
  - compose.yaml + compose.prod.yaml
- **Success**:
  - `docker compose -f compose.yaml -f compose.prod.yaml --env-file config/env/env.prod config` validates successfully
  - All production configuration paths are correct
  - No missing volume mount paths
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 154-156) - Production usage example
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 200-205) - Success criteria
- **Dependencies**:
  - Task 4.2 completion

## Phase 5: Documentation and Templates

### Task 5.1: Create per-site deployment template documentation

Create documentation explaining how to use the new config structure for per-site deployments.

- **Files**:
  - docs/PER_SITE_DEPLOYMENT.md (new) - Document per-site config pattern
- **Success**:
  - Documentation explains config directory structure
  - Examples show how to create site-specific config repos
  - Instructions for using git submodules or separate config repos
  - Template structure provided for per-site deployments
- **Research References**:
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 163-174) - Advanced per-site pattern
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 46-56) - Config directory and submodule patterns
  - #file:../research/20251226-deployment-config-organization-research.md (Lines 70-88) - Recommended approach
- **Dependencies**:
  - Phase 4 completion

## Dependencies

- Git (for moving files with history)
- Docker and Docker Compose

## Success Criteria

- All deployment config is in `config/` directory
- All environments work with new paths
- Deployments are reproducible
- Per-site customization pattern is documented
- Documentation reflects new structure
