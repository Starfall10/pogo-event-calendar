---
name: update-plans
description: Bring .claude/plans/ and the build plan back in line with what has actually happened on pogo-event-calendar — record what a completed milestone really did, file a decision where it was made, correct a design assumption that met reality badly, and keep plan-of-action.md accurate as the live document. Use when the user asks to update, tidy or file the plans folder, after a milestone lands, when a decision is taken, or when a plan document has drifted from the work.
---

# Update the plans

There are two kinds of document here and they are not maintained the same way.

**`docs/PogoCalBuildPlan.md` is committed and is the design.** It was written
before any code existed. It records what was decided and why, and it is the
thing a future reader is pointed at. Change it when reality proves part of it
wrong — not to reflect progress.

**`.claude/plans/` is local working memory.** It answers three things git
cannot: what was decided, what was decided *against*, and what the work turned
out to be once it was attempted. Keep it out of commits.

Either is only worth keeping if it is accurate. A document describing what
somebody intended a fortnight ago is worse than none, because it is read as
current.

---

## The shape of the plans folder

Keep it flat. No index, no numbering.

| Document | Its job |
| --- | --- |
| `plan-of-action.md` | **The live document.** The milestone in flight, its steps, and a status block under anything completed. |
| `PROGRESS.md` | The running log for the task currently in hand. See the `progress-log` skill. |
| `<topic>.md` | A decision or an explanation that needed its own document. |
| `finished/` | Milestones that are done and their working documents. |

**When a milestone completes**, move anything written only for it into
`finished/` and point `plan-of-action.md` at the next one. A live document
describing finished work is read as current and misleads.

---

## When a milestone completes

Add a status block to `plan-of-action.md`, **while it is accurate**. It states
five things:

1. **What was done**, per file, in a table
2. **Where it lives** — branch name, and whether it is committed
3. **What the acceptance check returned** — the actual command and its output,
   or, where the check was the owner looking at their calendar, what they
   reported and on which device
4. **What is still outstanding** in that milestone
5. **Anything noticed and deliberately not acted on**

That fifth item is the one people skip and the one that pays. A gap left open on
purpose, recorded as such, is a decision. The same gap unrecorded is a bug
somebody finds in three weeks.

Mark it in the heading — `🟢 M1 DONE — <date>, not yet committed` — so a cold
reader sees the state before reading the detail.

**An acceptance check that only the owner can run is not passed until they say
so.** Record who ran it. "M0 acceptance: owner confirmed both events visible on
Mac and iPhone, 8 Sep" is a fact. "M0 acceptance: passed" is not.

---

## When a decision is taken

**Record it in the document that raised the question**, not in a separate log,
so the reasoning and the answer sit together and neither can be read without the
other.

Each recorded decision carries: the date, what was chosen, and — where it
matters — **what it was chosen over and why**. A decision without its
alternatives cannot be revisited intelligently.

The decisions this project actually generates are mostly about matching and
time. Record the number, not the intent: the similarity threshold that was
settled on, the date window used to filter candidates, what happens when two
Leek Duck records match one post, which events get a `⚠️`, how `event_id` is
derived. Each of those is a knob somebody will want to turn later, and a
threshold with no recorded reasoning gets turned by guess.

Then update the consequences — the open-decisions section of
`plan-of-action.md`, and the build plan if the decision contradicts it.

---

## When the build plan meets reality

The build plan makes claims that were true when written and may not be now: the
ScrapedDuck field names, the trailing-`Z` convention, where a crossposted image
turns up, what `icalendar` will let you set, how Apple Calendar treats a
property.

When one of them turns out to be wrong:

- **Correct it in place**, in the build plan, and say so in one sentence — "the
  feed now carries X rather than Y; checked 8 Sep".
- **Keep the original reasoning.** Do not delete the paragraph that explained
  why the decision was made because the fact underneath it changed. The method
  is usually worth more than the conclusion.
- **Say plainly if you were wrong.** A document that hides its errors is one
  nobody can calibrate against.
- **Update §8, the gotchas list.** That section is the project's accumulated
  scar tissue and it is the highest-value part of the document. Anything that
  cost an hour belongs in it, in one sentence, with the symptom first — the
  symptom is what a future reader will search for.

Do not rewrite history to look prescient. "I read this as X; the feed says Y;
here is the corrected version" is worth more than a clean document that quietly
changed its mind.

---

## Prose rules

`.claude/plans/` is written **assuming no prior knowledge** — plain language,
analogies where they are load-bearing, real numbers, no unexplained vocabulary.
See `.claude/skills/5yro/SKILL.md`.

That is a deliberate local choice and **it does not travel.** Anything committed
— `README.md`, `docs/`, docstrings, comments, commit messages — is written in
literal referential prose. Read the existing README before adding to it; it has
a register, and it is not this one. When a plan document produces something that
belongs in the repository, translate it first.

---

## What not to do

- **Do not create an index or a numbering scheme.** A handful of documents does
  not need one. `finished/` is the only subfolder.
- **Do not update the build plan to record progress.** It is the design.
  Progress lives in `plan-of-action.md`.
- **Do not delete a superseded decision.** Mark it and keep it.
- **Do not update the folder speculatively.** Record what happened, not what is
  about to.
