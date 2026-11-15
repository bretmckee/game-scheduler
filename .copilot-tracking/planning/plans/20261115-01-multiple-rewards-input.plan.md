---
applyTo: '.copilot-tracking/planning/changes/20261115-01-multiple-rewards-input-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Multiple Reward Entries Input

## Overview

Let hosts enter each reward in its own text box (add/remove), stored as a JSON list and displayed per entry on web and Discord without exceeding Discord limits.

## Objectives

- Store rewards as JSON list[str] with a safe data migration
- API validates and caps entries (20 entries, 2000 chars each); empty -> NULL
- Discord embed shows per-entry spoiler fields, or a single link field when they do not fit
- Form with "+ Add another reward" and per-row remove; GameDetails shows per-entry blocks

## Research Summary

### Project Files

- shared/models/game.py, shared/schemas/game.py, services/api/routes/games.py, services/api/services/games.py - rewards storage and API
- services/bot/formatters/game_message.py - embed rendering
- frontend/src/components/GameForm.tsx, frontend/src/pages/EditGame.tsx, frontend/src/pages/GameDetails.tsx - UI

### External References

- .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md - validated research
- Source: https://docs.discord.com/developers/resources/message - embed limits

### Standards References

- .github/instructions/test-driven-development.instructions.md - TDD rules
- .github/instructions/python.instructions.md, unit-tests.instructions.md, integration-tests.instructions.md, reactjs.instructions.md, copyright-headers.instructions.md

## Implementation Checklist

### [x] Phase 1: Storage, Migration and API

- [x] Task 1.1: Constants, migration SQL module, migration integration tests
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 13-28)

- [x] Task 1.2: Alembic revision, model, schema, route, service, formatter signature, existing test updates
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 29-51)

### [x] Phase 2: Discord Embed Fit-vs-Link (TDD)

- [x] Task 2.1: RED - stub and xfail unit tests
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 54-64)

- [x] Task 2.2: GREEN/REFACTOR - fit decision, non-optional game_url
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 65-75)

- [x] Task 2.3: E2E tests (inline, at-limit, overflow, archive)
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 76-85)

### [ ] Phase 3: Frontend

- [ ] Task 3.1: Constants, types, GameDetails per-entry display
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 88-98)

- [ ] Task 3.2: GameForm list UI, EditGame JSON submit, Save-and-Archive gate
  - Details: .copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md (Lines 99-109)

## Dependencies

- One new Alembic migration; no new libraries
- Real Postgres (integration) and Discord (e2e) environments

## Success Criteria

- Existing string rewards migrate to one-entry lists and display unchanged
- Multiple entries with newlines round-trip; blanks dropped; clearing stores NULL
- Discord inline-or-link behavior verified incl. at-limit e2e
- API rejects >20 entries or >2000-char entries
- Each phase passes pytest tests/unit, mypy, and (Phase 3) npm build/test
