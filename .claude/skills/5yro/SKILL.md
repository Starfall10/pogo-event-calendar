---
name: 5yro
description: Explain something in full, assuming the reader knows no engineering vocabulary at all — build it up in layers from a plain-language story to the real file and function names, then say why it matters and what breaks if it is wrong. Use when the user says "explain like I'm five", "5yro", "ELI5", "assume I know nothing", "in simple language", "I don't understand what you just did", or asks what a commit, defect, mechanism or decision actually was after work has landed. Also use unprompted when about to report a finding whose significance depends on machinery the user has not been shown.
---

# Explain it from zero

The instruction "as if to a five year old" does not mean *be childish*. It means
**assume no engineering vocabulary and no prior context, and do not skip a step
because it feels obvious to you.**

Get this calibration right or the output is patronising and useless:

- The reader knows their **own subject** better than you do — Pokémon GO, what a
  Community Day is, what the infographics contain, how they use their calendar.
  Never explain that back to them.
- The reader does **not** owe you knowledge of dataclasses, imports, fixtures,
  virtual environments, dependency pinning, CI, cron syntax, HTTP status codes,
  or what a test "collecting" means. Every one of those is a word to either
  avoid or introduce properly.
- The reader is **not stupid and is not in a hurry to be flattered**. They asked
  because an explanation failed, not because they want a gentler tone.

---

## The four layers

Build up. Do not open with the real answer and then soften it — open with the
smallest true thing and add detail until the real answer arrives on its own.

**Layer 1 — one sentence they could repeat to someone else.**
No names, no files, no jargon. If you cannot write this sentence, you do not yet
understand the thing well enough to explain it.

> "The calendar was telling everyone the event starts at 2pm in London, when
> what it should say is 2pm wherever you happen to be standing."

**Layer 2 — the story, with people doing things.**
Concrete actors performing concrete actions in a sequence. Somebody posts an
image. Something reads it. Something writes a file. A phone downloads that file
once a day. Avoid "the system" as the subject of every sentence — it hides who
is doing what.

Use an analogy **only if it is load-bearing**, and abandon it the moment it
stops being accurate. A wrong analogy is far more expensive than no analogy,
because the reader will reason from it later. When you drop one, say so.

**Layer 3 — attach the real names, once each.**
This is the layer most explanations skip, and it is the one that makes the
explanation useful the next day. Give the plain-language thing, then its real
name, in that order, in the same sentence:

> "…the line in the calendar file that says when the event begins — that is a
> property called `DTSTART`, one per event."

Now the reader can search for it, ask about it, and recognise it in a diff. Link
the file: [file.py:42](path/to/file.py#L42). One naming per concept. Do not
alternate between the plain word and the real name afterwards — pick one and
stay with it.

**Layer 4 — why it matters, in something the reader would notice.**
Not "this improves correctness". What would a person have *seen*? An event at
the wrong hour. A duplicate of every event. A calendar that stopped updating and
looked fine. A link that opens nothing. If you cannot name a visible
consequence, say honestly that the consequence is invisible today and explain
when it stops being invisible.

---

## Rules that keep it honest

**Do not lie to simplify.** If the simple version is wrong, give the simple
version and then correct it in the next sentence: *"That is roughly it. The one
place it is not quite true is…"* A simplification the reader later discovers was
false costs you the next ten explanations.

**Never write "simply", "just", "obviously", "of course", or "it turns out".**
Each one tells a reader who did not find it obvious that they should have.

**Say what you do not know.** "I do not know whether Apple Calendar honours that
property; here is how we would find out" is a complete and useful answer.
Rounding an open question up to a conclusion is the single worst thing this
skill can do, because the reader will act on it.

**Own the mistakes plainly, once.** If the explanation is about something that
went wrong and you caused it, say so in a sentence, in the same plain language,
and move on. Do not perform contrition — it makes the reader manage your
feelings instead of understanding the problem.

**Numbers are concrete; keep them.** "41 events in the feed", "3 unmatched",
"one vision call per post, about 2 pence a month", "the image URL dies after
about 24 hours". Real figures are load-bearing: without them the account reads
as impression rather than fact.

**End with the "so what".** One short paragraph: what this changes, what happens
next, or what is still open.

---

## Length and shape

Long is fine. Vague is not. The failure mode is not "too many words", it is
"words that assume the step they skipped".

- Short paragraphs. One idea each.
- Headings the reader can scan and return to.
- A worked example beats a definition every time.
- If it has more than about four moving parts, number them and keep the numbers
  stable for the rest of the explanation.

---

## A worked example, from this project

The rule: an event whose time has no timezone attached must stay that way all
the way to the calendar file.

**Layer 1.** "Most Pokémon GO events run at the same clock time everywhere on
Earth. The calendar has to say '2pm' without saying *whose* 2pm, or it will be
wrong for you the moment you get on a plane."

**Layer 2.** "Think about two different kinds of appointment. A dentist
appointment is at 3pm in one particular place — if you fly to New York, it is
still 3pm in London and you have missed it. A Pokémon GO Raid Day is the
opposite: it runs 2pm to 5pm in London *and* 2pm to 5pm in New York, at
different moments, for the people standing there. Calendar files can express
both, and they look almost identical. The difference is one letter."

**Layer 3.** "In the file, the start time is a line reading
`DTSTART:20260919T140000`. If a `Z` is added to the end — `20260919T140000Z` —
that means 2pm in Greenwich, and a phone in New York will show it as 10am. With
no `Z`, the phone shows 2pm wherever it is. The feed we take dates from uses the
same convention: a trailing `Z` means fixed, no `Z` means local. So the rule is
to pass the marker through untouched. In the code that is one flag on the event
record, `is_local_time` in [models.py](src/pogocal/models.py), set in exactly
one place — [leekduck.py](src/pogocal/leekduck.py) — and read in exactly one
place, [ics_build.py](src/pogocal/ics_build.py)."

**Layer 4.** "Nobody sees a crash. What they see is a Raid Day sitting at 3pm in
their calendar while the game runs it at 2pm, and they find out by missing it.
It also cannot be fixed by hand afterwards, because a subscribed calendar is
read-only — the only way to correct an event is to regenerate the whole file."

**So what.** "Keeping the flag in one place is the whole defence. If a second
place ever starts deciding this, the two will disagree eventually, and the
symptom will be one event an hour out with nothing in the logs."

---

## Where this output may and may not go

This explanation style is for **conversation with the owner**, and for
`.claude/plans/` — the planning documents here are written this way, with
analogies and no assumed vocabulary. That is a deliberate local choice and it
does not travel.

It does **not** go into anything committed. `README.md` and `docs/` are written
in literal referential prose — read them before adding to them — and the same
applies to docstrings, comments, commit messages and pull request bodies.

When an explanation produces something that belongs in the repository,
**translate it first**: the fact and its consequence go in, in plain referential
language, and the story stays in the conversation.
