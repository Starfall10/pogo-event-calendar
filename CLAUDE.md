# pogo-event-calendar

Turns Pokémon GO event posts from a followed Discord channel into a
subscribable `.ics` calendar. See [docs/PogoCalBuildPlan.md](docs/PogoCalBuildPlan.md)
for the full design; §6 is the milestone list, §8 is the gotchas.

## The hard constraint: this project costs nothing to run

**Nothing in this repository may spend money. There is no budget and this is
not a trade-off to be weighed — it is a line.**

Every part of the system runs on something free: the Discord REST API, the
ScrapedDuck feed, GitHub Actions, GitHub Pages. No paid API, no metered
service, no hosting, no credits.

Concretely, and permanently:

- **No calls to the Anthropic API, or any other paid model API.** No
  `anthropic` dependency, no `ANTHROPIC_API_KEY`, no vision extraction. The
  build plan's M3 assumed one call per Discord post; that milestone is
  withdrawn, not deferred. See §6a of the build plan.
- **No paid service of any kind**, including anything with a free tier that
  bills after a threshold. A free tier is a bill waiting for a busy month.
- **The repository stays public**, because GitHub Pages and Actions are only
  free that way.
- **If a feature cannot be built for nothing, it does not get built.** Say so
  plainly and stop. Do not price it, do not propose it as an option, and do
  not implement it behind a flag that is off by default.

The owner's subscription to Claude does not cover API usage — that is billed
separately — so "I have a subscription" never satisfies this rule.

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
- Leek Duck is authoritative for dates and times, and is the only source of
  event detail. Richer descriptions come from the feed's own `extraData`, not
  from reading the infographics.
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

Fixtures in `tests/fixtures/` are saved copies of real data — the feed, and
real Discord message JSON. Assert on structured fields, never on exact wording.
Tests run offline: no Discord call and no feed fetch, so the suite needs no
network and no credentials.

A green suite is not a correct calendar. Rebuild `docs/pogo.ics` and read it.

## Working rhythm

Skills in `.claude/skills/` define how work is done here — read
`work-the-plan` before any change touching more than one file, and `catchup` at
the start of a session.
