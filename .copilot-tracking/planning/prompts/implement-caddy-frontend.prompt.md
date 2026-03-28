---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Replace nginx Frontend with Caddy (SSL Termination)

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260328-01-caddy-frontend-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260328-01-caddy-frontend.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Dockerfile and compose changes
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**TDD note**: All changes in this plan are Dockerfiles, Caddyfiles (plain text), and YAML — none apply to TDD methodology per the test-driven-development instructions. Implement each task directly.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260328-01-caddy-frontend-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260328-01-caddy-frontend.plan.md, .copilot-tracking/planning/details/20260328-01-caddy-frontend-details.md, and .copilot-tracking/research/20260328-01-reverse-proxy-ssl-termination-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] `docker/frontend.Dockerfile` production stage replaced with `caddy:2-alpine`; assets copied to `/srv`
- [ ] `docker/Caddyfile.staging` created: plain HTTP on `:80`, all nginx behavior replicated
- [ ] `docker/Caddyfile.prod` created: `{$DOMAIN}` address with automatic HTTPS
- [ ] `compose.yaml` frontend `NGINX_LOG_LEVEL` renamed to `LOG_LEVEL`; `Caddyfile.staging` volume mount added
- [ ] `compose.staging.yaml` frontend `NGINX_LOG_LEVEL: debug` replaced with `LOG_LEVEL: debug`; `Caddyfile.staging` volume mount added
- [ ] `compose.prod.yaml` frontend updated with `Caddyfile.prod` mount, ports 80/443/443udp, `caddy_data` and `caddy_config` volumes; top-level `volumes:` section added
- [ ] `config/env/env.prod` and `config.template/env.template` contain `DOMAIN=` and `ACME_EMAIL=` entries
- [ ] `docker/frontend-nginx.conf` deleted; `grep -r "frontend-nginx.conf" .` returns no results
- [ ] Changes file updated continuously
