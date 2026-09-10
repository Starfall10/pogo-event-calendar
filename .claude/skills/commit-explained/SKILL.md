---
name: commit-explained
description: Write a standalone markdown document explaining every change in a landed or staged commit on pogo-event-calendar to someone who does not write software — building from what the change was for, through each part in the order they depended on each other, to what is absent now and what restores it. Use when the user asks to explain a commit, wants a change-by-change breakdown, asks "what did we actually change", wants a document a non-engineer can read, or before committing a large change. One document per commit, named `<milestone-or-topic>-explained.md` in `.claude/plans/`.
---

# Explain a commit, change by change

Produce one markdown file that lets someone who does not write software
understand everything a commit did and why, without reading the code, the diff,
or the conversation that produced it.

This is not a summary and not release notes. A summary tells them what happened.
This tells them **why each change had to happen, in an order where each one
makes sense only because of the one before it.** If the reader could have got
the same understanding from `git log`, the document has failed.

Reserve it for changes worth the effort — a whole milestone landing, a rewrite
of how matching works, a change to the `Event` model. A three-line fix does not
need one.

## Calibration

The reader knows their **own subject** better than you do: Pokémon GO, the
events, the infographics, how they use their calendar. Never explain that back
to them.

The reader does **not** owe you: dataclass, schema, fixture, mock, dependency,
import, module, environment variable, container, CI, cron, or what "collection"
means in a test run. Each is either avoided or introduced properly the first
time it appears.

The reader is **not stupid**. They are reading because they want to know what
happened to their system, and probably because they will have to make a decision
about it later.

**"Explain it to a five year old" means assume less than you think, not write
for a child.** The register stays adult; the assumed knowledge goes to zero.

**Length is not the enemy; skipped steps are.** What must never happen is a
sentence that only makes sense if you already knew the thing it is explaining.

## Where the file goes

`.claude/plans/<milestone-or-topic>-explained.md`. One document per commit. Link
it from `plan-of-action.md` so it is findable. The folder is flat and has no
index. Nothing in `.claude/` is committed.

## The document opens with the shortest true version

Before section 1, write **one paragraph the reader could repeat to someone
else**: what this commit did, in their own vocabulary, with no file names and no
jargon. Then a second short paragraph: why it was done.

Someone who reads only those two paragraphs should come away with something
correct, if incomplete. Everything after them adds detail; nothing after them
contradicts them.

## The order is the explanation

Do not walk the file list. Do not group by folder. Do not follow the diff.

**Find the sequence the thing actually performs**, step by step, with a person
or a machine doing something at each step. Then explain the parts in the order
they depend on each other, and say at each section why it follows the previous
one.

For this project the natural sequence is nearly always the pipeline, and the
document should follow it:

1. **What happens, end to end.** A numbered sequence — somebody posts an image
   to a channel; a scheduled job asks Discord for anything new; the image is read;
   a public feed is fetched; the two are matched; a calendar file is written; a
   phone downloads it. A table with two columns: what happens, and which part of
   the code does it. **Every later section refers back to a numbered step
   here.** Without it the reader has nowhere to put anything.
2. **The record everything is written into** — the `Event` model — because every
   later section either fills it or reads it.
3. **Each stage in pipeline order**, saying why it follows: the poller finds
   messages, so the extractor has something to read; the extractor produces
   dates that cannot be trusted, so the reconciler exists; the reconciler
   produces trustworthy events, so the builder can write them out.
4. **The thing that runs it all on a schedule**, last, because automating a
   pipeline only makes sense once the pipeline is right.

**If you cannot say why a section follows the one before it, the order is
wrong.** Rearrange until you can.

## Depth floor

A document that groups five files into one paragraph has failed, however well
written. The floor, per section:

- **Every file gets its own row and its own sentence.** Not "the extraction was
  added" — each file, what it does, what happened to it.
- **Every function whose behaviour is not obvious gets its behaviour
  recorded**, in prose. If the reader would have to read the code to understand
  why something exists, that is exactly the paragraph that must be here.
- **Every non-obvious decision inside a file** gets a line. A threshold that was
  chosen over another, a check that looked redundant and was not, an ordering
  that mattered.
- **Every number that was measured** appears: events in the feed, events
  matched, events left unverified, lines changed, tests added, cost per run.

If a section is shorter than the list of files it covers, it is too short.

## What every section contains

- **A table of the files touched**, with the change stated in a phrase and the
  real line count. `+184 lines` is information; "updated" is not.
- **Plain-language explanation of what that part does**, or did before.
- **Why it changed**, sourced. If the build plan decided it, quote the line and
  link it. If it followed from an earlier section, say which.
- **Anything found while doing it that nobody planned.** These are the most
  valuable paragraphs in the document, because they exist nowhere else.

## Sections that must exist at the end

**What the change cannot prove.** Specific to this project and not optional. The
tests run against saved fixtures with no network; the calendar the owner
actually sees is produced hours later by a job on somebody else's machine and
read by an application neither of you controls. State plainly which claims in
the document are backed by a check that ran, and which are backed by reasoning
alone. "The file we generate contains no timezone marker" is checked. "It shows
at 2pm on your phone" is not, until they look.

**What is absent now, and until when.** Every capability the commit defers or
removes, each with the milestone that restores it. An absence a reader discovers
themselves reads as a defect; an absence they were told about reads as a
decision.

**Every file, and where it is explained.** A table mapping each changed file to
its section. Then **verify it programmatically** — compare against
`git status --short` or `git show --stat` and confirm nothing is unmentioned. A
file the document silently omits is the one the reader will later find and
distrust the whole document over.

**Verification performed.** What was run, what the result was, and what is still
outstanding — including anything only the owner can check on their own devices.

**A glossary of every term the document had to introduce.** One line each, in
the reader's language, in the order they first appear. Likely entries for this
project: floating time, `DTSTART`, `UID`, `SEQUENCE`, crosspost, webhook
message, cursor, fixture, deep link, feed. If a term appears in the document and
not in the glossary, either define it where it appears or add it here.

## Rules that keep it honest

**Do not lie to simplify.** If the simple version is wrong, give it and correct
it in the next sentence.

**Never write "simply", "just", "obviously", "of course", or "it turns out".**

**Numbers are load-bearing. Keep them.** Without them the document reads as
impression rather than fact, and impressions do not survive a disagreement.

**Say what you do not know.** "This was not verified, and here is what would
verify it" is a complete entry. Rounding an unrun check up to a result is the
worst thing this skill can do.

**Own mistakes plainly, once.** A document that reads as flawless is not trusted
by anyone who was there.

**Explain what a mechanism is before explaining what happened to it.** If a
section needs the reader to know what a webhook message is, or why an image URL
expires, introduce it in that section rather than assuming an earlier one
covered it.

## Prose register: plain, but literal

Anything committed to this repository is written in literal referential prose,
and `.claude/plans/` follows the same rules. That is not in tension with writing
for a beginner — the two are separate axes:

- **Keep:** short sentences, one idea each, every term introduced, concrete
  actors performing concrete actions, worked examples over definitions.
- **Drop:** metaphor, spatial framing ("sits within", "layer", "surface"),
  temporal drama ("when X lands"), anthropomorphism, and any phrase that could
  appear in marketing copy.

Use an analogy only where it is genuinely load-bearing, mark it as one, and
abandon it the moment it stops being accurate.

Concrete nouns do the work that metaphor would otherwise do: file, function,
message, image, feed, event, property, job, calendar.

## What this document is not

It is **not a specification and must never be cited as one.** It explains a
change to a person; it does not define behaviour. When it disagrees with
`docs/PogoCalBuildPlan.md` or `CLAUDE.md`, those win, and the explanation is
wrong and should be corrected. Say this in the document itself if there is any
chance of confusion.

## Before you finish

- [ ] Every changed file appears, verified against `git status` / `git show --stat`.
- [ ] Every section states why it follows the previous one.
- [ ] Every claim about a decision links to the document that made it.
- [ ] Every number is real and was measured, not estimated.
- [ ] Claims backed by a check are separated from claims backed by reasoning.
- [ ] Absences each name the milestone that restores them.
- [ ] No sentence assumes a term the document has not introduced.
- [ ] A two-paragraph plain version opens the document.
- [ ] Every file has its own row and its own sentence — none grouped away.
- [ ] A glossary covers every term the document introduced.
- [ ] Linked from `plan-of-action.md`.
