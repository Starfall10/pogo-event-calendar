"""Turns Event records into the text of the published web page.

Same shape as ics_build.py: Events in, a string out. It opens no files and
fetches nothing, so the whole of it is tested against saved data.

The page is not the calendar. The calendar carries everything the feed lists;
the page leaves off what the owner does not want to see — league rotations, and
Wild Areas in cities they cannot reach.

Three rules it holds:

  * What the page shows depends on the date it was built, so `today` is passed
    in rather than read from the clock. A page that changed with the hour would
    make the scheduled job commit every time it ran.
  * Everything the feed does not carry — artwork, weaknesses, infographics —
    arrives as plain mappings. A missing entry is never an error; most events
    have no Pokémon, and three name one that has not been announced.
  * Images are referenced by their local path. A Discord CDN url expires in
    about a day and must never reach anything that is kept.
"""

from datetime import date, datetime
from html import escape
from typing import Any, Iterable

from pogocal import config
from pogocal.models import Event
from pogocal.type_icons import COLOURS, SYMBOLS

# Left off the page. They stay in the calendar file.
HIDDEN_TYPES = frozenset({"go-battle-league"})

# A Wild Area is a real-world event in one city. Only the global one is
# playable from anywhere.
CITY_EVENT_TYPES = frozenset({"wild-area"})

# Longer than this and an event is not "on" any particular day, so repeating it
# inside every day card says nothing. It becomes a ribbon at the top instead.
RIBBON_AFTER_DAYS = 14

# One colour family per kind of event: background, motif tint, ink, and what to
# call it. Colour here is a label — you should be able to tell a Community Day
# from a Raid Hour across the room.
KINDS: dict[str, tuple[str, str, str, str]] = {
    "community-day":          ("#ffe3ec", "#ffc3d6", "#c02a5e", "Community Day"),
    "raid-day":               ("#ffe2d4", "#ffc2a6", "#c4471c", "Raid Day"),
    "raid-hour":              ("#ffeccd", "#ffd79a", "#b4661a", "Raid Hour"),
    "pokemon-spotlight-hour": ("#fff2cc", "#fbe09a", "#a86e00", "Spotlight Hour"),
    "raid-battles":           ("#e0e6ff", "#c3cdff", "#3948a8", "Raids"),
    "max-mondays":            ("#f2ddff", "#e3bcff", "#7c30b4", "Max Monday"),
    "max-battles":            ("#ffe0f4", "#ffc0e8", "#b02a7e", "Max Battle"),
    "event":                  ("#d7f0ee", "#b6e3e0", "#1d7f79", "Event"),
    "wild-area":              ("#dcefff", "#bcdfff", "#1f6ba8", "Wild Area"),
    "go-pass":                ("#d9f2e3", "#b6e4c9", "#1f7f4d", "GO Pass"),
    "season":                 ("#e6e1ff", "#cec6ff", "#4f41ac", "Season"),
}
DEFAULT_KIND = ("#eceae4", "#dcd8cf", "#5b5468", "Event")


def render(events: Iterable[Event], today: date | None = None,
           images: dict[str, str] | None = None,
           details: dict[str, dict[str, Any]] | None = None) -> str:
    """Render what is coming up as a complete HTML page."""
    today = today or date.today()
    images = images or {}
    details = details or {}

    showing = sorted(
        (e for e in events if _worth_showing(e, today)),
        key=lambda e: (_naive(e.start), e.event_id))

    ribbons = [e for e in showing if _runs_for(e) > RIBBON_AFTER_DAYS]
    dated = [e for e in showing if e not in ribbons]

    days: list[tuple[date, list[Event]]] = []
    for event in dated:
        when = _naive(event.start).date()
        if not days or days[-1][0] != when:
            days.append((when, []))
        days[-1][1].append(event)

    return _PAGE.format(
        style=_STYLE,
        today=f"{today:%A %-d %B}",
        ribbons="\n".join(_ribbon(e, today) for e in ribbons),
        days="\n".join(_day(when, items, today, images, details)
                       for when, items in days),
        calendar_url=config.CALENDAR_URL,
    )


def _worth_showing(event: Event, today: date) -> bool:
    if _naive(event.end).date() < today:
        return False
    if event.event_type in HIDDEN_TYPES:
        return False
    if event.event_type in CITY_EVENT_TYPES and "global" not in event.name.lower():
        return False
    return True


def _runs_for(event: Event) -> int:
    return (_naive(event.end).date() - _naive(event.start).date()).days


def _ribbon(event: Event, today: date) -> str:
    _bg, _tint, ink, kind = KINDS.get(event.event_type, DEFAULT_KIND)
    left = (_naive(event.end).date() - today).days
    return (f'    <div class="ribbon" style="--rc:{ink}">'
            f'<b>{escape(event.name)}</b><small>{escape(kind.lower())}</small>'
            f'<span class="days">{left} days left</span></div>')


def _day(when: date, items: list[Event], today: date,
         images: dict[str, str], details: dict[str, dict[str, Any]]) -> str:
    posters = "\n".join(_poster(e, today, images, details) for e in items)
    return (f'  <article class="day{" now" if when == today else ""}">\n'
            f'    <div class="spine"><div class="wd">{when:%a}</div>'
            f'<div class="n">{when.day}</div><div class="mo">{when:%b}</div></div>\n'
            f'    <div class="deck">\n{posters}\n    </div>\n  </article>')


def _poster(event: Event, today: date, images: dict[str, str],
            details: dict[str, dict[str, Any]]) -> str:
    bg, tint, ink, kind = KINDS.get(event.event_type, DEFAULT_KIND)
    detail = details.get(event.event_id, {})
    pokemon = detail.get("pokemon") or {}
    start, end = _naive(event.start), _naive(event.end)

    hero = (f'<img class="hero" src="{escape(pokemon["sprite"])}" alt="" '
            f'loading="lazy" decoding="async">'
            if pokemon.get("sprite") else '<div class="hero ball"></div>')

    weak = "".join(
        f'<span class="tp" style="--c:{COLOURS[t]}" title="{t}">'
        f'<svg viewBox="0 0 512 512" aria-hidden="true">{SYMBOLS[t]}</svg></span>'
        for t in pokemon.get("weaknesses", ()) if t in SYMBOLS)

    # The feed gives Community Day bonuses their own icons; a Spotlight Hour
    # bonus is text alone. Both are worth showing.
    bonuses = "".join(
        '<span class="bon">'
        + (f'<img src="{escape(b["icon"])}" alt="" loading="lazy">' if b.get("icon") else "")
        + f'{escape(b["text"])}</span>'
        for b in detail.get("bonuses", ()) if b.get("text"))

    figure = ""
    local = images.get(event.event_id)
    if local:
        figure = (f'<details class="ig"><summary>Infographic</summary>'
                  f'<img src="{escape(local)}" alt="Infographic for {escape(event.name)}"'
                  f' loading="lazy" decoding="async">'
                  f'<span class="credit">by G47IX</span></details>')

    links = ""
    if event.discord_url:
        links += f'<a href="{escape(event.discord_url)}">The post</a>'
    if event.leekduck_url:
        links += f'<a href="{escape(event.leekduck_url)}">Leek Duck</a>'

    return f'''      <article class="p" style="--bg:{bg};--tint:{tint};--ink:{ink}">
        <span class="kind">{escape(kind)}</span>
        <span class="badge">{_badge(event, today, start, end)}</span>
        {'<span class="spark" title="can be shiny"></span>' if pokemon.get("shiny") else ''}
        {hero}
        <div class="foot">
          <h3>{escape(event.name)}</h3>
          {f'<p class="sub">{escape(pokemon["name"])}</p>' if pokemon.get("name") else ''}
          {f'<div class="weak">{weak}</div>' if weak else ''}
          {bonuses}{figure}
          {f'<p class="links">{links}</p>' if links else ''}
        </div>
      </article>'''


def _badge(event: Event, today: date, start: datetime, end: datetime) -> str:
    """What to put in the corner: a time for something happening that day, a
    countdown for something already running."""
    if start.date() == end.date():
        return f"{_hour(start)}" if event.is_local_time else f"{start:%H:%M} UTC"
    left = (end.date() - today).days
    if left <= 0:
        return "last day"
    return f"{left} day{'s' if left != 1 else ''}"


def _hour(moment: datetime) -> str:
    hour = moment.strftime("%-I%p").lower()
    return hour if moment.minute == 0 else moment.strftime("%-I.%M%p").lower()


def _naive(moment: datetime) -> datetime:
    """Drop the timezone for ordering and grouping only. What each event says
    about its own time is decided in _badge."""
    return moment.replace(tzinfo=None) if moment.tzinfo else moment


_STYLE = """
:root{--paper:#f6f3ec;--card:#fff;--ink:#2b2438;--muted:#7b7389;--edge:#e7e1d6;--sun:#ffb020}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:400 16px/1.5 Lato,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:62rem;margin:0 auto;padding:2rem 1rem 5rem}
.top h1{font:600 2.3rem/1 Fredoka,system-ui,sans-serif;margin:0}
.top p{margin:.3rem 0 1.3rem;color:var(--muted)}
.sub-link{color:var(--ink)}

.ribbons{display:flex;flex-direction:column;gap:.4rem;margin-bottom:1.5rem}
.ribbon{position:relative;display:flex;align-items:center;gap:.7rem;background:var(--rc);
  color:#fff;padding:.6rem 1rem;border-radius:5px;box-shadow:0 5px 14px -10px rgba(40,30,60,.9)}
.ribbon b{font:600 1rem/1 Fredoka,system-ui,sans-serif}
.ribbon small{opacity:.85;font-size:.82rem}
.ribbon .days{margin-left:auto;font:900 .82rem/1 Lato,sans-serif;font-variant-numeric:tabular-nums;
  background:rgba(255,255,255,.22);padding:.3rem .5rem;border-radius:4px;white-space:nowrap}

.day{background:var(--card);border-radius:24px;margin-bottom:1.25rem;overflow:hidden;
  box-shadow:0 12px 34px -22px rgba(40,30,60,.6);display:grid;grid-template-columns:5.4rem 1fr}
.spine{padding:1.15rem .4rem;text-align:center;border-right:1px dashed var(--edge)}
.spine .wd{font:500 .8rem/1 Fredoka,system-ui,sans-serif;color:var(--muted)}
.spine .n{font:700 2.4rem/1 Fredoka,system-ui,sans-serif;font-variant-numeric:tabular-nums;margin:.08rem 0}
.spine .mo{font-size:.76rem;color:var(--muted)}
.day.now .spine{background:var(--sun)}
.day.now .spine .wd,.day.now .spine .mo{color:#7a4b00}
.deck{padding:.95rem;display:grid;gap:.8rem;grid-template-columns:repeat(auto-fill,minmax(12.5rem,1fr))}

.p{position:relative;display:flex;flex-direction:column;overflow:hidden;min-height:17.5rem;
  padding:.6rem;border:5px solid var(--card);outline:1px solid var(--edge);border-radius:16px;
  background:radial-gradient(circle at 16% 10%,var(--tint) 0 24%,transparent 24.5%),
             radial-gradient(circle at 88% 82%,var(--tint) 0 18%,transparent 18.5%),var(--bg);
  box-shadow:0 7px 18px -13px rgba(40,30,60,.75);color:var(--ink)}
.kind{position:relative;z-index:2;font:700 .64rem/1 Lato,sans-serif;letter-spacing:.05em;opacity:.7}
.badge{position:absolute;top:.55rem;right:.55rem;z-index:2;background:var(--ink);color:var(--bg);
  font:900 .72rem/1 Lato,sans-serif;padding:.32rem .5rem;border-radius:6px;font-variant-numeric:tabular-nums}
.hero{width:112%;margin:-.4rem 0 -.6rem -6%;height:10.5rem;object-fit:contain;
  filter:drop-shadow(0 8px 7px rgba(0,0,0,.24))}
.hero.ball{width:6.2rem;height:6.2rem;margin:.6rem auto 0;border:3px solid var(--ink);
  border-radius:50%;opacity:.18;
  background:radial-gradient(circle at 50% 42%,var(--ink) 0 14%,transparent 14.5%),
    linear-gradient(180deg,var(--ink) 0 47%,var(--card) 47% 53%,transparent 53%)}
.foot{margin-top:auto;position:relative;z-index:2}
.p h3{font:600 1.02rem/1.15 Fredoka,system-ui,sans-serif;margin:0}
.sub{margin:.15rem 0 0;font-size:.8rem;opacity:.75}
.weak{display:flex;flex-wrap:wrap;gap:.28rem;margin-top:.45rem}
.tp{width:22px;height:22px;border-radius:50%;background:var(--c);color:#fff;flex:none;
  display:grid;place-items:center;box-shadow:0 1px 2px rgba(0,0,0,.25)}
.tp svg{width:13px;height:13px;display:block}
.bon{display:inline-flex;align-items:center;gap:.22rem;font-size:.7rem;background:var(--card);
  border-radius:999px;padding:.16rem .45rem .16rem .18rem;margin:.35rem .2rem 0 0}
.bon img{width:17px;height:17px}
.spark{position:absolute;left:.5rem;top:1.9rem;z-index:2;width:17px;height:17px;background:var(--sun);
  clip-path:polygon(50% 0,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0 50%,39% 39%)}
.ig{margin-top:.4rem}
.ig > summary{cursor:pointer;font-size:.72rem;opacity:.8;list-style:none}
.ig > summary::-webkit-details-marker{display:none}
.ig > summary::before{content:"\25B8 "}
.ig[open] > summary::before{content:"\25BE "}
.ig img{display:block;width:100%;margin:.4rem 0 .1rem;border-radius:8px}
.credit{font-size:.66rem;opacity:.6}
.links{margin:.4rem 0 0;display:flex;gap:.6rem;font-size:.72rem}
.links a{color:var(--ink);opacity:.75}
a:focus-visible,summary:focus-visible{outline:2px solid var(--ink);outline-offset:3px}
footer{margin-top:2.5rem;color:var(--muted);font-size:.82rem}
footer a{color:var(--muted)}
@media (prefers-reduced-motion:no-preference){
  .p{transition:transform .16s ease}
  .p:hover{transform:translateY(-3px) rotate(-.6deg)}
}
@media (max-width:560px){
  .day{grid-template-columns:4.2rem 1fr}
  .deck{grid-template-columns:repeat(auto-fill,minmax(10rem,1fr));padding:.7rem}
  .hero{height:8.5rem}
  .spine .n{font-size:2rem}
}
"""


_PAGE = """<title>Pokémon GO — what's on</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Lato:wght@400;700;900&display=swap">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{style}</style>
<div class="wrap">
  <div class="top">
    <h1>What's on</h1>
    <p>{today} — <a class="sub-link" href="{calendar_url}">subscribe to this as a calendar</a></p>
  </div>
  <div class="ribbons">
{ribbons}
  </div>
{days}
  <footer>Times are your own local time unless a card says UTC.
    Event data from <a href="https://leekduck.com">Leek Duck</a>.
    Pokémon detail from <a href="https://pokeapi.co">PokéAPI</a>.
    Infographics by G47IX.</footer>
</div>
"""
