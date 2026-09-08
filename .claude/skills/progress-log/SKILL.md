---
name: progress-log
description: Maintain a running progress file for pogo-event-calendar that tracks the current milestone — plan, per-step status, decisions, blockers, and next action — updating it as the work happens rather than at the end. Use whenever the user asks to track, log, or write progress to a file, asks for a progress/status/handoff file, or kicks off any multi-step task likely to span more than a few tool calls, a compaction, or more than one session. Also use when resuming work in a directory that already contains a progress file. Also defines this repo's bulk-edit rule: multi-file edits are made one file at a time and never scripted — read this before any change touching more than a few files.
---

# Progress log

Keep a plain-markdown record of the current task that stays accurate *while* the
work happens. The point is that someone — including a future session after
`/clear` or a compaction — can open one file and know exactly where things stand
without reading the transcript.

This project is worked in evenings, days apart. The transcript will not survive
between them. The file is the only thing that does.

## Bulk edits are made by hand

Multi-file edits are made one file at a time, reading each diff before moving to
the next. A script may **report** candidate lines. It may not edit them.

This is a rule about a specific failure, not a general preference. A regex or
AST pass over a set of files goes wrong in three ways, and each is worth
checking for explicitly:

1. **It cannot tell a pure effect from a binding.** Removing every statement
   that mentions a deleted name takes `do_thing(x)` and `x = build_thing()` with
   equal confidence. The second one leaves everything downstream of `x` broken.
2. **Diff-based restores over-correct.** Putting things back into files that had
   already been fixed by hand undoes correct work, and the second sweep is
   harder to reason about than the first.
3. **A bare word matches an unrelated concept.** In this repo, `event`, `start`,
   `end`, `link`, `image`, `source` and `name` all appear across genuinely
   different things — Discord messages, Leek Duck records, `Event` objects, ICS
   properties. A substitution anchored on any of them will hit code that was
   never in scope.

**Search every spelling, not the ones you expect.** A concept is written several
ways and a grep for three of them reports clean while the fourth survives.
Before claiming a sweep is complete, check the spaced, hyphenated, camel and
snake forms separately and show the count for each.

**Word-anchor every substitution and use the longest name available.**
`discord_message_id` is a substring of nothing. `id` is a substring of
everything.

**Run the suite every few files, never only at the end.** A sweep that runs the
tests once, at the end, cannot attribute a single failure to a cause.

**Searching for a deleted name finds where it is mentioned, not everywhere it is
served.** Machinery built for a removed concept is often named with an ordinary
word, so no search for the removed identifier reaches it. After the identifiers
are gone, search again for the **plain concept word** and read each hit. Most
will be the surviving concepts — that is the point: you are reading, not
substituting.

## Where the file lives

Default to `.claude/plans/PROGRESS.md`. If the user names a different path, use
theirs. If a progress file already exists, **read it first** and continue it —
never overwrite an existing log.

`.claude/plans/` is local working memory. Keep it out of commits; the build plan
and the README are the committed record.

## Start of task

Before doing any real work, write the file using this exact structure:

```markdown
# <short task name>

**Status:** in progress · **Milestone:** M<n> · **Started:** <timestamp> · **Updated:** <timestamp>

## Goal
<one or two sentences: what "done" means, in the user's terms — usually the
milestone's acceptance check, quoted>

## Plan
- [ ] 1. <step>
- [ ] 2. <step>
- [ ] 3. <step>

## Log

## Decisions

## Blockers

## Next
<the single next action>
```

Get timestamps from the shell rather than guessing:
`date -u +"%Y-%m-%d %H:%M UTC"`.

If the task is genuinely one step, skip the file and do the work — a progress
log for a two-minute change is noise.

## While working

Update the file **immediately after finishing each step, before starting the
next one**, and always before ending a turn. Waiting until the end defeats the
purpose: if the session dies mid-task, whatever was not written is lost.

Each update is small and surgical — edit the affected lines, do not rewrite the
file:

- Tick the plan item (`- [x]`) and mark the one in flight with `← current`.
- Append one line to `## Log`: `- HH:MM — <what changed, and where>`. Name the
  files touched. Keep it to a line.
- Refresh the `**Updated:**` timestamp.
- Rewrite `## Next` to the actual next action, phrased so a cold reader could
  pick it up.

The `## Log` section is append-only. Past entries stay as written even when a
later step undoes them — that something was tried and reverted is exactly what
makes a log worth reading.

Add to `## Decisions` whenever a choice closes off alternatives: what was
chosen, what it was chosen over, and why. One line each. In this project the
decisions worth recording are usually about matching, naming and time — a
similarity threshold, an `event_id` scheme, what to do with an event that
matched two Leek Duck records.

Add to `## Blockers` anything that stops progress — a failing test you cannot
fix, a missing token, an ambiguous requirement, a Discord permission that is not
set. Remove the entry when it clears, and note the resolution in the log.

If the plan changes, edit `## Plan` to match reality and log why. A plan that
quietly diverges from what is happening is worse than no plan.

## What not to log

Skip reads, greps, and exploratory commands that changed nothing. Log outcomes,
not keystrokes. If a log entry would be "looked at the config", it does not
belong.

**Never paste a token, key, or `.env` line into the log.** It is a file on a
public-repo working tree; treat it as if it could be committed by accident,
because one day it will be.

## End of task

Set `**Status:**` to `complete` (or `blocked` / `paused`, honestly — a task
marked complete that is not is the one failure mode that makes the whole file
untrustworthy). Write a final log line, clear `## Next` or replace it with
follow-up work worth doing later, and tell the user the file is there.

## Resuming

When a progress file exists at the start of a session, read it before touching
anything else and pick up from `## Next`. Do not re-plan from scratch, and do
not redo completed steps — check the log first to see whether they actually
landed, and check the working tree to see whether they survived.
