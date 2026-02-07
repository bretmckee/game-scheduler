<!-- markdownlint-disable-file -->

# Release Changes: Web Join Game UX with Real-Time Cross-Platform Sync

**Related Plan**: 20260205-01-web-join-game-ux-plan.instructions.md
**Implementation Date**: 2026-02-07

## Summary

Enable real-time synchronization of game join/leave actions across web and Discord interfaces using SSE, allowing users to see updates on web pages when they interact with Discord buttons without manual refresh.

## Changes

### Added

- services/api/services/sse_bridge.py - SSE bridge service that consumes RabbitMQ game.updated.\* events and broadcasts to authorized SSE connections with server-side guild filtering
- services/api/routes/sse.py - SSE endpoint at /api/v1/sse/game-updates with FastAPI StreamingResponse, authentication, and keepalive pings
- tests/services/api/services/test_sse_bridge.py - Unit tests for SSE bridge service covering guild filtering, connection management, and error handling
- tests/services/api/routes/test_sse.py - Unit tests for SSE endpoint covering authentication, connection registration, keepalive, and cleanup
- tests/services/bot/events/test_publisher.py - Updated test_publish_game_updated to include guild_id parameter and verify routing key format
- frontend/src/hooks/useGameUpdates.ts - React hook for SSE connection with EventSource, handles game_updated events with guild filtering
- .github/instructions/copyright-headers.instructions.md - Instructions to prevent manual copyright header addition, rely on autocopyright pre-commit hook
- frontend/src/hooks/**tests**/useGameUpdates.test.ts - Unit tests for useGameUpdates hook (10 tests, 100% coverage) with refactored helper functions to eliminate duplication
- frontend/src/components/**tests**/GameCard.test.tsx - Updated tests for GameCard join/leave functionality (26 total tests, 93.3% coverage) with proper AuthContext mocking
- frontend/src/pages/**tests**/BrowseGames.test.tsx - SSE integration tests for BrowseGames (2 tests) covering callback invocation and game refetch
- frontend/src/pages/**tests**/MyGames.test.tsx - SSE integration tests for MyGames (2 tests) covering hosted and joined game updates
- frontend/src/test/setup.ts - Added global EventSource mock for consistent test environment
- tests/integration/test_sse_bridge.py - Comprehensive SSE integration tests (3 tests, 383 lines) covering single client event delivery, guild-based authorization filtering, and multiple concurrent clients (5) broadcasting
- tests/unit/services/api/services/test_sse_bridge.py - Unit tests for SSEGameUpdateBridge.set_keepalive_interval() method with validation (positive, zero, negative values)

### Modified

- services/api/app.py - Integrated SSE bridge into API service lifespan, registered SSE router, started bridge as background task on startup
- services/api/services/games.py - Added guild_id to GAME_UPDATED event data and routing key format game.updated.{guild_id}
- services/bot/events/publisher.py - Added guild_id parameter to publish_game_updated method and updated routing key format
- services/bot/handlers/join_game.py - Pass guild_id to publisher when publishing game.updated events
- services/bot/handlers/leave_game.py - Pass guild_id to publisher when publishing game.updated events
- shared/messaging/infrastructure.py - Added QUEUE_WEB_SSE_EVENTS queue with game.updated.\* binding, added corresponding DLQ queue and binding
- frontend/src/components/GameCard.tsx - Added join/leave buttons with authorization logic, optimistic updates, loading states, and error handling
- frontend/src/hooks/useGameUpdates.ts - Updated to support optional guildId parameter for filtering, accepts all authorized events when guildId is undefined
- frontend/src/pages/BrowseGames.tsx - Added useGameUpdates hook with handleGameUpdate callback, passes onGameUpdate to GameCard components for real-time sync
- frontend/src/pages/MyGames.tsx - Added useGameUpdates hook with handleGameUpdate callback for both hosted and joined games, passes onGameUpdate to GameCard components
- shared/messaging/publisher.py - **(Infrastructure fix outside plan)** Fixed EventPublisher.connect() to respect connection parameter instead of unconditionally using singleton, preventing event loop isolation issues in tests where connections from closed event loops were reused
- services/api/services/sse_bridge.py - **(Infrastructure fix outside plan)** Added set_keepalive_interval() method for configurable SSE keepalive intervals (default 30s, tests use 1s for faster execution), removed verbose debug logging

## Testing Status

### Phase 3 Test Coverage (Complete)

- **useGameUpdates hook**: 10 tests, 100% coverage - Connection, events, filtering, error handling, guildId changes, cleanup
- **GameCard component**: 26 tests, 93.3% coverage - Join/leave buttons, authorization, loading states, error handling, optimistic updates
- **BrowseGames page**: 2 SSE integration tests - SSE callback invocation, game refetch, state updates
- **MyGames page**: 2 SSE integration tests - Hosted and joined game updates via SSE callbacks
- **All tests passing**: 136 tests passing across frontend
- **Coverage requirement met**: 80%+ diff coverage achieved

### Infrastructure Testing (Outside Plan - Bug Fix)

- **SSE integration tests**: 3 tests validating RabbitMQ-to-SSE event flow
  - test_sse_receives_rabbitmq_game_updated_events: Single client receives events from RabbitMQ
  - test_sse_filters_events_by_guild_membership: Server-side guild authorization filtering
  - test_sse_broadcasts_to_multiple_clients: 5 concurrent clients receive same event (previously flaky, now validated with 10/10 consecutive successful runs)
- **SSE configuration tests**: Unit tests for keepalive interval validation (positive, zero, negative)
- **Root cause**: EventPublisher was unconditionally discarding provided connections and reusing singleton from closed event loops
- **Solution**: Modified connect() to respect connection parameter, only use singleton when no connection provided
- **Impact**: Production code unchanged (always uses singleton), tests now properly isolated

### Removed
