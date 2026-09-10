---
name: work-the-plan
description: Execute the pogo-event-calendar build plan one milestone at a time and one file at a time, stopping after every single file to explain the change in plain language and wait for the owner's approval before touching the next one. Use when the user says "start M0/M1/M2", "next milestone", "continue the plan", "next file", or asks to begin any step in docs/PogoCalBuildPlan.md §6. Also use for any repeat of this shape of work — a sweep of edits across several files where the owner wants to see and approve each one.
---

# Work the plan, one file at a time

The plan is [docs/PogoCalBuildPlan.md](../../../docs/PogoCalBuildPlan.md).
Read it before starting anything, and read the milestone you are about to work
on in full — including its acceptance check, which is the definition of done.

This skill is about **rhythm**, not content. The plan says what to build. This
says how to go about it so the owner stays in control and understands every edit
as it lands.

---

## The one rule everything else serves

> ## Change one file. Stop. Explain. Wait to be told to continue.

Not two files. Not "the three small ones together because they're similar". Not
"I'll do the rest and show you at the end".

**One file, then a full stop.**

The owner is learning this codebase — and, in places, Python — through these
explanations. Batching edits takes that away and replaces it with a diff they
have to reconstruct backwards. It also removes the moment where they can say
"actually, leave that one".

### What "stop" means

End your turn. Do not call another edit tool. Do not start reading the next
file "to be ready". The turn ends with the explanation and a clear statement of
what is left.

### What counts as approval

An explicit go-ahead: "A", "approved", "yes", "next", "continue". Anything else —
a question, a correction, a change of mind, silence about the substance — is not
approval. Answer what was asked and stay where you are.

---

## Milestones are the outer loop

The plan's milestones exist in dependency order and each one ends with something
runnable. **Do not skip ahead and do not work two at once.**

- **M0 before M1**, because there is no point generating real events until the
  delivery pipe to Apple Calendar is proven.
- **M1 before M2**, because Leek Duck alone already gives a useful calendar, and
  every later stage is enrichment on top of a thing that works.
- **M2 before M3**, because you need real message JSON on disk before you can
  test extraction against it without hammering an API.
- **M3 before M4**, because reconcile has nothing to reconcile until both
  sources produce Events.
- **M4 before M5**, because automating a pipeline that produces wrong output
  just produces wrong output on a schedule.

**A milestone is not done until its acceptance check has been run and shown.**
The plan writes one for each. Several of them are the owner looking at their own
calendar — those are theirs to run, so stop and ask, and do not mark the
milestone done on your own say-so.

Within a milestone, prefer the smallest and clearest file first. It builds a
shared vocabulary before the hard file arrives.

---

## Before you touch a file

**Read the surrounding context first, and show it.** Not just the matching
lines — enough of the function, class, or module that both you and the owner can
see what the edit sits inside.

**Verify before you reference.** Never call a function, import a name, or assume
a field exists because it would be reasonable. `grep` for it and say what you
found. The Discord message shape, the ScrapedDuck field names and the
`icalendar` API are all things to check rather than remember — remembered API
shapes are the top source of wasted evenings here.

**Work out the shape of the edit before making it:**

| Shape | What to do |
|---|---|
| A new module the plan names | Write it whole, smallest working version, then stop |
| A function inside an existing module | Show the function as it stands, then the replacement |
| A change to the `Event` model | Stop first. This is the spine — every stage reads it, and a field added casually is a field four modules now half-support |
| A change to timezone handling | It lives in exactly one place. If your edit adds a second place, the edit is wrong |
| A constant or config value | It goes in `config.py`, not inline |

**Never invent a replacement for something you remove.** If taking out a line
leaves a real need with nothing behind it, say so plainly and let the owner
decide.

---

## Making the edit

**Use a targeted replacement with a uniqueness assertion.** Match on an exact
string and confirm it occurs exactly once before writing. If it is not unique,
widen the match until it is. Never `replace_all` a short string across a file,
and never edit by line number alone — line numbers move.

**Keep the four stages separate.** `poll`, `extract`, `reconcile`, `build`. The
whole point of the split is that the ICS builder can be run against saved
fixtures with no network, no Discord and no API key. An edit that makes one
stage need another is a design change, not a tidy-up — raise it, do not make it.

**Every network call gets a timeout and a retry. Every per-message failure gets
caught, logged and skipped.** One bad post must never wedge the run, and it must
never advance the cursor past itself.

---

## The explanation

**Always use the `5yro` skill's four layers. This is not optional and does not
need asking for.**

1. **One sentence** they could repeat to someone else
2. **The story** — what the thing does, and what goes wrong, with people doing
   things
3. **The real names** — files, functions, line numbers, attached once each
4. **What someone would notice** — a visible consequence, or an honest statement
   that it is invisible today and when it stops being

On top of that, every explanation in this rhythm needs:

**What this file is and what it does — before the diff.** Do not open with the
change. Open with the thing being changed. Two or three short paragraphs
answering, in this order:

- **What is this file for?** In one sentence somebody could repeat.
- **Where does it sit?** Which stage, what calls it, what it calls, what it
  would break.
- **What was it doing wrong, or not doing at all?**

Only then the diff. This applies on **every** pass, including the third file in
a row in the same directory — a file seen yesterday is not a file the owner
remembers.

**Show the thing, do not describe it. Run it and paste the real output.**
"`leekduck.fetch()` returns a list of Events" leaves the reader with nothing to
picture. This does:

> `leekduck.fetch()` returned **41 events**. The first three:
>
> ```
> [0]  community-day-september-2026     2026-09-20T14:00:00   floating
> [1]  raid-hour-mega-staraptor         2026-09-17T18:00:00   floating
> [2]  gofest-global-2026               2026-08-01T10:00:00Z  fixed (UTC)
> ```
>
> Note event [2] — the trailing `Z`. That is the one case in forty-one where the
> time is fixed rather than local, and it is what the timezone rule exists for.

Real values from the real feed, not invented ones. Real counts.

**Before and after, run both.** Do not assert that behaviour changed — show it.
For this project the highest-value before-and-after is usually the calendar file
itself:

> **Before:** the Staraptor event as the vision extraction had it
> ```
> SUMMARY:⚠️ Mega Staraptor Raid Day
> DTSTART:20260919T140000
> ```
> **After:** the same event once Leek Duck matched it
> ```
> SUMMARY:Mega Staraptor Raid Day
> DTSTART:20260919T140000
> SEQUENCE:1
> ```
> The times are identical, which is the point — the merge did not change them,
> it *confirmed* them, and the `⚠️` came off because they were confirmed.

Do this even when the answer is "nothing visible changes" — **especially** then.

**Say what the example does not cover.** "This proves the file we generate says
`DTSTART:20260919T140000` with no timezone. It cannot prove Apple Calendar reads
that as 2pm local — the only thing that proves that is looking at your phone."

**The diff, or its substance.**

**Why this shape of edit and not another.** That sentence is the whole point of
stopping.

**Anything you noticed and did not act on.** A gap, a claim you could not
verify, something odd nearby. Say it once, plainly, and let it go if the owner
says to.

**What is left.** A count and a list. "M1 has 3 files left: `leekduck.py`
(done), `models.py` (1 field to add), `cli.py` (the `build` subcommand)."

### Keep it plain

- Short paragraphs, one idea each
- Real numbers, always — "41 events, 3 unmatched", not "several"
- Never "simply", "just", "obviously", "of course", "as you can see"
- An analogy only if it is load-bearing, and dropped the moment it stops being
  true
- Do not lie to simplify. Give the simple version, then correct it in the next
  sentence if it is not quite right

---

## Finishing a milestone

**Run the acceptance check the plan names, and show the result.** If it is one
the owner must run — anything involving their calendar, their phone, or their
Mac's timezone — say exactly what they should look at and what a pass looks
like, then stop.

**Show the total.** `git diff --stat` for every file touched.

**Record it.** Add a status block to `.claude/plans/plan-of-action.md`: what was
done, on which branch, what the acceptance check returned, what is still
outstanding, and anything noticed-but-not-acted-on. Do this as the milestone
completes, while it is accurate.

**Do not commit unless asked.** Leave the branch dirty. The owner decides when
work becomes a commit.

**Never commit a secret.** `.env` holds a Discord bot token and an Anthropic API
key, and this repository is public by design. Check `git status` before every
commit you are asked to make.

---

## When something is wrong

**If the plan is wrong, say so and stop.** The plan is a record of decisions
taken before any code existed, and some of them will meet reality badly. If a
library does not behave as §7 says, or a milestone's acceptance check cannot be
met as written, explain what you found and wait.

**If you were wrong earlier, correct it in one sentence and continue.** No
performance of contrition. The owner needs the correct fact, not managed
feelings.
