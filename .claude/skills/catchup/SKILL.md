---
name: catchup
description: Get a fresh session up to speed on pogo-event-calendar before doing any work — establish where the branch actually is from git, read the build plan and plans folder in the right order, check the state files and the published calendar against them, load the standing rules, then report back and stop. Use at the start of a new session, after /clear or a compaction, when the user says "catch up", "get up to speed", "where are we", "what's the state", "which milestone are we on", or "carry on from last time".
---

# Catch up

**Read the repository first, then the documents, then check they agree.** The
build plan records intent; git and the files on disk record what happened.
Either can be stale, and the disagreement between them is the most useful thing
you will find in the first five minutes.

This project is milestone-driven (M0–M6 in the build plan). The first question
to answer is always **which milestone is actually finished**, and that is
answered by what runs, not by what a document says.

Do not edit anything until the read-back at the end has been confirmed.

---

## 1. Ground truth from git

Read-only.

```bash
git branch --show-current
git log --oneline -8
git status --short
```

- **A clean tree does not mean a good state.** It means nothing is uncommitted.
- **Uncommitted work is normal here.** Whole steps may have been left
  uncommitted on purpose for the owner to review. Read the plans before
  assuming a dirty tree is unfinished.
- **The hourly GitHub Action commits to this repo.** A commit you did not make,
  touching `docs/pogo.ics` and `state/`, is the job running — not someone else's
  work. Check the author before reading anything into it.

---

## 2. Ground truth from the files

Cheap, read-only, and it tells you more than the documents do:

```bash
ls src/pogocal/ 2>/dev/null || echo "no package yet — pre-M0"
ls state/events/ 2>/dev/null | wc -l          # extracted events on disk
cat state/cursor.json 2>/dev/null              # last processed message id
head -20 docs/pogo.ics 2>/dev/null             # is there a published calendar?
grep -c "^BEGIN:VEVENT" docs/pogo.ics 2>/dev/null   # how many events in it
ls tests/fixtures/ 2>/dev/null
```

Map what you find onto the milestones:

| What exists | Milestone reached |
| --- | --- |
| `docs/pogo.ics` with hand-written events, no `leekduck.py` | M0 |
| `leekduck.py` and real events in the calendar | M1 |
| `discord_src.py` and a `state/cursor.json` | M2 |
| `vision.py` and fixture expectations that pass | M3 |
| `reconcile.py`, merged events carrying both links | M4 |
| `.github/workflows/update.yml` and Action-authored commits | M5 |

Do not ask the owner which milestone they are on before doing this. Work it out,
then confirm it.

---

## 3. Read the written record, in this order

1. **`docs/PogoCalBuildPlan.md`** — the design and the milestone list. §1–§5 are
   the design, §6 is the work, §7–§10 are reference. Read §5 (architecture and
   the Event model) and the milestone you believe is in flight, in full.
2. **`CLAUDE.md`** — the standing rules, short. Read every line; they are all
   load-bearing and several are the difference between a working calendar and a
   silently wrong one.
3. **`README.md`** — what the thing is for and how it is subscribed to. Read if
   you have not seen it this session.
4. **`.claude/plans/plan-of-action.md`**, if it exists — the live document:
   what is being done now, with a status block under anything completed.
   Read the completed-step notes; they record what landed and what was
   deliberately not done.

**Decisions are recorded where they were made**, dated, in the document that
raised the question. Search the plans folder before concluding a decision was
never taken.

---

## 4. Reconcile — the step that catches a rotted record

| Check | If it disagrees |
| --- | --- |
| Does the milestone marked done in the plans folder match what actually runs? | The folder is ahead of the work, or the work was reverted. Say so before answering anything else. |
| Does `docs/pogo.ics` contain what the current code would produce? | The published calendar is stale, or was committed by hand. Establish which. |
| Does `state/cursor.json` point at a message the channel still has? | The cursor may have been seeded or reset. It changes what a poll will do. |
| Do the README's commands exist in `cli.py`? | The README describes the finished system, not necessarily the current one. |

Never resolve a disagreement silently. Quietly editing a plan to match the code
converts a decision into an accident.

---

## 5. Load the standing rules

Not derivable from the code. Skim rather than assume:

- **`.claude/skills/work-the-plan/SKILL.md`** — the working rhythm the owner
  expects: one file, stop, explain, wait for approval. **Read this before any
  change touching more than one file.**
- **`.claude/skills/progress-log/SKILL.md`** — the bulk-edit rule and the
  progress file.
- **`.claude/skills/5yro/SKILL.md`** — how the owner wants things explained.
- **`CLAUDE.md`** — one milestone at a time; four stages kept separate; Discord
  CDN URLs never written into calendar output; timezone handling in exactly one
  place; Leek Duck authoritative for dates, vision for everything else; every
  per-message failure caught and skipped; no secrets committed.

---

## 6. Know what the cheap checks do not cover

This project's real risks are not the ones a test suite catches:

- **A green `pytest` says nothing about the calendar being right.** The output
  that matters is what Apple Calendar shows on the owner's phone, and no test
  in this repo can see that.
- **The floating-time bug is invisible locally.** An event with a timezone
  wrongly attached looks perfect until the owner travels or shares the
  calendar. The only real check is changing the Mac's timezone and looking.
- **Vision extraction drifts between model versions.** Fixture tests assert on
  structured fields for that reason. A passing fixture test is evidence about
  those fields and nothing else.
- **Leek Duck is somebody else's feed.** Its shape can change without notice,
  and nothing here would fail loudly if it did — the calendar would just get
  thinner.
- **A wrong merge is worse than no merge.** An event silently taking another
  event's dates produces a confident, wrong calendar entry. The `⚠️` prefix on
  unverified events is the safety valve; treat its absence as a claim.
- **The Action can fail quietly for weeks.** Nobody reports a bug on a calendar
  that stopped updating — it just stops being right.

---

## 7. Report back, then stop

Six lines, nothing else. No plan, no proposal, no edits.

```
Branch:      <name>
Last landed: <hash> — <subject>   (say if it was the Action, not a person)
Tree:        clean | N modified, N untracked (name them)
Milestone:   <the milestone in flight, and what proves it>
Blocked on:  <what must be settled first, or "nothing">
Outstanding: <decisions still open, one clause each>
```

Then ask one question: whether that matches their understanding.

**Do not** run the test suite to find out where things are. **Do not** run any
git write operation. **Do not** run `pogocal poll` to see what happens — it
spends API credit, moves the cursor, and changes state you were asked to read.
Ask.
