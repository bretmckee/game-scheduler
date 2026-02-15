---
applyTo: '.copilot-tracking/changes/20260205-channel-lazy-loading-guild-setup-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Channel Lazy Loading and Guild Setup Flow

## Overview

Eliminate channel staleness by fetching channels from Discord dynamically and implement lazy creation of ChannelConfiguration records with improved guild setup workflow.

## Objectives

- Fetch channel lists from Discord API with caching instead of storing in database
- Lazy-create ChannelConfiguration records only when templates/games use them
- Implement per-guild transaction isolation for partial success during bulk setup
- Maintain "every guild needs a template" invariant with improved UX
- Remove `new_channels` count from sync response (always 0 with lazy creation)

## Research Summary

### Project Files

- services/api/routes/guilds.py - Guild endpoints including channel listing
- services/api/services/guild_service.py - Guild sync and setup logic
- shared/discord/client.py - Discord API client with get_guild_channels method
- shared/models/channel.py - ChannelConfiguration model with is_active flag
- frontend/src/pages/TemplateManagement.tsx - Template form with channel dropdown

### External References

- #file:../research/20260205-channel-lazy-loading-guild-setup-research.md - Complete architecture analysis
- #fetch:https://discord.com/developers/docs/resources/guild#get-guild-channels - Discord API documentation

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding standards
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript standards
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Transaction management

## Implementation Checklist

### [ ] Phase 1: Dynamic Channel Fetching with Caching

- [ ] Task 1.1: Add Redis caching to get_guild_channels() method
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 15-35)

- [ ] Task 1.2: Update list_guild_channels endpoint to fetch from Discord
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 37-60)

- [ ] Task 1.3: Update TemplateManagement page to handle Discord channels
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 62-85)

- [ ] Task 1.4: Add cache key for guild channels
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 87-105)

### [ ] Phase 2: Guild Setup Flow with Per-Guild Transactions

- [ ] Task 2.1: Create discover endpoint for new guilds
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 107-135)

- [ ] Task 2.2: Create setup-batch endpoint with per-guild transactions
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 137-180)

- [ ] Task 2.3: Add GuildDiscoveryResponse and GuildSetupBatchRequest schemas
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 182-210)

- [ ] Task 2.4: Build frontend setup modal with channel dropdowns
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 212-255)

- [ ] Task 2.5: Update sync flow to call discover then show modal
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 257-285)

### [ ] Phase 3: Remove Channel Sync and Update Response Schema

- [ ] Task 3.1: Remove channel creation from \_create_guild_with_channels_and_template
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 287-310)

- [ ] Task 3.2: Simplify sync_user_guilds to discovery-only
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 312-335)

- [ ] Task 3.3: Remove new_channels from GuildSyncResponse schema
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 337-355)

- [ ] Task 3.4: Update frontend to handle new sync response format
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 357-380)

### [ ] Phase 4: Testing and Documentation

- [ ] Task 4.1: Update integration tests for new flow
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 382-410)

- [ ] Task 4.2: Add E2E tests for guild setup modal
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 412-440)

- [ ] Task 4.3: Update API documentation
  - Details: .copilot-tracking/details/20260205-channel-lazy-loading-guild-setup-details.md (Lines 442-460)

## Dependencies

- Redis caching infrastructure (CacheTTL.DISCORD_CHANNEL = 300 seconds)
- SQLAlchemy nested transaction support (db.begin_nested())
- Discord API bot token with channel read permissions
- Existing get_guild_channels() method in DiscordAPIClient

## Success Criteria

- New Discord channels appear in template dropdowns after cache TTL (5 minutes)
- Guild sync shows setup modal for new guilds with channel selection
- Multiple guilds can be configured in single operation
- Partial failures don't block successful guild setups
- Every guild has exactly one default template after setup
- ChannelConfiguration records only created for channels actually used
- All existing guilds/templates/games continue working
- Integration and E2E tests pass
