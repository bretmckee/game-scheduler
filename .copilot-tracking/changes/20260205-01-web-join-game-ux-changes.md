<!-- markdownlint-disable-file -->

# Release Changes: Web Join Game UX with Real-Time Cross-Platform Sync

**Related Plan**: 20260205-01-web-join-game-ux-plan.instructions.md
**Implementation Date**: 2026-02-07

## Summary

Enable real-time synchronization of game join/leave actions across web and Discord interfaces using SSE, allowing users to see updates on web pages when they interact with Discord buttons without manual refresh.

## Changes

### Added

- services/api/services/sse_bridge.py - SSE bridge service that consumes RabbitMQ game.updated.* events and broadcasts to authorized SSE connections with server-side guild filtering
- services/api/routes/sse.py - SSE endpoint at /api/v1/sse/game-updates with FastAPI StreamingResponse, authentication, and keepalive pings
- tests/services/api/services/test_sse_bridge.py - Unit tests for SSE bridge service covering guild filtering, connection management, and error handling
- tests/services/api/routes/test_sse.py - Unit tests for SSE endpoint covering authentication, connection registration, keepalive, and cleanup
- tests/services/bot/events/test_publisher.py - Updated test_publish_game_updated to include guild_id parameter and verify routing key format

### Modified

- services/api/app.py - Integrated SSE bridge into API service lifespan, registered SSE router, started bridge as background task on startup
- services/api/services/games.py - Added guild_id to GAME_UPDATED event data and routing key format game.updated.{guild_id}
- services/bot/events/publisher.py - Added guild_id parameter to publish_game_updated method and updated routing key format
- services/bot/handlers/join_game.py - Pass guild_id to publisher when publishing game.updated events
- services/bot/handlers/leave_game.py - Pass guild_id to publisher when publishing game.updated events
- shared/messaging/infrastructure.py - Added QUEUE_WEB_SSE_EVENTS queue with game.updated.* binding, added corresponding DLQ queue and binding

### Removed
