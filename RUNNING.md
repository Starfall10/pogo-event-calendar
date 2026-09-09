# Running it

Everything goes through `uv` from the repository root. There is nothing to
activate and no virtual environment to remember — `uv run` builds and uses one
on its own.

If `uv` is not installed: `brew install uv`. It fetches the Python version
`pyproject.toml` asks for, so no separate Python install is needed.

## Commands

| Command | What it does | Needs `.env`? |
|---|---|---|
| `uv run pytest` | The whole test suite. Offline, about 0.2 seconds | No |
| `uv run pytest -q tests/test_leekduck.py` | One file | No |
| `uv run pytest -q -k harvest` | One test, by name | No |
| `uv run pogocal build` | Rebuild `docs/pogo.ics` from the Leek Duck feed alone | No |
| `uv run pogocal run` | The full job — feed **and** Discord infographic links. This is what the hourly Action runs | Yes |
| `uv run pogocal poll` | Print posts in the channel newer than the cursor | Yes |

Nothing here costs money. The feed is a static file, the Discord REST API is
free, and no paid API is ever called — see the constraint at the top of
`CLAUDE.md`.

## Credentials

`uv run pytest` and `uv run pogocal build` work on a machine with no
credentials at all. That is deliberate: the suite must run on a train.

`run` and `poll` need `.env`:

```bash
cp .env.example .env   # then fill it in
```

`.env` is gitignored and must stay that way — this repository is public. If a
token is ever committed, reset it in the Discord Developer Portal rather than
trying to remove the commit; a pushed secret is a public secret.

Without `.env`, `run` still publishes — it logs a warning and leaves the
infographic links off. A calendar with correct times and no links is worth
having; one with neither is not.

## Looking at the output

```bash
head -40 docs/pogo.ics          # read the calendar as text
grep -c '^BEGIN:VEVENT' docs/pogo.ics    # how many events
grep '^DTSTART' docs/pogo.ics | head     # the times, as published
open docs/pogo.ics              # opens Calendar — it will offer to import.
                                # Don't; you are already subscribed to the
                                # published URL.
```

Preview the web page the way GitHub Pages serves it:

```bash
cd docs && python3 -m http.server 8000
```

Then open <http://localhost:8000>. Pages serves this folder the same way, so
if it looks right locally it will look right published.

## Two things worth knowing

**`run` rewrites `docs/pogo.ics`**, so `git status` will show it modified even
when nothing meaningful changed. That is normal. To look around without
touching anything, use `poll`.

**`poll` moves the cursor** in `state/cursor.json`. The cursor is local and
gitignored; nothing about the published calendar depends on it. Deleting the
file is safe — the next `poll` starts again from `CURSOR_SEED_MESSAGE_ID`.

## The scheduled job

```bash
gh run list --workflow="Update calendar" --limit 20   # every run
gh run view <id> --log                                # one run in full
gh workflow run "Update calendar"                     # trigger it now
```

Or the [Actions tab](https://github.com/Starfall10/pogo-event-calendar/actions).
Each run writes a summary saying what it saw; the last word of the first line
is `unchanged` or `updated`.

Runs are best-effort and GitHub skips many of them: measured over one night,
4 of 13 hourly slots fired, 9 to 51 minutes late. That is normal for a free
scheduled workflow and does not matter here, since events are announced weeks
ahead.

**Green runs with no commits is the normal state.** The job commits only when
the calendar actually changed, so a commit by `github-actions[bot]` means
something new was published.

## When something looks wrong

| Symptom | Where to look |
|---|---|
| Calendar not updating on the phone | Apple Calendar refreshes daily. Force it: View → Refresh Calendars (⌘R) |
| An event has no infographic link | Most posts announce nothing matchable. Only ~7 of 100 match; see `reconcile.py` |
| A run failed | You will have had an email. `gh run view <id> --log-failed` |
| `pogocal run` says "publishing without infographic links" | `.env` is missing, or the bot token is wrong |
| Times look an hour out | Stop. That is the floating-time bug. Nothing should ever attach a timezone |
