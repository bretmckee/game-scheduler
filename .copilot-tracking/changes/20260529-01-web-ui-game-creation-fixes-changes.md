<!-- markdownlint-disable-file -->

# Changes: Web UI Game Creation Fixes

## Overview

Implementation record for fixing four UX issues in game creation: GIF animation,
@mention resolution, #channel resolution, and custom emoji resolution.

---

## Phase 1: GIF Animation Fix

### Added

- `tests/unit/services/api/routes/test_public.py` — regression tests for extension-suffixed URLs on GET and HEAD, plus `_public_app` fixture using `TestClient` with dependency override

### Modified

- `services/api/routes/public.py` — changed `image_id: UUID` to `image_id_with_ext: str` on both GET and HEAD routes; added `UUID(image_id_with_ext.split(".")[0])` parse; added `ValueError` → 404 handling for invalid UUIDs; updated existing unit tests to pass `str` instead of `UUID` objects
- `tests/unit/services/api/routes/test_public.py` — updated existing direct-call tests to pass `str(uuid)` since parameter is now `str`
- `services/bot/formatters/game_message.py` — added `_MIME_TO_EXT` dict; added `thumbnail_mime_type` and `banner_image_mime_type` optional parameters to `format_game_announcement()`; updated URL construction to append extension when MIME type is known
- `tests/unit/services/bot/formatters/test_game_message.py` — added `import pytest`; added `TestFormatGameAnnouncementMimeTypes` class with tests for gif/png extension appending and None passthrough
- `services/bot/events/handlers.py` — added `thumbnail_mime_type` and `banner_image_mime_type` keyword arguments to the `format_game_announcement()` call in `_create_game_announcement()`
- `tests/unit/services/bot/events/test_handlers_game_created.py` — added `TestCreateGameAnnouncementMimeTypes` class with tests verifying MIME types are forwarded to `format_game_announcement`

---

## Phase 2: #channel Integer Passthrough Fix

### Added

### Modified

### Removed

---

## Phase 3: @mention Resolution in Free-Text Fields

### Added

### Modified

### Removed

---

## Phase 4: Custom Emoji Resolution

### Added

### Modified

### Removed

---

## Phase 5: Documentation Update

### Added

### Modified

### Removed
