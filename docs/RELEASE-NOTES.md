# Release Notes

## v1.2.12 — 2026-09-14

<!-- release-notes-skill: generated-through=fd6080b2fdefaf5478a1a2457dcf8f4c76c20a7e -->

**New**

- Game cards now show the day of the week and a quick "in 3 hours" / "in 2 days" style hint for upcoming games, so it's easier to tell at a glance how soon a game is.
- Game cards show a colored border for your seating status: a solid teal border if you're seated, confirmed, or hosting, and a dashed amber border if you're on the waitlist.
- Hosts can now click the Participants header on a game to open a new **Seat Positions** page — a clean table of confirmed and waitlisted players in order.
- Discord role pings (e.g. @AL-games) are no longer sent for host-selected games, since those games aren't open for self-signup anyway — less notification noise.

**Fixed**

- Fixed a bug where editing an existing player's name on a game and saving would silently do nothing — your edit now actually saves.
- Fixed a crash when a host edited a game and mentioned someone who was already seated elsewhere in that game — they're now correctly moved to the new seat instead of the save failing.
- Fixed saving a game edit sometimes failing because of an unrelated, unnecessary re-check of the Location field — this could happen even when you hadn't touched Location at all (often showed up as "I removed a participant, clicked save, and nothing happened," with the real error hidden off-screen).
- Error messages on the create/edit game form now appear right next to the Save/Cancel buttons instead of at the top of the page, so you'll actually see them.
