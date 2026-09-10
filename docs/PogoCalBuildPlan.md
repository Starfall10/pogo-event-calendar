# PoGO Cal — Build Plan

**For:** Kien
**Written:** 8 September 2026
**Repo name suggestion:** `pogo-cal`

---

## ⛔ Constraint added 8 September 2026 — this project costs nothing to run

**Read this before §1. It withdraws part of the plan below.**

The owner set a hard constraint after M1 landed: nothing in this project may
spend money, at any point, ever. Not a budget to manage — a line not to cross.

Everything else in this document stands. What it removes:

- **M3, vision extraction, is withdrawn.** It assumed one paid Anthropic API
  call per Discord post. There is no free substitute for reading an image, so
  the capability goes rather than being replaced.
- **§4.5 (Anthropic API key), the `anthropic` library in §7, and the running
  cost in §9 no longer apply.**
- **M4 changes shape** — see §6a. It still matches Discord posts to Leek Duck
  events, but on text and date rather than on an image extraction.

The original reasoning below is left intact rather than deleted. It explains
why vision was chosen and what it was for, which is worth keeping now that it
is not being used — and the matching rules in §5 survive almost unchanged.

**What the project still delivers with no cost:** every event with correct
dates and times from Leek Duck, richer descriptions from the feed's own
`extraData`, and a permanent link to the Discord infographic post on every
event that can be matched.

---

## 0. What this document is

A build plan for a system that turns Pokémon GO event announcements into
events in your Apple Calendar, automatically, forever, with no server to
maintain.

Drop this file in the repo root as `BUILD_PLAN.md` and point Claude Code at
it. Sections 1–5 are the design and should be read before any code is
written. Section 6 is the milestone list to actually work through. Sections
7–10 are reference you'll come back to.

Work one milestone at a time. Every milestone ends with something you can
run and check.

---

## 1. Scope

### What you're building

Your Discord server has a channel that follows an external Pokémon GO news
channel (G47IX). Each post is a title plus an infographic image packed with
event details — dates, times, bonuses, ticket prices, shiny odds.

This system reads those posts, works out what the event is and when it
happens, and publishes a calendar file you subscribe to in Apple Calendar.
Each calendar event carries a link straight back to the original Discord
post, so the infographic is one tap away.

### v1 feature set — what "done" means

| Feature | In v1 |
|---|---|
| Reads new posts from the followed channel | ✅ |
| ~~Extracts event details from the infographic~~ | ⛔ withdrawn — needs a paid API |
| Cross-checks dates against Leek Duck | ✅ |
| Publishes a subscribable `.ics` calendar | ✅ |
| Link to the original Discord post in each event | ✅ |
| Handles local-time vs global-time events correctly | ✅ |
| Updates events when details change | ✅ |
| Runs itself on a schedule, no server | ✅ |
| Archiving/re-hosting the infographics | ❌ — explicitly out |
| A web UI | ❌ v2 |
| Reminders/notifications | ❌ — Apple Calendar does that |
| Multiple source channels | ❌ v2 (but don't hard-code one) |

### Explicit non-goals

- **Keeping copies of the images.** If G47IX deletes a post, that calendar
  event's link dies. Accepted. It keeps the whole system to one moving part
  and sidesteps mirroring someone else's artwork.
- **A live/always-on bot.** See §2. The system polls on a schedule instead of
  holding a websocket open, which removes the need for hosting entirely.
- **Reading the external server directly.** You read your *own* channel, which
  Discord's follow feature fills for you. Reading someone else's server with
  your personal account is a self-bot and a ban risk. Never do it.

---

## 2. Decisions already made (and why)

**Poll the Discord REST API; do not run a gateway bot.**

The obvious design is a bot that stays connected to Discord and reacts the
instant a message arrives. That needs a process running 24/7, which needs
hosting, which needs monitoring. For events announced days or weeks in
advance, "within the hour" is fine.

So instead: a scheduled job asks Discord "any messages after ID X?", handles
whatever comes back, and exits. That job is a **GitHub Action**. No server, no
hosting bill, no uptime to worry about. This is the single most important
decision in the plan — it collapses the whole project into one scheduled
script.

**Leek Duck is the authority on timing; the infographic is the authority on
everything else.**

Vision models read these infographics well, but the images leave things out
that a human fills in from context — the Staraptor one has no year on it and
never says whether 2–5pm is local time. Meanwhile ScrapedDuck already
publishes exact, machine-readable start and end times sourced from Leek Duck.

Verified today: Leek Duck lists a Raid Day at `14:00–17:00` with no timezone
marker, which is precisely the 2–5pm local on your infographic. So: match each
Discord post to a Leek Duck event and take the dates from there. Fall back to
the vision extraction only when there's no match, and flag it.

**Discord deep link, not a hosted image.**

Every message has a permanent address:

```
https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
```

That never expires, needs no token, needs nothing running, and opens the
Discord app right on the post. The raw CDN image URL does the opposite — it
expires in about 24 hours — so it must never be written into a calendar event.

**Output is an `.ics` file on GitHub Pages.**

Apple Calendar subscribes to a URL and re-checks it daily. GitHub Pages serves
a static file from your repo for free. The Action rebuilds the file and commits
it; Pages serves the new version; your calendar picks it up. Nothing else
required.

**Python.**

The vision SDK, the Discord REST calls, and the calendar library are all
comfortable there, and it's what GitHub Actions runs with zero setup.

---

## 3. Concepts you'll meet

Things specific to this project that will confuse you if nobody warns you.

**Floating time.** Normally a calendar event has a timezone attached — "3pm in
London". A *floating* time has none: it means "3pm wherever you happen to be".
Pokémon GO events are almost all floating (an event runs 10am–8pm local time
everywhere on Earth simultaneously). If you attach a timezone to those, your
calendar will be wrong the moment you travel, and wrong for anyone you share it
with. In an `.ics` file, floating times are written with **no `Z` and no
`TZID`**:

```
DTSTART:20260919T140000        ← floating: 2pm wherever you are
DTSTART:20260919T140000Z       ← fixed: 2pm UTC, shows as 3pm in London
```

ScrapedDuck uses the same convention — no `Z` means local. So the rule is
simply: pass the marker through unchanged.

**UID and SEQUENCE.** Every calendar event needs a unique ID. If you generate a
fresh one each run, your calendar fills with duplicates. Use a stable ID
derived from the event itself, so a rebuilt event *replaces* the old one
instead of joining it. `SEQUENCE` is a counter you bump when the details
change, which tells well-behaved clients "this is a revision".

**Subscribed calendars are read-only.** You cannot edit or delete individual
events in Apple Calendar once subscribed. Everything is controlled by
regenerating the file. This is why the ICS builder is worth getting right
early — you can't paper over its mistakes by hand.

**Privileged intents.** Discord gates access to message *text* behind a toggle
called the Message Content Intent. It's free for bots in fewer than 100
servers, but it's off by default and the symptom of forgetting it is an empty
`content` field with no error. Turn it on in the Developer Portal before you
write any code.

**Crossposted messages.** When you "follow" a channel, the copies that land in
your server are webhook messages. They have a `webhook_id`, the author is the
*source channel's* name rather than a user, and the image may arrive as an
**attachment** or as an **embed** depending on how it was originally posted.
Your code must check both places. This is the single most likely thing to
silently return nothing.

---

## 4. Environment setup

1. **Create the Discord application.** discord.com/developers/applications →
   New Application → Bot tab → Reset Token, copy it somewhere safe (you only
   see it once).
2. **Enable Message Content Intent** on that same Bot tab. Scroll to
   Privileged Gateway Intents and switch it on. Do not skip this.
3. **Invite the bot to your server.** OAuth2 → URL Generator → scope `bot`,
   permissions `View Channels` + `Read Message History`. Nothing else — it
   never needs to send, react, or manage anything. Open the generated URL and
   add it to your server.
4. **Collect three IDs.** In Discord, Settings → Advanced → Developer Mode on.
   Then right-click → Copy ID on: your server (guild), the news channel, and
   any one existing post in it (you'll use that as the starting point so you
   don't reprocess years of history).
5. ~~**Anthropic API key** from console.anthropic.com for the vision calls.~~
   **Not needed.** Withdrawn by the constraint at the top of this document.
6. **Create the repo, public.** Public is required for free GitHub Pages. The
   only thing in it is public event info, so this is fine — but be aware the
   calendar URL is guessable, and never commit a token.
7. **Local env:** Python 3.12+, `uv` or a venv, and a `.env` holding
   `DISCORD_BOT_TOKEN`, `GUILD_ID`, `CHANNEL_ID`. There is no
   `ANTHROPIC_API_KEY` — see the constraint at the top of this document.
   `.env` goes in `.gitignore` on line one.

---

## 5. Architecture

Four stages, each independently runnable and testable. Resist merging them —
being able to run just the ICS builder against saved fixtures is what makes
this debuggable.

```
pogo-cal/
├── BUILD_PLAN.md
├── CLAUDE.md                    # see §10
├── README.md
├── pyproject.toml
├── .env.example
├── src/pogocal/
│   ├── __init__.py
│   ├── config.py                # env vars, constants, one place for tuning
│   ├── models.py                # the Event dataclass — the spine, see below
│   ├── discord_src.py           # poll REST, find images, build deep links
│   ├── vision.py                # image -> structured JSON
│   ├── leekduck.py              # fetch + parse ScrapedDuck
│   ├── reconcile.py             # merge the two sources
│   ├── ics_build.py             # Event list -> .ics text
│   ├── state.py                 # load/save the JSON state file
│   └── cli.py                   # subcommands: poll, build, run
├── state/
│   ├── cursor.json              # last processed message id
│   └── events/<event_id>.json   # one extracted event per file
├── docs/
│   └── pogo.ics                 # the published output (GitHub Pages)
├── tests/
│   ├── fixtures/*.png           # the two infographics, to start
│   ├── fixtures/*.json          # expected extraction for each
│   └── test_*.py
└── .github/workflows/update.yml
```

### Data flow

```
GitHub Action (every 3 hours)
        │
        ▼
  discord_src.poll()  ── GET /channels/{id}/messages?after=<cursor>
        │                 for each new message:
        │                   • find image (attachments[] OR embeds[].image.url)
        │                   • build permanent deep link
        │                   • download image bytes (URL is fresh right now)
        ▼
    vision.extract()  ── image bytes -> RawExtraction (name, dates, bonuses…)
        │
        │              leekduck.fetch() ── events.min.json (40-ish events)
        │                      │
        ▼                      ▼
        └──────► reconcile.merge() ◄──────┘
                        │   dates from Leek Duck when matched,
                        │   from vision when not (flagged low-confidence)
                        ▼
                 state/events/*.json   (committed, so it survives)
                        │
                        ▼
                  ics_build.render()
                        │
                        ▼
                   docs/pogo.ics  ──git commit──► GitHub Pages
                        │
                        ▼
              Apple Calendar (re-checks daily)
```

### The spine: the Event model

Get this right first; everything else is plumbing around it.

```python
@dataclass
class Event:
    event_id: str            # stable slug, e.g. "mega-staraptor-raid-day-2026-09-19"
    name: str
    event_type: str | None   # "raid-day", "event", "community-day"…
    start: datetime          # naive = floating/local, tz-aware = fixed
    end: datetime
    is_local_time: bool      # True -> emit floating; False -> emit UTC with Z
    summary_lines: list[str] # bonuses, ticket info, notes — for the description
    discord_url: str | None  # permanent deep link to the post
    leekduck_url: str | None
    source: str              # "leekduck" | "vision" | "merged"
    confidence: str          # "high" | "low"  — low = vision-only, unverified
    revision: int            # bump when content changes -> ICS SEQUENCE
```

### The one design decision worth thinking about

**How do you decide two records are the same event?**

You have a vision extraction saying *"Mega Staraptor Raid Day, 19 Sep,
2–5pm"* and a Leek Duck record saying *"Mega Staraptor Raid Day",
`2026-09-19T14:00:00.000`*. Matching these is the heart of `reconcile.py`.

Recommended rule, in order:

1. **Date first.** Filter Leek Duck candidates to those whose start date is
   within ±1 day of the extracted date. This alone usually leaves one or two.
2. **Then name similarity.** Slugify both (lowercase, strip punctuation and
   "pokémon"/"go"), compare with `difflib.SequenceMatcher`. Accept ≥ 0.6.
3. **Tie-break on event type** if the vision output guessed one.

If exactly one candidate survives → merge, `source="merged"`,
`confidence="high"`, dates from Leek Duck.
If none survive → keep the vision version, `confidence="low"`, and prefix the
calendar event title with `⚠️` so you can see at a glance which ones haven't
been verified.
If several survive → take the best score but mark it `low`.

Do **not** try to be clever here. A wrong merge is worse than no merge, and
the `⚠️` prefix costs you nothing.

### The year problem

The infographics show `19 SEP` with no year. Infer it from the Discord
message's own `timestamp` field:

> Take the year from the post date. If the resulting event date is more than
> 60 days *before* the post date, add one year.

That handles a December post announcing January events, which is the only case
that actually goes wrong.

---

## 6. Milestones

Each milestone is a working, runnable thing. Never spend two sessions without
something you can execute.

---

### M0 — A calendar that exists
*Est. 1 evening. You'll learn: the ICS format, Apple Calendar subscriptions.*

No Discord, no vision, no network. Prove the delivery pipe works before
building anything that fills it.

1. Repo skeleton, `pyproject.toml`, `models.py` with the `Event` dataclass.
2. `ics_build.py` using the `icalendar` library (not `ics` — `icalendar` is
   the maintained one with proper control over raw properties).
3. Hand-write two fake `Event` objects: one floating (2–5pm local), one
   multi-day.
4. Render to `docs/pogo.ics`. Calendar-level properties to set:

   ```
   X-WR-CALNAME:Pokémon GO
   REFRESH-INTERVAL;VALUE=DURATION:PT1440M
   X-PUBLISHED-TTL:PT1440M
   ```

   Per event: `UID` (stable), `SUMMARY`, `DTSTART`, `DTEND`, `DESCRIPTION`,
   `URL`, `SEQUENCE`. **No `VALARM`** — you don't want fifty notifications,
   and it's easier to never emit them than to strip them in Apple's UI.
5. Enable GitHub Pages: repo Settings → Pages → Deploy from branch `main`,
   folder `/docs`. Commit and push.
6. Subscribe in Apple Calendar: **File → New Calendar Subscription**, paste
   `https://<you>.github.io/pogo-cal/pogo.ics`, set Location to **iCloud** so
   it syncs to your phone, Auto-refresh **Every day**.

**Acceptance:** both fake events appear in Apple Calendar on your Mac *and*
your iPhone, at the right times, with a working link in the notes.

---

### M1 — Real events, no Discord
*Est. 1 evening. You'll learn: the ScrapedDuck feed, the floating-time rule.*

At the end of this milestone the project is already useful. If you stopped
here you'd have a working PoGO calendar.

1. `leekduck.py`: fetch
   `https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.min.json`
   and parse into `Event` objects.
2. **The timezone rule, implemented once, in one place:** if the `start`
   string ends in `Z`, parse as UTC-aware and set `is_local_time=False`;
   otherwise parse naive and set `is_local_time=True`. Add a test for both.
3. `event_id` = ScrapedDuck's `eventID` (already a stable slug — use it).
4. Description gets the Leek Duck link and the `heading`.
5. Rebuild `docs/pogo.ics` from real data. Commit, push.

**Acceptance:** your calendar shows the real upcoming events. Cross-check
three of them against leekduck.com by eye. Check that a Raid Day shows at
2pm *your* time and doesn't shift if you temporarily change your Mac's
timezone in System Settings — that's the floating-time test, and it's the one
that catches the bug that matters most.

---

### M2 — See the Discord posts
*Est. half an evening. You'll learn: the Discord REST API, crossposts.*

Still no vision. Just prove you can read the channel and get a permanent link.

1. `discord_src.py`: `GET https://discord.com/api/v10/channels/{id}/messages`
   with `after={cursor}&limit=100`, header `Authorization: Bot {token}`.
2. **Results come back newest-first — reverse them** before processing, or
   your cursor logic will be wrong.
3. For each message, find the image by checking, in order:
   `attachments[0].url` → `embeds[0].image.url` → `embeds[0].thumbnail.url`.
   Log loudly when none of the three has anything.
4. Build the deep link from `guild_id` / `channel_id` / `message.id`.
5. Save each message's raw JSON under `state/messages/` while developing —
   you'll want real examples to test against without hammering the API.
6. `state.py`: cursor is just the highest message ID seen. Seed it with the ID
   you copied in §4.4.

**Acceptance:** run `pogocal poll`, get a printed list of recent posts with a
Discord link for each. Click one — it opens the right post.

---

### ⛔ M3 — Read the infographics — WITHDRAWN 8 Sep 2026
*Superseded by §6a. Kept for its reasoning; do not build it.*

**This milestone requires a paid API and will not be built.** The prompt design
below is still the best record of what the infographics contain and what a
reader should refuse to guess at, which is why it stays in the document.

1. `vision.py`: send the image to the Anthropic API asking for strict JSON.
   Use **tool-use / structured output** rather than "please reply with JSON" —
   it's the difference between reliable and mostly-reliable.
2. The schema to ask for:

   ```json
   {
     "name": "string",
     "event_type": "raid-day|community-day|event|raid-hour|other",
     "start_date": "DD MMM or null",
     "end_date": "DD MMM or null",
     "start_time": "HH:MM or null",
     "end_time": "HH:MM or null",
     "explicitly_says_local_time": true,
     "bonuses": ["string"],
     "ticket": {"price": "string|null", "perks": ["string"]},
     "notes": ["string"]
   }
   ```

3. **Tell the model what not to guess.** Add to the prompt: *"If a detail is
   shown only as an icon with no text label — such as type or weakness
   symbols — omit it rather than guessing. If no year is shown, leave the year
   out."* Icon-reading is where these models are confidently wrong, and you get
   the reliable version of that data from Leek Duck anyway.
4. Apply the year rule from §5 using the message timestamp.
5. **Tests:** the two fixture images are in `tests/fixtures/`. Write the
   expected extraction as JSON beside each and assert on the fields that
   matter (name, dates, times, bonus count) — not on exact wording, which will
   drift between model versions.

**Acceptance:** both fixtures extract correctly. Harvest Festival must come
out as 29 Sep 10:00 → 5 Oct 20:00 with `explicitly_says_local_time: true`;
Staraptor as 19 Sep 14:00 → 17:00 with it `false` (the image genuinely doesn't
say — that's the correct answer, and M4 is what resolves it).

---

## 6a. The free path, replacing M3 — added 8 September 2026

M3 is withdrawn. This is what takes its place, and it costs nothing.

### What is actually lost

Only what appears **on the image and nowhere else**: the bonus lists, ticket
prices and perks, shiny-odds notes, and the wording of the graphic. That is
genuinely a loss and it should be stated rather than glossed over.

What is **not** lost: every event, with correct dates and times, and — this is
the part people assume needs the image — **the link to the infographic post
itself**. Getting that link needs the post identified, not read.

### The insight this rests on

The build plan assumed the only way to know which event a Discord post is about
was to read its picture. That is not the only way. Every crossposted message
carries, for free:

- a **timestamp**, which places it within a day or two of the event it announces
- **text** — the message content, and for a crossposted news item usually an
  embed title and description

§5's matching rule already filters candidates by date and then compares names.
It never needed the *image* — it needed a **name and a date**, and both arrive
in the message itself.

**What is unknown until M2:** how much text these particular crossposts carry.
If the embeds have titles, matching is straightforward. If a post is nothing
but an image with no text at all, that post cannot be matched and gets no link.
**Do not design past this point until M2 has printed real message JSON.** That
is a free thing to find out and it decides the rest.

### The revised milestones

**M3 (revised) — match posts to events, no image reading.**

- Take the message text — embed title first, then embed description, then the
  message content — as the name to match on.
- Filter Leek Duck candidates to those starting within a few days of the post
  timestamp, then compare names with `difflib.SequenceMatcher`, exactly as §5
  describes.
- On a match, attach `discord_url` to that event. Nothing else changes: dates,
  times and description all still come from the feed.
- On no match, log it and move on. An unmatched post is a missing link, not a
  broken calendar.
- `SOURCES` in `models.py` becomes `("leekduck", "discord", "merged")` —
  `"vision"` is removed, since nothing can produce it.

**M4 (revised) — richer descriptions from `extraData`.**

The feed already carries a per-event `extraData` object, present on all 55
events, with shapes including `generic`, `communityday`, `raidbattles` and
`spotlight`. It holds spawns, featured Pokémon and bonus information. It is
free, it is already downloaded, and it is machine-readable rather than read off
a picture.

This does not fully replace the infographic's bonus list, and it should not be
described as if it does. It is the free half of it.

**M5 is unchanged**, and gets simpler: with no per-post API call, the run has
one less thing that can fail and no cost to bound.

### The `⚠️` marker

Under the original plan it meant "dates came from an image and nothing verified
them". Nothing produces unverified dates now — every date comes from Leek Duck.
The marker is therefore unnecessary, and `confidence` can stay on the model,
always `"high"`, until something needs it.

### If the constraint is ever lifted

M3 as originally written is still in this document, above. Nothing built on the
free path blocks it: matching would gain a second signal rather than being
replaced, and `SOURCES` would regain `"vision"`. That is the only reason the
withdrawn milestone is kept rather than deleted.

---

### M4 — Merge the two sources — SEE §6a
*The matching rules here still hold. What is being matched has changed: a
Discord post's text and timestamp, not a vision extraction. Read §6a first.*

1. `reconcile.py` implementing the matching rule from §5.
2. Merged events: dates and `is_local_time` from Leek Duck, description body
   from the vision extraction (the bonuses and ticket detail Leek Duck's feed
   doesn't carry), both links attached.
3. Unmatched vision events: keep, mark `confidence="low"`, prefix the title
   with `⚠️`.
4. Description layout, in this order — first line matters most because it's
   what Apple Calendar shows in the collapsed view:

   ```
   📱 Infographic: https://discord.com/channels/…

   Bonuses:
   • Up to 5 additional daily Raid Passes from Gyms
   • Remote Raid limit increased to 20
   • Increased chance of Shiny Staraptor

   Ticket (5 USD, 14:00–17:00):
   • Up to 8 extra daily Raid Passes (14 total)
   • +5,000 XP and Stardust from Super Mega Raids

   📄 Details: https://leekduck.com/events/…
   ```

5. Set the `URL` property to the Discord link — Apple Calendar renders that as
   a dedicated clickable field.
6. Bump `revision` (→ `SEQUENCE`) when a stored event's content hash changes.

**Acceptance:** the Staraptor event in your calendar has Leek Duck's exact
times, the infographic's bonus list, and a working link to the Discord post.

---

### M5 — Make it run itself
*Est. half an evening. You'll learn: GitHub Actions, scheduled jobs.*

1. `.github/workflows/update.yml`, `on: schedule: cron: "0 * * * *"` plus
   `workflow_dispatch` so you can trigger it by hand while testing.
2. Permissions block: `contents: write` — the job commits the rebuilt `.ics`
   and the state files back to the repo. That commit is also what keeps the
   schedule alive (GitHub disables cron on repos with 60 days of no activity).
3. Secrets: `DISCORD_BOT_TOKEN` under repo Settings → Secrets and variables →
   Actions. That is the only one.
4. Make the job **idempotent and forgiving**: if one message cannot be
   handled, log it, skip it, don't advance the cursor past it, and still
   rebuild the calendar from everything else. One bad post must never wedge
   the pipeline.
5. Commit only when the output actually changed, or you'll get a pointless
   commit every hour.

**Acceptance:** trigger it manually, watch it green, see a new commit. Then
leave it alone for a day and check a real new event turned up on your phone
without you touching anything.

---

### M6 — Live with it
*Ongoing.*

Use it for a couple of weeks and keep a list. Likely v2 candidates:

- A second calendar file filtered to only the events you care about
  (skip Raid Hour and Spotlight Hour, keep Community Days) — this is a
  one-line filter and probably the first thing you'll want
- A GitHub Pages HTML page per event, so the calendar link opens infographic
  *and* text in a browser instead of the Discord app
- Multiple source channels
- A weekly digest posted back into your own Discord
- Alerts only on Community Days, via a `VALARM` on selected event types

---

## 7. API cheat sheet

**Discord REST** — base `https://discord.com/api/v10`, header
`Authorization: Bot {token}`

| What | Call |
|---|---|
| New messages | `GET /channels/{channel_id}/messages?after={id}&limit=100` |
| One message | `GET /channels/{channel_id}/messages/{message_id}` |
| Permanent post link | `https://discord.com/channels/{guild_id}/{channel_id}/{message_id}` |

Message fields you need: `id`, `timestamp` (ISO 8601), `content`,
`attachments[]` (`url`, `content_type`, `width`, `height`), `embeds[]`
(`image.url`, `thumbnail.url`, `title`, `description`), `webhook_id`.

Rate limits: honour `X-RateLimit-Remaining` and `Retry-After`. At one poll an
hour you will never come close, but handle 429 anyway.

**ScrapedDuck**

- `https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.min.json`
- Fields: `eventID`, `name`, `eventType`, `heading`, `link`, `image`,
  `start`, `end`, `extraData`
- **Timezone convention:** trailing `Z` = fixed UTC (global event); no `Z` =
  local time (everything else). Verified: a Raid Day reads
  `"start":"2026-07-18T14:00:00.000"` — no `Z`, i.e. 2pm wherever you are.
- Around 40 events at a time. Past events drop off, so anything you want to
  keep must live in your own state files.

**Python libraries**

| Job | Library |
|---|---|
| ICS output | `icalendar` |
| HTTP | `httpx` |
| ~~Vision~~ | ~~`anthropic`~~ — withdrawn, see the constraint at the top |
| Fuzzy match | `difflib` (stdlib — no dependency needed) |
| Config | `python-dotenv` |

---

## 8. Gotchas, collected

1. **Discord CDN links expire in ~24 hours.** Never write `attachments[].url`
   into a calendar event. Download it during the run; put the deep link in the
   calendar.
2. **Message Content Intent is off by default.** Symptom: empty `content`, no
   error. §4.2.
3. **Crossposted images may be in `embeds`, not `attachments`.** Check both.
   This will be your first "why is it finding nothing" hour.
4. **`?after=` returns newest-first.** Reverse before processing.
5. **Never attach a timezone to a local-time event.** The whole calendar is
   wrong for anyone who travels. Test it by changing your Mac's timezone.
6. **Unstable UIDs cause duplicates.** Derive the ID from the event, never
   from a timestamp, a hash of the description, or a counter.
7. **Subscribed calendars are read-only.** No hand-fixing. The file is the
   only lever you have.
8. **The infographics have no year.** §5. Only bites in December.
9. **Icon-only data is a guess.** Type and weakness circles have no text.
   Don't extract them; get them from Leek Duck or leave them out.
10. **GitHub Actions cron is best-effort and often runs late** — sometimes 10+
    minutes. Irrelevant here, but don't be alarmed by it.
11. **GitHub disables scheduled workflows after 60 days of repo inactivity.**
    The job's own commits count as activity, so this only bites if the job has
    also been failing silently. Turn on Actions failure notifications.
12. **Public repo = public calendar.** Fine for this. Just never commit
    `.env`, and put it in `.gitignore` before the first commit, not after.
13. **One bad image must not wedge the run.** Catch per-message, log, skip,
    keep going, don't advance the cursor past the failure.

---

## 9. Rough schedule

| Milestone | Estimate |
|---|---|
| Setup + M0 | 1 evening |
| M1 | 1 evening |
| M2 | ½ evening |
| M3 | 1 evening |
| M4 | 1 evening |
| M5 | ½ evening |
| **v1 total** | **5 evenings** |

Running cost: **nothing.** GitHub Actions and Pages are free on a public
repository, the Discord REST API is free, and the ScrapedDuck feed is a static
file. There is no metered service anywhere in the system, by constraint.

---

## 10. Starter `CLAUDE.md`

Put this in the repo root alongside the plan.

```markdown
# pogo-cal

Turns Pokémon GO event posts from a followed Discord channel into a
subscribable .ics calendar. See BUILD_PLAN.md for the full design.

## Ground rules

- Work one milestone at a time (BUILD_PLAN.md §6). Do not skip ahead.
  Each milestone must run and pass its acceptance check before the next.
- Python 3.12+, `uv` for deps. Keep the four stages separate and
  independently runnable — never merge poll/extract/reconcile/build.
- Discord CDN image URLs expire in ~24h. They may be downloaded during a
  run; they must NEVER be written into calendar output.
- Timezone handling lives in exactly one place. Naive datetime = floating
  local time. Aware datetime = fixed UTC. Never attach a named timezone.
- Nothing in this project may spend money. No paid API, no metered service.
- Leek Duck is authoritative for dates and times, and is the only source of
  event detail.
- Every network call needs a timeout and a retry. Every per-message failure
  is caught, logged, and skipped — one bad post never stops the run.
- No secrets in code or committed files. `.env` is gitignored.

## Commands

    uv run pogocal poll     # fetch new Discord messages, extract, save state
    uv run pogocal build    # rebuild docs/pogo.ics from state + Leek Duck
    uv run pogocal run      # poll then build (what the Action runs)
    uv run pytest

## Testing

Fixtures in tests/fixtures/ are real infographics with expected extractions
beside them. Assert on structured fields (name, dates, times, bonus count),
never on exact wording — that drifts between model versions.
```

---

## First three things to do

1. Create the Discord app, **turn on Message Content Intent**, invite the bot,
   collect the three IDs (§4.1–4.4).
2. Build M0 — two fake events, published to Pages, subscribed on your Mac and
   phone. Don't touch Discord until this works.
3. Build M1 — real Leek Duck events. At that point you have a genuinely
   useful calendar, and everything after is enrichment.

The two infographics you sent are in `tests/fixtures/` ready for M3.