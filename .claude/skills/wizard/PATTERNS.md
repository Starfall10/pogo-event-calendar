# Common Patterns & Anti-Patterns

Quick reference for the wizard skill, written for this project's shapes.

## Idempotency Patterns

The job runs hourly and re-processes. Everything must be safe to repeat.

### Stable Identifiers

```
# WRONG: a new identifier every rebuild
uid = uuid4()
uid = f"pogo-{datetime.now().isoformat()}"
uid = hashlib.md5(description.encode()).hexdigest()   # changes when wording does

# CORRECT: derived from the event's own identity
uid = f"{event.event_id}@pogo-event-calendar"
```

An unstable `UID` means the calendar gains a second copy of the event on every
rebuild. Subscribed calendars are read-only, so the duplicates cannot be deleted
by hand — only regenerated away.

### Revisions, Not New Events

```
# CORRECT: content changed, so the same event is republished as a revision
if hash_of(new_content) != stored.content_hash:
    stored.revision += 1        # becomes SEQUENCE in the ICS output
    stored.content = new_content
```

`SEQUENCE` tells a calendar application "this is a newer version of the event
you already have". Bumping it when nothing changed is harmless noise; failing to
bump it when something did means clients may keep the old version.

### Cursor Advancement

```
# WRONG: the cursor moves past a failure, which is then unreachable forever
for msg in messages:
    try: process(msg)
    except Exception: log_error(msg)
    cursor = msg.id

# CORRECT: only past success
for msg in messages:
    try:
        process(msg)
    except Exception:
        log_error(msg)
        break                   # cursor stays; next run retries this message
    cursor = msg.id
```

Whichever policy is chosen — stop at the first failure, or skip and record it
for retry — write it down. An accident of control flow is not a policy.

### Newest-First Results

```
# WRONG: Discord returns newest-first, so the cursor ends up at the OLDEST id
messages = get_messages(after=cursor)
for msg in messages: ...

# CORRECT
messages = reversed(get_messages(after=cursor))
```

## Time Patterns

### Floating vs Fixed

```
# The rule, in one place, applied once:
if raw.endswith("Z"):
    start = datetime.fromisoformat(raw.replace("Z", "+00:00"))   # aware = fixed UTC
    is_local_time = False
else:
    start = datetime.fromisoformat(raw)                          # naive = floating
    is_local_time = True
```

```
# WRONG: every one of these attaches or assumes a zone
dt.astimezone()
dt.replace(tzinfo=ZoneInfo("Europe/London"))
datetime.now()                      # local zone, silently
datetime.fromtimestamp(ts)          # local zone, silently
```

### Assert on the Output, Not the Object

```
# WEAK: passes even when the builder attaches a zone downstream
assert event.start == datetime(2026, 9, 19, 14, 0)

# STRONG: asserts what the calendar file actually says
assert "DTSTART:20260919T140000\r\n" in ics_text          # floating
assert "DTSTART:20260801T100000Z\r\n" in ics_text          # fixed
assert "TZID" not in ics_text                              # no named zone anywhere
```

## Test Patterns

### Mutation-Resistant Assertions

```
# WEAK: checks that something happened
assert events

# STRONG: checks what would catch a mutation
assert len(events) == 41
assert events[0].event_id == "community-day-september-2026"
assert events[0].is_local_time is True
assert events[0].confidence == "high"
assert sum(1 for e in events if e.confidence == "low") == 3
```

### Boundary Testing

```
# If the matcher accepts similarity >= 0.6, test:
score_of(0.59)   # just below — must not match
score_of(0.60)   # the boundary itself — must match
score_of(0.61)   # just above

# If candidates are filtered to within one day, test:
offset_days(-2)  # outside
offset_days(-1)  # boundary
offset_days(0)
offset_days(+1)  # boundary
offset_days(+2)  # outside
```

### Fixture Assertions That Survive a Model Change

```
# WRONG: breaks the next time the vision model rewords anything
assert result.bonuses[0] == "Up to 5 additional daily Raid Passes from Gyms"

# CORRECT: assert on structure and the facts that matter
assert result.name == "Mega Staraptor Raid Day"
assert result.start_date == "19 Sep"
assert result.start_time == "14:00"
assert len(result.bonuses) == 3
assert any("Remote Raid" in b for b in result.bonuses)
```

## Implementation Patterns

### Constants Over Magic Values

```
# WRONG: a decision nobody can find
if SequenceMatcher(None, a, b).ratio() >= 0.6:

# CORRECT: a decision with a name and a home in config.py
if SequenceMatcher(None, a, b).ratio() >= NAME_SIMILARITY_THRESHOLD:
```

The same applies to the feed URL, the model name, the poll limit, the date
window, and every path.

### Per-Item Failure Isolation

```
# WRONG: one odd image ends the run and nothing rebuilds
for msg in messages:
    event = extract(msg)
    save(event)

# CORRECT: the failure is contained, recorded, and the rest still lands
for msg in messages:
    try:
        save(extract(msg))
    except Exception as exc:
        log.warning("extraction failed for %s: %s", msg.id, exc)
        failures.append(msg.id)
        continue
build_calendar()    # runs regardless
```

### Fail Loudly When Nothing Was Found

```
# WRONG: silently produces an empty calendar for weeks
image_url = find_image(msg)     # returns None, nobody notices

# CORRECT
image_url = find_image(msg)
if image_url is None:
    log.error("no image in message %s: %d attachments, %d embeds",
              msg.id, len(msg.attachments), len(msg.embeds))
```

Nobody reports a bug on this system. A quiet nothing is the normal failure.

### Duplication Over the Wrong Abstraction

```
# When fixing something in one place, check whether the pattern exists elsewhere:
grep -rn "the_pattern" src/

# Default to duplicating the fix. Only extract a shared abstraction when ALL of:
#   1. The same logic appears three or more times
#   2. The caller contexts are genuinely similar, not superficially alike
#   3. You were asked to extract, OR the duplication is exact
#
# The wrong abstraction is more expensive than duplication.
```

## Verification Commands

```bash
# Confirm a function exists before calling it
grep -rn "def function_name" src/

# Find all usages of a pattern
grep -rn "pattern" src/

# Check for an existing constant before hard-coding
grep -rn "CONSTANT_NAME" src/

# The two greps that must return nothing before any commit
grep -rn "cdn.discordapp.com\|media.discordapp.net" src/ state/ docs/pogo.ics
git diff --staged | grep -iE "token|api[_-]?key|secret"

# What the calendar actually contains
grep -c "^BEGIN:VEVENT" docs/pogo.ics
grep "^DTSTART" docs/pogo.ics | sort | uniq -c
grep "TZID" docs/pogo.ics            # must return nothing

# Review what you are about to commit
git diff --staged
```

## Pre-Implementation Verification

Before writing any code, answer:

1. What runs this, and how often?
2. What does it do the second time it sees the same input?
3. What other code reads the data it writes?
4. What are the edge cases — missing, empty, null, malformed, duplicated,
   spanning midnight, crossing a year boundary?
5. What must still be true after it runs?
6. How would a test show that it is?
7. Does this cost money or hit somebody else's API every time it runs?

If you cannot answer these, you are not ready to write code.
