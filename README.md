# pogo-event-calendar

Turns Pokémon GO event announcements into a calendar you can subscribe to.

A Discord channel in my server follows an external Pokémon GO news channel.
Each post is an infographic packed with event details. This reads those posts,
works out what the event is and when it happens, and publishes an `.ics`
calendar file. Apple Calendar subscribes to it and stays up to date on its own.

Every calendar event links back to the original Discord post, so the
infographic is one tap away.

## Subscribe

```
https://<username>.github.io/pogo-event-calendar/pogo.ics
```

**Apple Calendar (Mac):** File → New Calendar Subscription → paste the URL.
Set Location to **iCloud** so it syncs to your phone, Auto-refresh to
**Every day**, and tick **Remove: Alerts**.

**iPhone only:** Settings → Apps → Calendar → Calendar Accounts → Add Account
→ Other → Add Subscribed Calendar.

Subscribed calendars are read-only — you can't edit the events, only hide the
calendar or unsubscribe.

## How it works

```
Discord channel  ──►  vision model  ──┐
(followed news)      (reads the           ├──►  merge  ──►  pogo.ics  ──►  Apple Calendar
                      infographic)        │              (GitHub Pages)
Leek Duck feed  ─────────────────────────┘
(exact dates)
```

Two sources, each doing what it's good at. The infographics carry the bonuses,
ticket details and notes, but they have no year on them and often don't say
whether times are local. [Leek Duck](https://leekduck.com), via
[ScrapedDuck](https://github.com/bigfoott/ScrapedDuck), gives exact machine-readable
start and end times. The two get matched on date and name; Leek Duck wins on
timing, the infographic wins on everything else.

Anything that can't be matched still goes in the calendar, with a ⚠️ on the
title so it's obvious it hasn't been verified.

No server. A GitHub Action runs hourly, rebuilds the calendar file, and commits
it. That's the whole deployment.

## Setup

Needs a Discord bot token, an Anthropic API key, and a public repo with GitHub
Pages serving `/docs`.

```bash
git clone https://github.com/<username>/pogo-event-calendar.git
cd pogo-event-calendar
uv sync
cp .env.example .env      # fill in tokens and IDs
```

`.env`:

```
DISCORD_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
GUILD_ID=...
CHANNEL_ID=...
```

The Discord bot needs **View Channels** and **Read Message History**, and the
**Message Content Intent** switched on in the Developer Portal — it's off by
default and the symptom of forgetting is empty message text with no error.

Full setup walkthrough in [`BUILD_PLAN.md`](BUILD_PLAN.md) §4.

## Commands

```bash
uv run pogocal poll     # fetch new Discord posts, extract, save state
uv run pogocal build    # rebuild docs/pogo.ics from state + Leek Duck
uv run pogocal run      # poll then build (what the Action runs)
uv run pytest
```

## Layout

```
src/pogocal/       poll → extract → reconcile → build, one module each
state/             cursor + one JSON file per extracted event (committed)
docs/pogo.ics      the published calendar
tests/fixtures/    real infographics with expected extractions
```

## Notes

**Times are floating.** Most Pokémon GO events run at the same local hour
everywhere on Earth, so the calendar stores them with no timezone attached.
A 2pm Raid Day shows as 2pm wherever you are. That's deliberate — attaching a
timezone would make the calendar wrong the moment you travel.

**Discord image links expire after about 24 hours.** They're downloaded during
a run and never written into calendar output. The calendar carries the
permanent message link instead.

**Deleted posts break their links.** No copies of the images are kept. If the
source post goes, that event's infographic link goes with it. Accepted
trade-off.

## Credit

Event data from [Leek Duck](https://leekduck.com) via
[ScrapedDuck](https://github.com/bigfoott/ScrapedDuck). Infographics by
[G47IX](https://linktr.ee/g47ix). Personal project, not affiliated with either,
or with Niantic or The Pokémon Company.