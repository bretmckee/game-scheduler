---
name: release-notes
description: Draft user-facing release notes from the commits since the last entry, and insert the approved entry at the top of docs/RELEASE-NOTES.md. Invoke when the user wants release notes, a changelog entry, or a message to let users know about a new staging/production release.
---

# Release Notes

Turns recent git history into a short, user-facing summary — what's new and what's fixed,
no technical detail — and records it in `docs/RELEASE-NOTES.md`. This is for the players,
hosts, and admins using Game Scheduler, not for contributors: skip anything they wouldn't
notice or care about.

## Step 1: Find the starting point

`docs/RELEASE-NOTES.md` starts with a header, then one entry per release, newest first. Each
entry heading carries an HTML comment recording the exact commit it was generated through:

```
## v1.3.0 — 2026-09-14
<!-- release-notes-skill: generated-through=b2556757 -->
```

- If the file exists, read the topmost entry's `generated-through` ref — that's the start of
  your range (`git log <ref>..HEAD`).
- If the file doesn't exist yet, or the topmost entry has no such comment (hand-written before
  this skill existed), ask the user what to diff from — the latest git tag is a reasonable
  suggestion (`git tag --sort=-creatordate | head -5`), but confirm rather than assuming.

Note the current `HEAD` SHA (`git rev-parse HEAD`) now — that's what this entry's own
`generated-through` comment will record, so the next run picks up exactly where this one left
off, independent of whether anyone tags the release.

## Step 2: Ask for the version number

Always ask — don't infer it from a tag, since staging releases often go out ahead of tagging.
Use `AskUserQuestion` if there's an obvious next version to suggest (e.g. bump the last entry's
version), otherwise just ask in text.

## Step 3: Read the commits and filter hard

```
git log <start>..HEAD --format='=====%n%H%n%s%n%b' | cat
```

Read every commit's full body, not just the subject — the user-visible effect is usually in the
rationale, not the summary line. Then keep only what a player, host, or server admin would
notice using the product. As a rule of thumb:

**Exclude:**

- devcontainer, CI/CD, dependency, build-tooling, and pre-commit changes
- test-only changes (new/fixed tests, e2e flakiness fixes, test infra) unless the commit _also_
  fixed a real product bug
- internal refactors, performance/reliability fixes with no user-observable symptom (e.g. a
  background task pacing fix that only mattered under an internal error condition)
- docs-only or tracking-file changes about the work itself (research/plan/details files)

**Include:**

- anything a user would see, click, receive, or be blocked by: new pages, UI changes, new
  bot behavior, fixed bugs that broke a workflow, changed notification behavior

When in doubt, prefer leaving something out and flagging it to the user over guessing it's
user-facing.

Get the mechanism right before phrasing it for users — read the diff, not just the commit
message, when the message's causal claim (e.g. "triggered by a channel rename") is more specific
than what the code actually shows. Describe the failure at the level of what actually happens,
not the first plausible trigger that comes to mind.

## Step 4: Draft, grouped as **New** and **Fixed**

Plain language, no jargon, no file names, no internal component names. Each bullet: what changed
from the user's point of view, and if it was a bug, what it looked like when it was broken (helps
users recognize "oh, that was me").

Show the draft in the conversation before writing anything. Revise based on feedback — including
correcting the underlying mechanism if the user says the description is wrong, not just the
wording (re-check the code, per Step 3).

## Step 5: Insert at the top on approval

Once the user approves the draft, insert it as a new entry directly under the file's title
heading, above every existing entry (newest-first order) — never append at the bottom, never
edit or reflow older entries. New file: create it with a one-line title (`# Release Notes`)
followed by this first entry.

Entry format:

```
## v<version> — <YYYY-MM-DD>
<!-- release-notes-skill: generated-through=<HEAD SHA from Step 1> -->

**New**
- ...

**Fixed**
- ...
```

Omit a **New** or **Fixed** section entirely if this release has nothing for it — don't write
"None."

Write the file and stop. Don't commit — show the user the diff (or where the file is) and let
them review and commit it themselves, alongside whatever else is in the release.
