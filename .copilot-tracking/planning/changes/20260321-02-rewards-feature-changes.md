<!-- markdownlint-disable-file -->

# Changes: Rewards Feature

## Summary

Add `rewards` (nullable text) and `remind_host_rewards` (bool) fields to game sessions and
templates, with Discord spoiler display, a host DM reminder on completion, and a
"Save and Archive" shortcut button in the frontend.

## Added

- `.copilot-tracking/planning/changes/20260321-02-rewards-feature-changes.md` — this changes tracking file

## Modified

- `shared/models/game.py` — added `rewards: Mapped[str | None]` (Text, nullable) and `remind_host_rewards: Mapped[bool]` (Boolean, server_default false) to `GameSession`; added `Boolean` import
- `shared/models/template.py` — added `remind_host_rewards: Mapped[bool]` (Boolean, server_default false) to `GameTemplate` pre-populated fields section
- `shared/schemas/game.py` — added `rewards`, `remind_host_rewards`, `archive_delay_seconds` to `GameUpdateRequest`; added `remind_host_rewards` to `GameCreateRequest`; added `rewards`, `remind_host_rewards`, `archive_channel_id` to `GameResponse`
- `shared/schemas/template.py` — added `remind_host_rewards` to `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, and `TemplateListItem`

## Removed

_(none yet)_

---

## Phase Progress

- [x] Phase 1: Database Migration
- [x] Phase 2: Backend Models & Schemas
- [ ] Phase 3: API Service & Routes
- [ ] Phase 4: Bot Formatters & Handlers
- [ ] Phase 5: Frontend
- [ ] Phase 6: Tests (TDD)
