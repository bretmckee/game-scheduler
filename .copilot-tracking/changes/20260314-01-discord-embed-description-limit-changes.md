<!-- markdownlint-disable-file -->

# Changes: Discord Embed Description Length Fix

## Date

2026-03-14

## Added

- `shared/utils/limits.py` — added `DISCORD_EMBED_TOTAL_LIMIT = 6000`, `DISCORD_EMBED_TOTAL_SAFE_LIMIT = 5900`, `MAX_DESCRIPTION_LENGTH = 2000`, `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH = 100`
- `services/bot/formatters/game_message.py` — added `_trim_embed_if_needed` static method that dynamically trims `embed.description` when total embed length exceeds `DISCORD_EMBED_TOTAL_SAFE_LIMIT`
- `tests/services/bot/formatters/test_game_message.py` — added `TestTrimEmbedIfNeeded` class with six tests (short description unchanged, long description under limit preserved, trim when over limit, None description, empty description, 2,000-char description in normal game scenario)
- `tests/shared/schemas/__init__.py` — new package for shared schema tests
- `tests/shared/schemas/test_game_schema.py` — tests verifying 2,000-char description is accepted and 2,001-char is rejected for `GameCreateRequest` and `GameUpdateRequest`
- `tests/shared/schemas/test_template_schema.py` — tests verifying 2,000-char description is accepted and 2,001-char is rejected for `TemplateCreateRequest` and `TemplateUpdateRequest`

## Modified

- `shared/utils/limits.py` — removed `MAX_STRING_DISPLAY_LENGTH = 100`; replaced with four purpose-named constants
- `services/api/routes/export.py` — replaced `MAX_STRING_DISPLAY_LENGTH` import and usage with `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH`
- `services/bot/formatters/game_message.py` — replaced `MAX_STRING_DISPLAY_LENGTH` import with `DISCORD_EMBED_TOTAL_SAFE_LIMIT`; removed 97-char truncation logic from `_prepare_description_and_urls`; `create_game_embed` now calls `_trim_embed_if_needed` before returning
- `tests/services/bot/formatters/test_game_message.py` — updated `test_prepare_description_and_urls_truncates_long_description` to `test_prepare_description_and_urls_passes_long_description_unchanged` (truncation no longer occurs in that method); added `import discord`, `import pytest`, and `DISCORD_EMBED_TOTAL_SAFE_LIMIT` import
- `shared/discord/game_embeds.py` — imported `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH`; replaced hardcoded `[:100]` snippet slice with `[:GAME_LIST_DESCRIPTION_SNIPPET_LENGTH]`
- `shared/schemas/game.py` — changed `max_length=4000` to `max_length=2000` on `GameCreateRequest.description` and `GameUpdateRequest.description`
- `shared/schemas/template.py` — changed `max_length=4000` to `max_length=2000` on `TemplateCreateRequest.description` and `TemplateUpdateRequest.description`
- `frontend/src/constants/ui.ts` — changed `MAX_DESCRIPTION_LENGTH` from `4000` to `2000`
- `frontend/src/components/GameForm.tsx` — removed two local `MAX_DESCRIPTION_LENGTH = 2000` constants; both call sites now use `UI.MAX_DESCRIPTION_LENGTH`
- `frontend/src/components/__tests__/TemplateForm.validation.test.tsx` — updated `shows character counter for description` test assertion from `4000` to `2000`

## Removed

- `shared/utils/limits.py` — `MAX_STRING_DISPLAY_LENGTH = 100` constant removed

## Notes

- **Outside-plan change**: In Task 1.1, `game_message.py`'s import of `MAX_STRING_DISPLAY_LENGTH` was left in place temporarily (using `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH` as a transitional value) to keep existing tests passing, then fully updated in Task 2.1 as part of restructuring. This avoided a broken intermediate state between Phase 1 and Phase 2.
- **Task 2.1 deviation**: Per TDD RED phase, `create_game_embed` was not wired to call `_trim_embed_if_needed` until Task 2.3 (GREEN phase) to avoid breaking pre-existing tests during the stub phase.
