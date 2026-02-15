<!-- markdownlint-disable-file -->

# Release Changes: Deployment Configuration Organization

**Related Plan**: 20251226-deployment-config-organization.plan.md
**Implementation Date**: 2025-12-26

## Summary

Reorganizing all deployment configuration files into a single `config/` directory to simplify per-site deployments and enable better separation of code from configuration.

## Changes

### Added

- config/env/ - New directory for environment variable files
- config/rabbitmq/ - New directory for RabbitMQ configuration
- config/grafana-alloy/ - New directory for Grafana Alloy configuration
- config/grafana-alloy/dashboards/ - New directory for Grafana Alloy dashboards
- config/env/env.dev - Moved from env/env.dev
- config/env/env.prod - Moved from env/env.prod
- config/env/env.staging - Moved from env/env.staging
- config/env/env.e2e - Moved from env/env.e2e
- config/env/env.int - Moved from env/env.int
- config/rabbitmq/rabbitmq.conf - Moved from rabbitmq/rabbitmq.conf
- config/grafana-alloy/config.alloy - Moved from grafana-alloy/config.alloy
- config/grafana-alloy/dashboards/ - Moved from grafana-alloy/dashboards/
- config/grafana-alloy/SETUP_GRAFANA_CLOUD.md - Moved from grafana-alloy/SETUP_GRAFANA_CLOUD.md
- config/env/env.example - Moved from .env.example
- docs/grafana-alloy/ - New directory for Grafana Alloy documentation
- docs/grafana-alloy/TESTING_PHASE1.md - Moved from grafana-alloy/TESTING_PHASE1.md
- docs/grafana-alloy/TESTING_PHASE2.md - Moved from grafana-alloy/TESTING_PHASE2.md
- docs/grafana-alloy/TESTING_PHASE3.md - Moved from grafana-alloy/TESTING_PHASE3.md
- docs/grafana-alloy/TESTING_PHASE4.md - Moved from grafana-alloy/TESTING_PHASE4.md
- docs/grafana-alloy/TESTING_PHASE5.md - Moved from grafana-alloy/TESTING_PHASE5.md
- docs/grafana-alloy/TESTING_PHASE6.md - Moved from grafana-alloy/TESTING_PHASE6.md
- docs/grafana-alloy/TESTING_PHASE7.md - Moved from grafana-alloy/TESTING_PHASE7.md

### Modified

- compose.yaml - Updated RabbitMQ and Grafana Alloy volume mount paths to reference config/ directory
- compose.override.yaml - No changes needed (no config path references)
- compose.prod.yaml - Updated env file path references in comments
- compose.staging.yaml - Updated env file path references in comments
- compose.e2e.yaml - Updated env file path references in comments
- compose.int.yaml - Updated env file path references in comments
- scripts/run-e2e-tests.sh - Updated to use config/env/env.e2e path
- scripts/run-integration-tests.sh - Updated to use config/env/env.int path
- DEPLOYMENT_QUICKSTART.md - Updated all env file path references to config/env/
- README.md - Updated all env file path references to config/env/
- RUNTIME_CONFIG.md - Updated Grafana Alloy setup guide path to config/grafana-alloy/
- RUNTIME_CONFIG.md - Updated .env.example reference to config/env/env.example
- frontend/README.md - Updated .env.example reference to config/env/env.example
- .gitignore - No changes needed (existing env/ pattern matches config/env/ files)

### Removed

- env/ - Removed after moving all files to config/env/
- rabbitmq/ - Removed after moving all files to config/rabbitmq/
- grafana-alloy/ - Removed after moving all files to config/grafana-alloy/

## Validation

### Phase 4: Testing and Validation

- Development environment: Validated with `docker compose config` - all volume mounts correctly reference config/ paths
- Staging environment: Validated with `docker compose -f compose.yaml -f compose.staging.yaml --env-file config/env/env.staging config` - configuration loads successfully
- Production environment: Validated with `docker compose -f compose.yaml -f compose.prod.yaml --env-file config/env/env.prod config` - configuration is correct
- All RabbitMQ and Grafana Alloy config paths verified in resolved compose configurations
