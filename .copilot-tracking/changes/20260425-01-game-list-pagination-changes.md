# Change Record: Game List Pagination

## Summary

Add server-side pagination to the game list API and wire up MUI `Pagination`
controls in BrowseGames and MyGames, replacing unbounded fetches with 25-game
pages.

## Status: Complete (Phases 1–4 done)

---

## Added

- `tests/unit/services/api/services/test_games_service.py`: added
  `test_list_games_role_host_filters_count_query`,
  `test_list_games_role_host_filters_main_query`,
  `test_list_games_role_participant_filters_count_query`,
  `test_list_games_role_participant_filters_main_query` — verify role filter
  SQL is applied to both the count and main queries for each role value
- `.copilot-tracking/changes/20260425-01-game-list-pagination-changes.md`:
  this change record

## Modified

- `shared/schemas/game.py`: added `limit: int` and `offset: int` required
  fields to `GameListResponse` with descriptions
- `services/api/services/games.py`: added `role: str | None` and
  `user_id: str | None` params to `list_games`; lowered `limit` default from
  50 → 25; added host and participant role-filter SQL blocks after existing
  guild/channel/status filters
- `services/api/routes/games.py`: added `role` query param; lowered limit
  default and max from 50/100 → 25/25; fixed `total` to use the DB
  pre-auth count instead of `len(authorized_games)`; passed `limit` and
  `offset` into `GameListResponse`
- `tests/unit/services/api/routes/test_games_routes.py`: added `role=None`
  and corrected `limit=50` → `limit=25` at all 5 `list_games` call sites
- `tests/unit/services/api/routes/test_games_endpoint_errors.py`: updated
  `test_list_games_filters_unauthorized_games` to assert `total == 1`
  (DB pre-auth count) instead of `total == 0`; added `role=None`; fixed
  `limit=50` → `limit=25`
- `frontend/src/types/index.ts`: made `limit` and `offset` required (removed
  `?`) in `GameListResponse` interface
- `frontend/src/pages/BrowseGames.tsx`: added `Pagination` MUI import;
  added `PAGE_SIZE = 25`; added `page` and `total` state; added `limit` and
  `offset` to API params; reset `page` to 1 on filter changes; render MUI
  `Pagination` when `total > PAGE_SIZE`
- `frontend/src/pages/MyGames.tsx`: added `Pagination` MUI import;
  added `PAGE_SIZE = 25`; added per-tab `hostedPage`, `joinedPage`,
  `hostedTotal`, `joinedTotal` state; replaced single games fetch with
  three-way `Promise.all` using `role: 'host'` and `role: 'participant'`
  params; render MUI `Pagination` in each tab when total exceeds page size;
  updated tab labels to show totals
- `frontend/src/pages/__tests__/BrowseGames.test.tsx`: added `limit`/`offset`
  to all existing mock responses; promoted 3 `it.fails` pagination tests to
  regular passing tests; re-added second mock in page-2 navigation test
- `frontend/src/pages/__tests__/MyGames.test.tsx`: added `limit`/`offset` to
  `mockGamesResponse`; updated SSE tests to mock 4 calls (hosted + joined +
  guilds + SSE); promoted 3 `it.fails` pagination tests to regular passing
  tests with correct separate-call mock setup

## Removed

_(nothing yet)_
