---
applyTo: '.copilot-tracking/changes/20251127-frontend-docker-build-optimization-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: Frontend Docker Build Optimization

## Overview

Optimize frontend Docker build by implementing selective COPY instructions (primary control) with comprehensive .dockerignore (safety net) to reduce build context size from 413MB to <300KB and improve layer caching efficiency.

## Objectives

- Reduce Docker build context size from ~413MB to <300KB
- Improve incremental build times for source-only changes to <10 seconds
- Implement explicit COPY control to prevent accidental file inclusion
- Add .dockerignore as safety net against node_modules and unnecessary files
- Maintain dependency layer cache across source code changes

## Research Summary

### Project Files
- docker/frontend.Dockerfile - Current multi-stage build with broad COPY instruction at line 11
- frontend/ - Contains src/ (268KB), and potentially node_modules (413MB if present)

### External References
- #file:../research/20251127-frontend-docker-build-optimization-research.md - Comprehensive analysis showing selective COPY + .dockerignore strategy
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices emphasizing layer caching and selective COPY

### Standards References
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Container optimization guidelines

## Implementation Checklist

### [ ] Phase 1: Create .dockerignore Safety Net

- [ ] Task 1.1: Create comprehensive .dockerignore in project root
  - Details: .copilot-tracking/details/20251127-frontend-docker-build-optimization-details.md (Lines 11-70)

### [ ] Phase 2: Implement Selective COPY Instructions

- [ ] Task 2.1: Replace broad COPY with explicit selective COPY statements
  - Details: .copilot-tracking/details/20251127-frontend-docker-build-optimization-details.md (Lines 72-124)

### [ ] Phase 3: Validation and Testing

- [ ] Task 3.1: Test Docker build with optimizations
  - Details: .copilot-tracking/details/20251127-frontend-docker-build-optimization-details.md (Lines 126-155)

- [ ] Task 3.2: Verify build context size reduction
  - Details: .copilot-tracking/details/20251127-frontend-docker-build-optimization-details.md (Lines 157-180)

- [ ] Task 3.3: Validate incremental build performance
  - Details: .copilot-tracking/details/20251127-frontend-docker-build-optimization-details.md (Lines 182-207)

## Dependencies

- Docker
- docker-compose

## Success Criteria

- Build context size reduced to <300KB
- Incremental builds complete in <10 seconds
- Dependencies layer cache preserved across source changes
- Production image builds successfully
- Only explicitly listed files can enter build context
- .dockerignore provides backup protection
