# pogo-event-calendar

Turns Pokémon GO event posts from a followed Discord channel into a
subscribable `.ics` calendar. See [docs/PogoCalBuildPlan.md](docs/PogoCalBuildPlan.md)
for the full design; §6 is the milestone list, §8 is the gotchas.

## Ground rules

- Work one milestone at a time (build plan §6). Do not skip ahead. Each
  milestone must run and pass its acceptance check before the next.
- Python 3.12+, `uv` for dependencies. Keep the four stages separate and
  independently runnable — never merge poll / extract / reconcile / build.
- Discord CDN image URLs expire in about 24 hours. They may be downloaded
  during a run; they must NEVER be written into calendar output or committed
  state.
- Timezone handling lives in exactly one place. Naive datetime = floating local
  time. Aware datetime = fixed UTC. Never attach a named timezone.
- Leek Duck is authoritative for dates and times. Vision output is
  authoritative for bonuses and descriptions. Never let vision override a
  matched Leek Duck date.
- `UID` is derived from the event's own identity, never from a timestamp,
  counter or hash of wording. An unstable `UID` duplicates every event, and a
  subscribed calendar is read-only, so duplicates cannot be deleted by hand.
- Every network call needs a timeout and a retry. Every per-message failure is
  caught, logged and skipped — one bad post never stops the run, and the cursor
  never advances past a failure.
- Anything that finds nothing logs loudly. Nobody reports a bug on this system;
  a quiet nothing is the normal failure.
- Thresholds, URLs, model names and paths live in `config.py`, never inline.
- No secrets in code or committed files. `.env` is gitignored. This repository
  is public.

## Commands

    uv run pogocal poll     # fetch new Discord messages, extract, save state
    uv run pogocal build    # rebuild docs/pogo.ics from state + Leek Duck
    uv run pogocal run      # poll then build (what the Action runs)
    uv run pytest

`poll` spends API credit and moves the cursor. Use it deliberately.

## Testing

Fixtures in `tests/fixtures/` are real infographics with expected extractions
beside them. Assert on structured fields (name, dates, times, bonus count),
never on exact wording — that drifts between model versions. Tests run offline:
no Discord call, no vision call, no feed fetch.

A green suite is not a correct calendar. Rebuild `docs/pogo.ics` and read it.

## Working rhythm

Skills in `.claude/skills/` define how work is done here — read
`work-the-plan` before any change touching more than one file, and `catchup` at
the start of a session.
