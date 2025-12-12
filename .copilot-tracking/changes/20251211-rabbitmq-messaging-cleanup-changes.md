<!-- markdownlint-disable-file -->

# Release Changes: RabbitMQ Messaging Architecture Cleanup

**Related Plan**: 20251211-rabbitmq-messaging-cleanup-plan.instructions.md
**Implementation Date**: 2025-12-11

## Summary

Fix DLQ exponential growth bug and remove unused RabbitMQ queues by implementing a dedicated retry service with per-queue DLQs and clear ownership.

## Changes

### Added

### Modified

- shared/messaging/infrastructure.py - Removed unused queue constants (QUEUE_API_EVENTS, QUEUE_SCHEDULER_EVENTS, QUEUE_DLQ)
- shared/messaging/infrastructure.py - Updated PRIMARY_QUEUES and QUEUE_BINDINGS to only include bot_events and notification_queue
- scripts/init_rabbitmq.py - Removed unused queue declarations (api_events, scheduler_events, DLQ)
- tests/integration/test_rabbitmq_infrastructure.py - Removed tests for unused queues (api_events, scheduler_events, DLQ)

### Removed

- tests/integration/test_rabbitmq_dlq.py - Removed tests for shared DLQ (will be replaced with per-queue DLQ tests in Phase 2)

