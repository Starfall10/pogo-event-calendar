"""Turns Event records into the text of the published web page.

The same shape as ics_build.py: Events in, a string out. It opens no files and
fetches nothing, so it can be rendered from saved data with no network. The
module that downloads infographics is separate, and this one takes the result
as a plain mapping — a missing image is never an error here.

Two rules it holds:

  * The page shows only what has not finished, and what it shows depends on
    the date it was built. That date is passed in rather than read from the
    clock, so the output is stable within a day. A page that differed every
    time it was built would make the scheduled job commit on every run.
  * Images are referenced by their local path. A Discord CDN url expires in
    about 24 hours and must never reach anything that is kept.
"""

from datetime import date, datetime
from html import escape
from typing import Iterable

from pogocal import config
from pogocal.models import Event

# The feed's own type names, in the reader's words. Anything unlisted falls
# back to the raw value rather than being hidden.
TYPE_LABELS = {
    "community-day": "Community Day", "raid-day": "Raid Day",
    "raid-hour": "Raid Hour", "pokemon-spotlight-hour": "Spotlight Hour",
    "go-battle-league": "Battle League", "max-mondays": "Max Monday",
    "max-battles": "Max Battle", "raid-battles": "Raids",
    "event": "Event", "go-pass": "GO Pass", "season": "Season",
}

# Types worth planning around, given the accent colour. The rest are the
# weekly furniture.
NOTABLE_TYPES = frozenset({"community-day", "raid-day", "event", "season", "go-pass"})


def render(events: Iterable[Event], today: date | None = None,
           images: dict[str, str] | None = None) -> str:
    """Render upcoming events as a complete HTML page."""
    today = today or date.today()
    images = images or {}

    upcoming = sorted((e for e in events if _naive(e.end).date() >= today),
                      key=lambda e: (_naive(e.start), e.event_id))

    counts: dict[str, int] = {}
    for event in upcoming:
        label = TYPE_LABELS.get(event.event_type, event.event_type or "Event")
        counts[label] = counts.get(label, 0) + 1

    with_images = sum(1 for e in upcoming if e.discord_url)
    chips = "".join(
        f'<li><span class="n">{n}</span>{escape(label)}</li>'
        for label, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    months, current = [], None
    for event in upcoming:
        key = f"{_naive(event.start):%Y-%m}"
        if current is None or current[0] != key:
            current = (key, f"{_naive(event.start):%B %Y}", [])
            months.append(current)
        current[2].append(event)

    sections = "\n".join(
        f'    <section class="month">\n'
        f'      <h2>{label}</h2>\n'
        f'      <ul class="rows">\n'
        + "\n".join(_row(e, today, images) for e in items)
        + f"\n      </ul>\n    </section>"
        for _key, label, items in months)

    return _PAGE.format(
        style=_STYLE,
        count=len(upcoming),
        with_images=with_images,
        chips=chips,
        sections=sections,
        calendar_url=config.CALENDAR_URL,
    )


def _row(event: Event, today: date, images: dict[str, str]) -> str:
    start, end = _naive(event.start), _naive(event.end)
    running = start.date() <= today <= end.date()

    badge = ' <span class="now">today</span>' if running else ""
    label = TYPE_LABELS.get(event.event_type, event.event_type or "Event")
    notable = " big" if event.event_type in NOTABLE_TYPES else ""

    when, zone = _times(event, start, end)

    links = []
    if event.discord_url:
        links.append(f'<a class="lk ig" href="{escape(event.discord_url)}">Post</a>')
    if event.leekduck_url:
        links.append(f'<a class="lk" href="{escape(event.leekduck_url)}">Leek Duck</a>')

    figure = ""
    image = images.get(event.event_id)
    if image:
        figure = (
            f'\n        <details class="ig-wrap">'
            f'<summary>Infographic</summary>'
            f'<img src="{escape(image)}" alt="Infographic for {escape(event.name)}"'
            f' loading="lazy" decoding="async">'
            f'<p class="credit">Infographic by G47IX</p>'
            f'</details>')

    return f"""      <li class="row{' live' if running else ''}">
        <div class="date">{_day_cell(start, end)}</div>
        <div class="body">
          <h3>{escape(event.name)}{badge}</h3>
          <p class="meta"><span class="type{notable}">{escape(label)}</span></p>{figure}
        </div>
        <div class="when"><span class="t">{when}</span><span class="z">{zone}</span></div>
        <div class="links">{"".join(links)}</div>
      </li>"""


def _day_cell(start: datetime, end: datetime) -> str:
    if start.date() == end.date():
        return f'<span class="d">{start.day}</span><span class="m">{start:%a}</span>'
    return f'<span class="d">{start.day}</span><span class="m">–{end.day} {end:%b}</span>'


def _times(event: Event, start: datetime, end: datetime) -> tuple[str, str]:
    """What time it runs, and which kind of time that is.

    The distinction this whole project exists to get right, said plainly on
    the page rather than left implicit.
    """
    if event.is_local_time:
        if start.date() == end.date():
            return f"{start:%H:%M}–{end:%H:%M}", "local time"
        return f"{start:%H:%M} → {end.day} {end:%b} {end:%H:%M}", "local time"
    return f"{start:%H:%M}", "UTC, fixed"


def _naive(moment: datetime) -> datetime:
    """Drop the timezone for ordering and grouping only. What each event says
    about its own time is decided in _times above."""
    return moment.replace(tzinfo=None) if moment.tzinfo else moment


_STYLE = """
:root {
  --ground:#f7f8f6; --surface:#ffffff; --ink:#15211c; --muted:#5c6b64;
  --line:#dfe4e0; --line-soft:#eceeeb; --accent:#1f7a5c; --accent-soft:#e6f1ec;
  --amber:#a8681a; --amber-soft:#f7ecdd;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#101613; --surface:#18201c; --ink:#e7ece9; --muted:#93a49b;
    --line:#28322c; --line-soft:#1f2823; --accent:#54b891; --accent-soft:#172a22;
    --amber:#d69a4a; --amber-soft:#2a2118;
  }
}
:root[data-theme="dark"] {
  --ground:#101613; --surface:#18201c; --ink:#e7ece9; --muted:#93a49b;
  --line:#28322c; --line-soft:#1f2823; --accent:#54b891; --accent-soft:#172a22;
  --amber:#d69a4a; --amber-soft:#2a2118;
}
* { box-sizing:border-box; }
body {
  margin:0; background:var(--ground); color:var(--ink);
  font:400 15px/1.5 "IBM Plex Sans", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing:antialiased;
}
.wrap { max-width:60rem; margin:0 auto; padding:2.5rem 1.25rem 4rem; }
header { display:flex; flex-wrap:wrap; gap:1.25rem 2rem; align-items:flex-end;
  justify-content:space-between; padding-bottom:1.25rem; border-bottom:2px solid var(--ink); }
h1 { font:700 1.9rem/1.1 Archivo, system-ui, sans-serif; margin:0; letter-spacing:-.02em; text-wrap:balance; }
.sub { color:var(--muted); font-size:.875rem; margin:.4rem 0 0; }
.sub b { color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.subscribe { display:inline-flex; align-items:center; gap:.5rem; background:var(--accent);
  color:#fff; text-decoration:none; font:600 .875rem/1 "IBM Plex Sans", sans-serif;
  padding:.7rem 1rem; border-radius:6px; }
.subscribe:hover { filter:brightness(1.08); }
.subscribe span { font-family:"IBM Plex Mono", monospace; opacity:.75; font-weight:400; }
.legend { list-style:none; display:flex; flex-wrap:wrap; gap:.4rem; margin:1.5rem 0 0; padding:0; }
.legend li { display:flex; align-items:baseline; gap:.4rem; border:1px solid var(--line);
  border-radius:999px; padding:.3rem .7rem; font-size:.78rem; color:var(--muted); background:var(--surface); }
.legend .n { font:500 .8rem "IBM Plex Mono", monospace; color:var(--ink); font-variant-numeric:tabular-nums; }
.month { margin-top:2.75rem; }
.month > h2 { font:600 .78rem/1 "IBM Plex Sans", sans-serif; text-transform:uppercase;
  letter-spacing:.13em; color:var(--muted); margin:0 0 .75rem; }
.rows { list-style:none; margin:0; padding:0; border-top:1px solid var(--line); }
.row { display:grid; grid-template-columns:3.25rem 1fr auto auto; gap:1rem;
  align-items:baseline; padding:.85rem .25rem .85rem .5rem; border-bottom:1px solid var(--line-soft); }
.row.live { background:var(--amber-soft); box-shadow:inset 3px 0 0 var(--amber); border-radius:2px; }
.date { font-family:"IBM Plex Mono", monospace; font-variant-numeric:tabular-nums; line-height:1.2; }
.date .d { display:block; font-size:1.25rem; font-weight:500; }
.date .m { display:block; font-size:.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }
.body h3 { font:600 1rem/1.3 "IBM Plex Sans", sans-serif; margin:0; text-wrap:balance; }
.meta { margin:.28rem 0 0; display:flex; flex-wrap:wrap; gap:.5rem; align-items:baseline; }
.type { font-size:.72rem; letter-spacing:.04em; text-transform:uppercase; color:var(--muted); }
.type.big { color:var(--accent); font-weight:600; }
.now { font:600 .68rem/1 "IBM Plex Sans", sans-serif; text-transform:uppercase;
  letter-spacing:.07em; padding:.22rem .4rem; border-radius:3px; vertical-align:.12em;
  margin-left:.4rem; background:var(--amber); color:#fff; }
.when { text-align:right; font-family:"IBM Plex Mono", monospace; font-variant-numeric:tabular-nums; line-height:1.25; }
.when .t { display:block; font-size:.86rem; }
.when .z { display:block; font-size:.68rem; color:var(--muted); letter-spacing:.02em; }
.links { display:flex; gap:.75rem; }
.lk { font-size:.78rem; color:var(--muted); text-decoration:none; border-bottom:1px solid var(--line); white-space:nowrap; }
.lk:hover { color:var(--ink); border-color:var(--ink); }
.lk.ig { color:var(--accent); border-color:var(--accent-soft); font-weight:500; }
.ig-wrap { margin-top:.6rem; }
.ig-wrap > summary { display:inline-block; cursor:pointer; font-size:.78rem; color:var(--accent);
  border:1px solid var(--accent-soft); border-radius:4px; padding:.2rem .55rem; list-style:none; }
.ig-wrap > summary::-webkit-details-marker { display:none; }
.ig-wrap > summary::before { content:"\25B8 "; }
.ig-wrap[open] > summary::before { content:"\25BE "; }
.ig-wrap > summary:hover { background:var(--accent-soft); }
.ig-wrap img { display:block; width:100%; max-width:32rem; height:auto; margin:.75rem 0 .35rem;
  border:1px solid var(--line); border-radius:4px; background:var(--surface); }
.credit { margin:0 0 .25rem; font-size:.72rem; color:var(--muted); }
footer { margin-top:3rem; padding-top:1.25rem; border-top:1px solid var(--line);
  color:var(--muted); font-size:.8rem; display:flex; flex-wrap:wrap; gap:.5rem 1.5rem; }
footer a { color:var(--muted); }
a:focus-visible, .subscribe:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
@media (max-width:640px) {
  .row { grid-template-columns:2.75rem 1fr; gap:.5rem .9rem; }
  .when { grid-column:2; text-align:left; }
  .links { grid-column:2; }
}
"""


_PAGE = """<title>Pokémon GO Events</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{style}</style>
<div class="wrap">
  <header>
    <div>
      <h1>Pokémon GO Events</h1>
      <p class="sub"><b>{count}</b> upcoming · <b>{with_images}</b> with an infographic · rebuilt every 3 hours from Leek&nbsp;Duck</p>
    </div>
    <a class="subscribe" href="{calendar_url}">Subscribe <span>.ics</span></a>
  </header>
  <ul class="legend">{chips}</ul>
{sections}
  <footer>
    <span><b>Local time</b> means the same clock time everywhere — a 2pm Raid Day is 2pm wherever you are.</span>
    <span><b>UTC, fixed</b> is one moment worldwide.</span>
    <span>Event data from <a href="https://leekduck.com">Leek Duck</a>. Infographics by G47IX.</span>
  </footer>
</div>
"""
