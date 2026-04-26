<!-- markdownlint-disable-file -->

# Changes: coalesce-member-update-projection

## Summary

Replace direct `repopulate_all` calls in the three member-event handlers with an
`asyncio.Event`-based coalescing worker that caps rebuilds at one per 60 seconds.
Move the `started` counter emission out of `repopulate_all` and into each caller.
Remove the `reason` label from the duration and members-written histograms.

## Added

- `tests/unit/bot/test_bot_member_event_worker.py` — new xfail test file with three test classes (`TestMemberEventWorkerCoalescing`, `TestMemberEventWorkerCooldown`, `TestOnReadyUnaffected`) covering worker coalescing, cooldown sleep, and on_ready counter+repopulate behavior

## Modified

- `services/bot/bot.py` — added `self._member_event: asyncio.Event = asyncio.Event()` to `__init__`; added `_member_event_worker` async method with coalescing loop and `CancelledError` guard; started worker task in `setup_hook` with `hasattr` guard; replaced `on_member_add`, `on_member_update`, `on_member_remove` bodies to emit counter with reason label + `self._member_event.set()`; added `guild_projection.repopulation_started_counter.add(1, {"reason": "on_ready"})` before `repopulate_all` in `on_ready`; removed `reason=` from all four `repopulate_all` call sites
- `services/bot/guild_projection.py` — removed `reason` param from `repopulate_all`, removed `repopulation_started_counter.add` call, removed `{"reason": reason}` labels from both histograms, simplified logger.info message
- `tests/unit/bot/test_guild_projection.py` — added `patch` to imports; removed `reason=` from all 10 `repopulate_all` call sites; updated `test_repopulate_all_otel_metrics` to assert started counter is not called inside `repopulate_all`; added then removed xfail markers from `test_repopulate_all_has_no_reason_parameter` and `test_repopulate_all_does_not_emit_started_counter`
- `tests/unit/bot/test_bot_ready.py` — updated `test_on_ready_calls_repopulate_all` assertion to expect no `reason=` kwarg
- `tests/unit/bot/test_bot_member_event_worker.py` — removed all `@pytest.mark.xfail(strict=True)` markers; all 4 tests now pass

## Removed

<!-- Files deleted during this task -->
