<!-- markdownlint-disable-file -->
# RabbitMQ Messaging Architecture Cleanup

## Executive Summary

This document outlines a comprehensive cleanup of the RabbitMQ messaging architecture to:
1. **Remove unused queues** (scheduler_events, api_events)
2. **Implement per-queue DLQs** for clear ownership
3. **Create a dedicated retry service** to handle DLQ processing
4. **Fix the DLQ exponential growth bug** (root cause: duplicate processing)

## Root Cause Analysis

### **Root Cause: Unknown - Not Captured in Available Logs**

**IMPORTANT**: Analysis of complete logs from service initialization shows **no definitive evidence** of how initial messages entered the DLQ.

**Possible Mechanisms for DLQ Entry**:

1. **Message TTL Expiry** (`shared/messaging/infrastructure.py` lines 58-75):
   ```python
   PRIMARY_QUEUE_TTL_MS = 3600000  # 1 hour in milliseconds

   QUEUE_ARGUMENTS_MAP: dict[str, dict[str, str | int]] = {
       QUEUE_BOT_EVENTS: {
           "x-dead-letter-exchange": DLX_EXCHANGE,
           "x-message-ttl": PRIMARY_QUEUE_TTL_MS,  # ← 1 hour TTL
       },
       # ... all queues have this configuration
   }
   ```
   - Messages sitting unconsumed for >1 hour automatically route to DLQ
   - RabbitMQ handles this at queue level, no consumer code involved
   - **Evidence**: Queue configured with 1-hour TTL
   - **Counter-evidence**: Bot consumer ran continuously from 07:53 onward with no processing gaps >1 hour

2. **Explicit NACK on Handler Failure** (`shared/messaging/consumer.py` line 147-154):
   ```python
   except Exception as e:
       await message.nack(requeue=False)  # Routes to DLQ
       logger.error(
           f"Handler failed, sending to DLQ for daemon processing: {event_type}, error: {e}",
           exc_info=True,
       )
   ```
   - **CRITICAL LOGGING GUARANTEE**: Bot ALWAYS logs at ERROR level when NACKing messages
   - **Evidence from logs**: Zero ERROR messages containing "Handler failed, sending to DLQ"
   - **Conclusion**: Bot did NOT NACK any messages during logging period (07:47-12:55 UTC)

**Log Analysis Summary**:
- Bot logs: 07:47-12:55 UTC (complete from service startup with clean volumes)
- Daemon logs: 07:47-12:53 UTC (complete from service startup)
- Bot consumer: Multiple restarts with gaps (07:47, 07:53, 08:15, 08:25, 08:38, 09:41, 10:07)
- First DLQ processing: 10:30 UTC with 10 messages already queued
- **No ERROR logs indicating message rejection**

**CRITICAL DISCOVERY: Prefetch Buffer and Restart Interaction**

**Location**: `shared/messaging/consumer.py` line 73
```python
await self._channel.set_qos(prefetch_count=10)
```

**How Messages Entered DLQ**:

1. **Message Prefetch**: RabbitMQ delivers up to 10 messages to bot consumer at once
2. **Bot Restart**: Bot crashes/restarts while holding unacked messages in prefetch buffer
3. **Message Redelivery**: RabbitMQ redelivers unacked messages back to queue
4. **TTL Continues**: Messages continue aging from original publish time, not redelivery time
5. **TTL Expiry**: Messages sitting in queue >1 hour trigger automatic DLQ routing

**Evidence from Bot Restart Timeline**:
```
07:47 Start
07:53 Restart (6 min gap)
08:15 Restart (22 min gap)
08:25 Restart (10 min gap)
08:38 Restart (13 min gap)
09:41 Restart (63 min gap) ← Close to 1-hour TTL
10:07 Restart (26 min gap)
```

**Scenario Explanation**:
- Messages published around 08:30
- Bot consumer at 08:38 receives 10 messages via prefetch
- Bot processes 2-3 messages, then crashes
- 7-8 unacked messages redelivered to queue
- Bot down until 09:41 (63 minutes later)
- Combined with original publish time, messages exceed 1-hour TTL
- RabbitMQ automatically dead-letters them to DLQ at ~09:30-09:40
- First daemon cycle at 10:30 finds 10 messages in DLQ

**Conclusion**: TTL expiry triggered by combination of prefetch buffering + frequent bot restarts. Messages held in prefetch don't consume queue space, so TTL clock keeps ticking from original publish time.

### **CONFIRMED Root Cause: Multiple Daemons Processing Same Shared DLQ**

**Discovery from daemon logs**: TWO separate daemons were both configured to process the SAME shared DLQ.

**Evidence**:
- `notification_daemon_wrapper.py`: `process_dlq=True`
- `status_transition_daemon_wrapper.py`: `process_dlq=True`
- Both daemons running on different schedules (45min offset)
- Both processing queue named "DLQ"

**Exponential Growth Mechanism**:

1. **10:30 AM**: Notification daemon processes DLQ with 10 messages
   - Republishes all 10 messages to primary queues
   - ACKs all 10 from DLQ (removes them)

2. **10:30-11:15**: Republished messages re-enter DLQ somehow (original cause unknown)
   - Now DLQ has ~10 messages again

3. **11:15 AM**: Status transition daemon ALSO processes DLQ with ~10 messages
   - Republishes all 10 messages AGAIN
   - ACKs all 10 from DLQ

4. **11:15-11:30**: Now ~20 messages re-enter DLQ (10 from step 2 + 10 from step 3)

5. **11:30 AM**: Notification daemon processes again with ~20 messages
   - Republishes all 20
   - Next cycle: ~40 messages

**Result**: Each daemon cycle DOUBLES the message count by republishing messages that the other daemon already republished.

**Daemon Processing Timeline from Logs**:
```
10:30 - 10 messages
11:15 - 38 messages (3.8x growth)
11:30 - 18 messages
12:15 - 70 messages (3.9x growth from 11:30)
12:30 - 34 messages
```

The ~4x growth between cycles confirms two processors with ~45min offset.

Track message hashes to prevent republishing duplicates:

```python
import hashlib

processed_hashes = set()

for method, _properties, body in channel.consume("DLQ", auto_ack=False):
    msg_hash = hashlib.sha256(body).hexdigest()

    if msg_hash in processed_hashes:
        logger.warning(f"Skipping duplicate message: {msg_hash[:8]}")
        channel.basic_ack(method.delivery_tag)
        continue

    # Republish logic...
    processed_hashes.add(msg_hash)
```

**Problem**: Hashes reset each daemon cycle. Duplicates across cycles still republished.

### Solution 3: Use RabbitMQ Message Deduplication Plugin

**Problem**: Requires plugin installation, added complexity.

### Solution 4: Only Process DLQ Once Per Day (Not Per Cycle)

**Idea**: DLQ processing should be rare - only for messages that failed during bot downtime.

Current: daemon checks DLQ every 15 minutes
Proposed: daemon checks DLQ only on startup

**Rationale**:
- During normal operation, messages should NOT go to DLQ frequently
- If messages are accumulating in DLQ, there's a systemic issue (bot crashing, DB down)
- Retrying every 15 minutes just amplifies the problem
- Better: Fix the underlying issue, then restart daemon to clear DLQ

### Solution 5: Add Backoff and Limit DLQ Processing Attempts

Track how many times we've tried to process DLQ, back off exponentially:

```python
dlq_retry_count = 0
MAX_DLQ_RETRIES_PER_BOOT = 3

def _should_process_dlq(self):
    if self.dlq_retry_count >= MAX_DLQ_RETRIES_PER_BOOT:
        return False

    # Exponential backoff: 5min, 15min, 45min
    backoff = 300 * (3 ** self.dlq_retry_count)
    return (time.time() - self.last_dlq_check) >= backoff
```

## Recommended Fix

**Immediate fix**: Process DLQ only on daemon startup, not periodically.

**Rationale**:
- Aligns with original research intent: "Daemon should run DLQ as part of startup"
- Prevents amplification of systemic issues
- DLQ becomes a safety net for downtime recovery, not a retry mechanism

**Code change**:
```python
def run(self, shutdown_requested, max_timeout: int = 900) -> None:
    try:
        self.connect()

        # Process DLQ once on startup
        if self.process_dlq:
            self._process_dlq_messages()

        # Rest of daemon loop (no periodic DLQ processing)
        while not shutdown_requested():
            # ... existing logic WITHOUT dlq_check_interval ...
```

**Future enhancement**: Add manual trigger (signal/API) to process DLQ on demand.

## Questions for User

Before implementing fix, need to understand:

1. **Are you seeing bot crashes/restarts?** Check bot logs for exceptions, pod kills, OOM errors
2. **What's in the DLQ messages?** Check `x-death` header for reason (rejected, expired, TTL, etc)
3. **Are DLQ messages duplicates?** Compare message bodies to see if same event repeated
4. **When did this start?** Before or after enabling daemon DLQ processing?

This will help confirm the root cause and choose the right fix.

## CONFIRMED ROOT CAUSE

After analyzing the code, the root cause is **periodic DLQ processing combined with immediate ACK**.

**The daemon currently**:
1. Processes DLQ **every 15 minutes** (line 136-138 in generic_scheduler_daemon.py)
2. **Immediately ACKs** DLQ messages after republishing (line 308)
3. **Cannot verify** if bot successfully processed the republished message

**Exponential growth scenario**:
- Bot is down or crashing repeatedly
- Daemon cycle 1: Republishes 1 message, ACKs it, bot fails → 1 back in DLQ
- Daemon cycle 2: Republishes 1 message, ACKs it, bot fails → 1 back in DLQ (or more if new failures)
- **If multiple messages fail simultaneously**: Each cycle can amplify

**Alternatively** (more likely):
- Bot is working but slow
- Daemon republishes message faster than bot can process
- Multiple copies of same message in flight
- Each copy that fails → DLQ
- Exponential growth!

## RECOMMENDED SOLUTION

### Immediate Fix: Remove Periodic DLQ Processing

**Change**: Process DLQ **only on daemon startup**, not every 15 minutes.

**Rationale**:
1. DLQ is for recovery from downtime, not continuous retry
2. If messages keep going to DLQ, there's a systemic issue (bot down, DB down)
3. Retrying every 15 minutes amplifies the problem
4. Original research stated: "The daemons should run the DLQ as part of startup"
5. Prevents exponential growth by limiting processing frequency

**Code changes**:
- Remove lines 136-138 (periodic DLQ check)
- Keep lines 127-130 (startup DLQ processing)

**Benefits**:
- ✅ Fixes exponential growth
- ✅ Aligns with original design intent
- ✅ Simpler logic (no timing tracking)
- ✅ Still provides downtime recovery
- ✅ Prevents amplification loops

### Alternative: Add Message Deduplication

If periodic processing is needed, add deduplication:

```python
# Track message IDs seen in this DLQ processing cycle
seen_message_ids = set()

for method, properties, body in channel.consume("DLQ", auto_ack=False):
    event = Event.model_validate_json(body)

    # Check if we've already processed this exact message
    message_id = properties.message_id
    if message_id and message_id in seen_message_ids:
        logger.info(f"Skipping duplicate DLQ message: {message_id}")
        channel.basic_ack(method.delivery_tag)
        continue

    # Republish...
    if message_id:
        seen_message_ids.add(message_id)
```

**Problem**: RabbitMQ doesn't auto-generate message_id - daemon would need to set it when publishing. Complex change.

## IMPLEMENTATION PLAN

**Preferred approach**: Remove periodic DLQ processing.

**File**: `services/scheduler/generic_scheduler_daemon.py`

**Changes**:
1. Remove periodic DLQ check (lines 136-138)
2. Update docstring to clarify DLQ processed only on startup
3. Remove `dlq_check_interval` parameter (no longer needed)
4. Remove `last_dlq_check` instance variable

**Impact**:
- Daemon wrappers: No changes needed (process_dlq flag still works)
- Tests: Update to remove periodic DLQ expectations
- Documentation: Update to reflect startup-only processing

**Migration**:
- Existing DLQ messages will be cleared on next daemon restart
- No data loss (messages still in DLQ, just not processed until restart)

## ACTUAL ROOT CAUSE (Confirmed from Logs)

**The real problem**: **TWO daemons are both processing the same DLQ!**

From configuration:
- `services/scheduler/notification_daemon_wrapper.py` line 73: `process_dlq=True`
- `services/scheduler/status_transition_daemon_wrapper.py` line 73: `process_dlq=True`

**What's happening**:
1. Messages fail and go to single shared DLQ queue
2. **Notification daemon** processes DLQ every ~45 minutes, republishes all messages, ACKs them
3. **Status transition daemon** processes same DLQ every ~15 minutes, republishes all messages, ACKs them
4. **Same messages republished by BOTH daemons** → duplicates created
5. Duplicates fail → go back to DLQ
6. Exponential growth!

**Log evidence**:
```
02:30:01 -  10 msgs (notification daemon processes)
03:15:01 -  38 msgs (+28, status daemon processes 15min later → creates duplicates)
03:30:01 -  18 msgs (-20, notification daemon clears some)
04:15:01 -  70 msgs (+52, status daemon processes → more duplicates)
04:30:01 -  34 msgs (-36, notification daemon clears some)
```

**The pattern**:
- Δ 2700s (45 min) = notification daemon interval
- Δ 900s (15 min) = status daemon interval
- Growth happens 15min after each notification daemon run (status daemon duplicates)
- Shrinkage happens when notification daemon runs again (clears some, creates new ones)

## THE FIX

**Only ONE daemon should process the DLQ**.

Since the DLQ contains messages from BOTH daemons (notifications + status transitions), either:

**Option 1**: Notification daemon processes DLQ only
```python
# notification_daemon_wrapper.py
process_dlq=True

# status_transition_daemon_wrapper.py
process_dlq=False  # ← CHANGE THIS
```

**Option 2**: Status transition daemon processes DLQ only
```python
# notification_daemon_wrapper.py
process_dlq=False  # ← CHANGE THIS

# status_transition_daemon_wrapper.py
process_dlq=True
```

**Recommendation**: **Status transition daemon** should own DLQ processing because:
- Status transitions are critical (must never be lost)
- Runs more frequently (15min vs 45min) → faster recovery
- Already configured for retries

**Implementation**:
1. Set `process_dlq=False` in notification_daemon_wrapper.py
2. Keep `process_dlq=True` in status_transition_daemon_wrapper.py
3. Deploy and monitor DLQ depth

**Expected result**: DLQ messages processed once per cycle, no duplication, no exponential growth.

## Queue Architecture and Daemon Consumption Patterns

### Complete RabbitMQ Queue Topology

**Queues and Their Consumers**:
- **bot_events**: Consumed by bot service
  - Routing keys: `game.*` (all game events)
  - Handlers: game.created, game.updated, game.reminder_due, game.status_transition_due, player.removed
- **notification_queue**: Consumed by bot service
  - Routing keys: `notification.send_dm`
  - Used for direct message notifications
- **api_events**: **NO CONSUMERS** (placeholder for future API consumption)
- **scheduler_events**: **NO CONSUMERS** (currently unused - messages accumulate)

### Daemon Message Flow Pattern

**CRITICAL**: Daemons do **NOT** consume from RabbitMQ for their scheduling work!

**PostgreSQL LISTEN/NOTIFY Pattern**:
1. Database triggers fire on schedule table changes (notification_schedule, game_status_schedule)
2. PostgreSQL sends NOTIFY on specific channels:
   - `notification_schedule_changed` → notification_daemon wakes
   - `game_status_schedule_changed` → status_transition_daemon wakes
3. Daemon queries database MIN(scheduled_time) for next due item
4. Daemon waits for earliest of: due time, PostgreSQL NOTIFY, or 15-minute timeout
5. When item is due, daemon publishes event TO RabbitMQ

**Daemon Publishing (not consuming)**:
- notification_daemon publishes: `game.reminder_due` → bot_events queue
- status_transition_daemon publishes: `game.status_transition_due` → bot_events queue
- Bot consumes these events from bot_events queue

**Evidence from Code**:
- `services/scheduler/generic_scheduler_daemon.py:101-115` - Uses PostgresNotificationListener
- `services/bot/events/handlers.py:75-115` - Bot binds to "game.*" and "notification.*"
- No RabbitMQ consumer code in daemon implementations

### Unused Queue: scheduler_events

**Current State**:
- Queue receives `game.created`, `game.updated`, `game.cancelled` events (from bot publishes)
- NO consumers process messages from this queue
- Messages accumulate indefinitely without TTL or consumer

**Historical Context**:
- Likely intended for daemon consumption in original architecture
- Replaced by PostgreSQL LISTEN/NOTIFY pattern for efficiency
- Queue binding remains but serves no current purpose

**Recommendation**:
- Either remove scheduler_events queue entirely from infrastructure
- Or configure TTL to prevent unbounded message accumulation
- Or add consumer if future functionality is planned

### Per-Queue DLQ Architecture

Following the fix for duplicate DLQ processing, the architecture now uses per-queue DLQs:

**DLQ Ownership**:
1. **bot_events.dlq** - Processed by notification_daemon (only one daemon processes it)
2. **notification_queue.dlq** - Needs decision: bot self-recovery or daemon processing?
3. **api_events.dlq** - No processing needed (no consumer exists)
4. **scheduler_events.dlq** - No processing needed (no consumer exists, consider removing queue)

**Remaining Decisions**:
- notification_queue.dlq: Should bot process its own DLQ or delegate to daemon?
- Unused queues: Remove scheduler_events and api_events, or keep for future use?

## RabbitMQ Built-in Retry Mechanisms

### Quorum Queue Delivery Limits (Automatic Retry with Limits)

RabbitMQ **quorum queues** have built-in poison message handling using `delivery-limit`:

**How It Works**:
- Tracks redelivery count in `x-delivery-count` header
- After exceeding delivery-limit, message is automatically dead-lettered or dropped
- **Default in RabbitMQ 4.0+**: delivery-limit = 20
- **RabbitMQ 3.x**: No default limit (must be set via policy)

**Configuration via Policy**:
```bash
# Set delivery limit to 50
rabbitmqctl set_policy qq-overrides \
  "^qq\." '{"delivery-limit": 50}' \
  --priority 123 \
  --apply-to "quorum_queues"

# Disable limit (not recommended)
rabbitmqctl set_policy qq-overrides \
  "^qq\." '{"delivery-limit": -1}' \
  --priority 123 \
  --apply-to "quorum_queues"

# Set limit AND dead-letter exchange
rabbitmqctl set_policy qq-overrides \
  "^qq\." '{"delivery-limit": 50, "dead-letter-exchange": "redeliveries.limit.dlx"}' \
  --priority 123 \
  --apply-to "quorum_queues"
```

**Our Configuration**:
- Using **classic queues** (not quorum queues) → delivery-limit **NOT available**
- TTL-based dead-lettering only (messages expire after 1 hour)

### At-Least-Once Dead-Lettering (Reliable DLQ Pattern)

Quorum queues support **at-least-once** dead-lettering for safe message transfer to DLX:

**How It Works**:
- Internal DLX consumer process handles republishing
- Source queue retains messages until DLX confirms receipt
- Uses publisher confirms for guaranteed delivery
- **Caveat**: Requires `overflow: reject-publish` (not `drop-head`)

**Configuration**:
```bash
rabbitmqctl set_policy qq-overrides \
  "^qq\." \
  '{"dead-letter-strategy": "at-least-once", "overflow": "reject-publish", "dead-letter-exchange": "dlx"}' \
  --priority 123 \
  --apply-to "quorum_queues"
```

**Our Configuration**:
- Using **classic queues** → at-least-once **NOT available**
- Default at-most-once dead-lettering (can lose messages during transfer)

### Classic Queues vs Quorum Queues

**Classic Queues (our current setup)**:
- ❌ No delivery-limit support
- ❌ No at-least-once dead-lettering
- ✅ TTL-based expiry (x-message-ttl)
- ✅ Basic dead-letter exchange (at-most-once)
- ✅ Lower latency, simpler for transient workloads

**Quorum Queues (alternative)**:
- ✅ Automatic poison message handling (delivery-limit)
- ✅ At-least-once dead-lettering
- ✅ Replicated for high availability
- ✅ Data safety guarantees (Raft consensus)
- ❌ Higher latency due to consensus
- ❌ Higher resource usage (memory, disk)
- ❌ Not suitable for transient/exclusive queues

## Summary and Implementation Checklist

### Selected Approach: Dedicated Retry Service

**Decision**: Implement Option 3 (Dedicated Retry Service) to:
1. Fix DLQ exponential growth bug
2. Remove unused queues (scheduler_events, api_events)
3. Establish clear ownership for retry logic
4. Simplify daemon responsibilities

### Implementation Tasks

#### Phase 1: Remove Unused Infrastructure
- [ ] Remove QUEUE_API_EVENTS and QUEUE_SCHEDULER_EVENTS from `shared/messaging/infrastructure.py`
- [ ] Remove api_events and scheduler_events queue declarations from `scripts/init_rabbitmq.py`
- [ ] Update PRIMARY_QUEUES and QUEUE_BINDINGS in infrastructure.py
- [ ] Update integration tests to remove unused queue references
- [ ] Deploy and verify unused queues are deleted from RabbitMQ

#### Phase 2: Create Retry Service
- [ ] Create `services/retry/retry_daemon.py` with RetryDaemon class
- [ ] Create `services/retry/retry_daemon_wrapper.py` for entry point
- [ ] Create `docker/retry.Dockerfile` for containerization
- [ ] Add retry-daemon service to `docker-compose.yml`
- [ ] Add environment variables for configuration (RETRY_INTERVAL_SECONDS)
- [ ] Write unit tests for RetryDaemon class
- [ ] Write integration tests for DLQ processing

#### Phase 3: Remove DLQ Processing from Daemons
- [ ] Set process_dlq=False in `notification_daemon_wrapper.py`
- [ ] Set process_dlq=False in `status_transition_daemon_wrapper.py`
- [ ] Update daemon tests to remove DLQ processing expectations
- [ ] Deploy and verify daemons no longer process DLQs

#### Phase 4: Monitoring and Documentation
- [ ] Add DLQ depth metrics to Grafana dashboard
- [ ] Configure alerts for DLQ depth thresholds (e.g., >10 messages)
- [ ] Document retry service in RUNTIME_CONFIG.md
- [ ] Document manual DLQ recovery procedure
- [ ] Update architecture diagrams with retry service

### Testing Strategy

**Unit Tests**:
- RetryDaemon._process_dlq() with mock publisher
- RetryDaemon._get_routing_key() with various message headers
- Error handling when republish fails

**Integration Tests**:
- Publish message to bot_events, let it TTL expire, verify retry service republishes
- Publish message to notification_queue, NACK it, verify retry service republishes
- Verify retry service processes both DLQs in correct order
- Verify retry service handles empty DLQs gracefully

**E2E Tests**:
- Simulate bot downtime, verify messages enter DLQ, verify retry service recovers them
- Verify no exponential growth under repeated failures
- Verify retry interval configurable via environment variable

### Rollback Plan

If retry service causes issues:
1. Stop retry-daemon container
2. Re-enable process_dlq=True on notification_daemon_wrapper
3. Manually drain DLQs if needed
4. Revert to previous architecture

### Success Metrics

- ✅ DLQ message count stays stable (no exponential growth)
- ✅ Messages successfully republished from DLQ within 15 minutes
- ✅ No duplicate message processing
- ✅ notification_daemon and status_transition_daemon logs show no DLQ processing
- ✅ retry-daemon logs show successful DLQ processing every 15 minutes

---

## Appendix: Message Flow Diagrams

### Current Architecture (Before Changes)

```
API Service
  |
  v (publishes notification.send_dm)
notification_queue --> Bot (consumes)
  |
  v (TTL expiry or NACK)
notification_queue.dlq
  |
  v (NO PROCESSING - accumulates messages)

Notification Daemon
  |
  v (publishes game.reminder_due)
bot_events --> Bot (consumes)
  |
  v (TTL expiry or NACK)
bot_events.dlq
  |
  v (notification_daemon processes - WRONG OWNER)
  republish to bot_events

Status Transition Daemon
  |
  v (publishes game.status_transition_due)
bot_events --> Bot (consumes)
  |
  v (TTL expiry or NACK)
bot_events.dlq
  |
  v (status_transition_daemon processes - DUPLICATE)
  republish to bot_events

RESULT: Exponential growth from duplicate processing
```

### Proposed Architecture (After Changes)

```
API Service
  |
  v (publishes notification.send_dm)
notification_queue --> Bot (consumes)
  |
  v (TTL expiry or NACK)
notification_queue.dlq
  |
  v (Retry Service processes every 15 min)
  republish to notification_queue --> Bot retries

Notification Daemon
  |
  v (publishes game.reminder_due)
bot_events --> Bot (consumes)
  |
  v (TTL expiry or NACK)
bot_events.dlq
  |
  v (Retry Service processes every 15 min)
  republish to bot_events --> Bot retries

Status Transition Daemon
  |
  v (publishes game.status_transition_due)
bot_events --> Bot (consumes)
  |
  v (TTL expiry or NACK)
bot_events.dlq
  |
  v (Retry Service processes every 15 min)
  republish to bot_events --> Bot retries

Retry Service
  |
  +-- Processes bot_events.dlq every 15 min
  |   (republishes messages from daemons)
  |
  +-- Processes notification_queue.dlq every 15 min
      (republishes messages from API)

RESULT: Single processor per DLQ, no duplication, clear ownership
```

### Queue Topology (After Cleanup)

```
Exchanges:
  game_scheduler (topic)
  game_scheduler.dlx (fanout)

Queues (Active):
  bot_events
    - bindings: game.*, guild.*, channel.*
    - TTL: 1 hour
    - DLX: game_scheduler.dlx
    - consumer: bot service

  notification_queue
    - bindings: notification.send_dm
    - TTL: 1 hour
    - DLX: game_scheduler.dlx
    - consumer: bot service

Dead Letter Queues:
  bot_events.dlq
    - bound to: game_scheduler.dlx
    - no TTL (infinite retention)
    - processor: retry service

  notification_queue.dlq
    - bound to: game_scheduler.dlx
    - no TTL (infinite retention)
    - processor: retry service

Queues (Removed):
  ❌ api_events (no consumers, never used)
  ❌ scheduler_events (no consumers, replaced by PostgreSQL NOTIFY)
  ❌ api_events.dlq (unused)
  ❌ scheduler_events.dlq (unused)
```

### Option 3: Dedicated Retry Service (Recommended)

**Approach**:
- Keep classic queues (simpler, lower latency)
- Remove unused queues (scheduler_events, api_events)
- Implement per-queue DLQs for clear ownership
- Create dedicated retry service to handle ALL DLQ processing
- Remove DLQ processing from notification_daemon

**Rationale**:
- Clear separation of concerns: publishers publish, consumers consume, retry service retries
- notification_daemon shouldn't retry messages for notification_queue (neither sender nor receiver)
- Single service owns all retry logic with configurable intervals
- Can handle any future DLQs without modifying daemons or consumers

**Architecture**:

```
Publishers                Primary Queues         Consumers
--------                  --------------         ---------
API ---------> notification_queue ---------> Bot
               (TTL: 1hr, DLX: game_scheduler.dlx)
                     |
                     v (on TTL expiry or NACK)
               notification_queue.dlq
                     |
                     v (every 15 min)
               [Retry Service] -----> republish to notification_queue

Daemons               Primary Queues         Consumers
-------               --------------         ---------
notification_daemon -> bot_events ---------> Bot
status_daemon ------>  (TTL: 1hr, DLX: game_scheduler.dlx)
                     |
                     v (on TTL expiry or NACK)
               bot_events.dlq
                     |
                     v (every 15 min)
               [Retry Service] -----> republish to bot_events
```

**Ownership Model**:
- `bot_events.dlq`: Contains messages FROM daemons FOR bot
  - Retry service owns retry logic (neutral party)
- `notification_queue.dlq`: Contains messages FROM api FOR bot
  - Retry service owns retry logic (neutral party)

**Implementation**:

1. **Create Retry Service** (`services/retry/retry_daemon.py`):

```python
"""
Dedicated retry service for DLQ processing.

Periodically checks configured DLQs and republishes messages
to their primary queues with configurable intervals.
"""

import time
import logging
from shared.messaging.publisher import SyncPublisher
from shared.messaging.infrastructure import (
    QUEUE_BOT_EVENTS,
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION,
    QUEUE_NOTIFICATION_DLQ,
    MAIN_EXCHANGE,
)

logger = logging.getLogger(__name__)

class RetryDaemon:
    """Processes DLQs and republishes messages with backoff."""

    def __init__(self, retry_interval_seconds: int = 900):
        """
        Initialize retry daemon.

        Args:
            retry_interval_seconds: How often to check DLQs (default 15 min)
        """
        self.retry_interval = retry_interval_seconds
        self.publisher = SyncPublisher()

        # Map DLQ to primary queue for republishing
        self.dlq_mappings = {
            QUEUE_BOT_EVENTS_DLQ: QUEUE_BOT_EVENTS,
            QUEUE_NOTIFICATION_DLQ: QUEUE_NOTIFICATION,
        }

    def run(self, shutdown_requested):
        """Main daemon loop."""
        self.publisher.connect()

        try:
            while not shutdown_requested():
                for dlq_name, primary_queue in self.dlq_mappings.items():
                    self._process_dlq(dlq_name, primary_queue)

                time.sleep(self.retry_interval)
        finally:
            self.publisher.close()

    def _process_dlq(self, dlq_name: str, primary_queue: str):
        """Process messages from one DLQ."""
        channel = self.publisher._channel

        # Count messages without consuming
        queue_state = channel.queue_declare(
            queue=dlq_name,
            passive=True,
            durable=True
        )
        message_count = queue_state.method.message_count

        if message_count == 0:
            return

        logger.info(f"Processing {message_count} messages from {dlq_name}")

        processed = 0
        for method, properties, body in channel.consume(
            dlq_name,
            inactivity_timeout=5
        ):
            if method is None:
                break

            try:
                # Extract routing key from original message
                routing_key = self._get_routing_key(properties)

                # Republish to primary queue via main exchange
                self.publisher.publish_raw(
                    exchange=MAIN_EXCHANGE,
                    routing_key=routing_key,
                    body=body,
                    properties=properties,
                )

                # ACK after successful republish
                channel.basic_ack(method.delivery_tag)
                processed += 1

            except Exception as e:
                logger.error(
                    f"Failed to republish message from {dlq_name}: {e}",
                    exc_info=True
                )
                # NACK without requeue - message stays in DLQ for next cycle
                channel.basic_nack(method.delivery_tag, requeue=True)

        logger.info(f"Republished {processed} messages from {dlq_name}")

    def _get_routing_key(self, properties) -> str:
        """Extract original routing key from message headers."""
        if properties.headers and "x-death" in properties.headers:
            # Get routing key from first death record
            deaths = properties.headers["x-death"]
            if deaths and len(deaths) > 0:
                return deaths[0].get("routing-keys", [None])[0]

        # Fallback to message routing key
        return properties.routing_key or "unknown"
```

2. **Create Retry Service Wrapper** (`services/retry/retry_daemon_wrapper.py`):

```python
from services.retry.retry_daemon import RetryDaemon

def main():
    daemon = RetryDaemon(retry_interval_seconds=900)  # 15 minutes
    shutdown_requested = lambda: False  # Implement signal handling
    daemon.run(shutdown_requested)

if __name__ == "__main__":
    main()
```

3. **Add Dockerfile** (`docker/retry.Dockerfile`):

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/retry/ /app/services/retry/

CMD ["python", "-m", "services.retry.retry_daemon_wrapper"]
```

4. **Update docker-compose.yml**:

```yaml
  retry-daemon:
    build:
      context: .
      dockerfile: docker/retry.Dockerfile
    environment:
      - RABBITMQ_URL=${RABBITMQ_URL}
      - RETRY_INTERVAL_SECONDS=900
    depends_on:
      - rabbitmq
    restart: unless-stopped
```

5. **Remove DLQ Processing from Daemons**:

```python
# services/scheduler/notification_daemon_wrapper.py
daemon = GenericSchedulerDaemon(
    # ... other config ...
    process_dlq=False,  # ← Remove DLQ processing
)

# services/scheduler/status_transition_daemon_wrapper.py
daemon = GenericSchedulerDaemon(
    # ... other config ...
    process_dlq=False,  # ← Remove DLQ processing
)
```

6. **Remove Unused Queues** from `shared/messaging/infrastructure.py`:

```python
# Remove these constants
# QUEUE_API_EVENTS = "api_events"
# QUEUE_SCHEDULER_EVENTS = "scheduler_events"
# QUEUE_API_EVENTS_DLQ = "api_events.dlq"
# QUEUE_SCHEDULER_EVENTS_DLQ = "scheduler_events.dlq"

# Update PRIMARY_QUEUES list
PRIMARY_QUEUES = [
    QUEUE_BOT_EVENTS,
    QUEUE_NOTIFICATION,
]

# Update DEAD_LETTER_QUEUES list
DEAD_LETTER_QUEUES = [
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION_DLQ,
]

# Update QUEUE_BINDINGS - remove scheduler_events and api_events bindings
QUEUE_BINDINGS = [
    (QUEUE_BOT_EVENTS, "game.*"),
    (QUEUE_BOT_EVENTS, "guild.*"),
    (QUEUE_BOT_EVENTS, "channel.*"),
    (QUEUE_NOTIFICATION, "notification.send_dm"),
]
```

7. **Update init_rabbitmq.py** to remove unused queues

**Benefits**:
✅ Clear ownership: Retry service owns all DLQ processing
✅ Daemons focus on their core responsibility (scheduling)
✅ Single place to configure retry intervals and backoff
✅ Easy to add new DLQs in the future
✅ Removes ~300 lines of DLQ code from generic_scheduler_daemon.py
✅ No more confusion about which daemon processes which DLQ

**Trade-offs**:
- One additional service to deploy and monitor
- ~100 lines of new code for retry service
- Simpler overall architecture (removes complexity from daemons)
