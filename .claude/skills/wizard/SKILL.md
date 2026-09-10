---
name: wizard
description: Disciplined development guidance for pogo-event-calendar — strict Red-Green-Refactor TDD, systematic planning, design heuristics, adversarial test coverage against this project's real failure modes (stale cursors, duplicate calendar entries, timezone leakage, one bad post wedging the run), and a self-review gate before anything is committed. Use when implementing a milestone, fixing a bug, or making multi-file changes that require careful planning and quality assurance.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, TodoWrite, WebFetch, AskUserQuestion
---

# Wizard Mode

## Visual Indicator

Prefix your first response with `## [WIZARD MODE]` to signal that architect-level
standards are active. Use `## [WIZARD MODE] Phase N: Name` at each phase
transition. Keep all checkpoint summaries to two or three sentences — state what
was found and what happens next.

## Core Behaviours

**Think Systemically, Not Locally**
- Do not ask "How do I fix this bug?" Ask "Why does this bug exist? What let it
  in? Where else does this pattern appear?"
- When you see a bug, map the stage it lives in: what data does it touch, what
  else reads that data, what runs before and after it, and what must stay true
  across all of them.

**Understand Before You Act**
- Before writing any code, verify you can answer: what data does this touch,
  what else touches it, what happens when it runs twice, and what must hold
  true afterwards.
- If you cannot answer those from your exploration, explore more.
- If you are coding immediately, you have not explored enough.

**Turn Adversarial Questions Into Tests**
For every behaviour you implement, write tests that answer:
- "What happens if this run repeats what the last run already did?"
- "What if this field is missing? Empty? Null? A different shape than expected?"
- "What assumptions am I making that could be wrong?"
- "If I were trying to break this, how would I?"
These are not questions to reflect on at commit time. They are test cases to
write during the RED phase.

---

## Phase 1: Understanding & Planning

**Goal**: Deeply understand before acting.

**Actions**:
1. Read `CLAUDE.md` in full.
2. Read the relevant part of `docs/PogoCalBuildPlan.md`: §5 for architecture and
   the `Event` model, §6 for the milestone, §7 for API shapes, §8 for the
   gotchas list. §8 is the accumulated scar tissue — read it before every
   non-trivial change, not once.
3. Read `.claude/plans/plan-of-action.md` if it exists, for what already landed.
4. Create a todo list with all phases.
5. Assess complexity:
   - **Simple**: one file, obvious fix, under 50 lines changed
   - **Medium**: 2–3 files, clear scope
   - **Complex**: 4+ files, touches the `Event` model or crosses stages

**For Medium/Complex work**: write it down before starting — the `progress-log`
skill, or a milestone section in `plan-of-action.md`. This project is worked in
evenings days apart; a plan held only in the transcript is a plan that is gone
by Thursday.

Use GitHub issues only if the repository already has them in use
(`gh issue list`). Do not introduce issue tracking to a solo hobby project that
is not using it.

**Checkpoint**: Brief summary of understanding and plan.

---

## Phase 2: Codebase Exploration

**Goal**: Understand existing patterns before making changes.

**Actions**:
1. Search for similar implementations already in the repo.
2. Verify every name you intend to use actually exists — functions, fields,
   constants, feed keys, library methods.
3. Confirm with grep or a real call, never memory:
   - Functions and methods exist as named
   - The ScrapedDuck feed still carries the fields §7 says it does
   - The Discord message JSON has the shape you expect (use a saved fixture
     under `state/messages/`, not a live call)
   - The `icalendar` API accepts what you are about to hand it
4. Identify patterns that must be followed.

**CRITICAL**: Never assume code or an external field exists. Two of the three
data sources here belong to other people and can change without telling you.
Hallucinated references are a top source of bugs; remembered API shapes are the
next.

**Checkpoint**: Files to modify and patterns discovered.

---

## Phase 3: Implementation (Test-Driven)

**Goal**: Build in tight Red-Green-Refactor cycles.

The TDD loop **is** the implementation. Each cycle targets a single behaviour.
Do not write all tests first and then implement — alternate.

### New Feature Development

For each behaviour, repeat:

#### RED — Write a Failing Test
Write one test for the next behaviour. Run it — it MUST fail. A test that passes
before the implementation exists is testing nothing.

Include adversarial cases as test cases, not afterthoughts:
- Missing, empty, null and malformed input
- A record that appears twice
- A stage running again over data it has already processed
- Boundary dates: an event spanning midnight, a December post about a January
  event, an event whose start and end are the same

#### GREEN — Implement Minimal Code
The minimum that makes the test pass. No gold-plating. No "while I'm here".
Documentation updates are not gold-plating — see Phase 5.

#### REFACTOR — Clean Up Before Moving On
- Extract a function if one is growing beyond 5–8 lines
- Extract a module if one is accumulating unrelated jobs
- Simplify conditionals
- Improve naming so the code reads as prose
- Check each function works at one level of abstraction
- Keep the four stages separate — poll, extract, reconcile, build. If a change
  makes one import another, stop: that is a design change, and it costs the
  ability to run the ICS builder against fixtures with no network.

Do not move to the next RED until the current code is clean.

#### Mutation Testing Mindset
- Do not assert success — assert specific values, counts and state changes
- Test boundaries: if code checks `>= 0.6`, test 0.59, 0.6 and 0.61
- Verify side effects: if a function writes three fields, assert all three
- If someone changed `>` to `>=`, would a test catch it? If not, add one.

### Bug Fixes

#### 3.1 Diagnose
Understand the bug and what allowed it. Map every code path that touches the
affected data. Identify where the expectation breaks and whether the same
pattern exists in another stage.

#### 3.2 RED — Reproduce It
Write a test that fails because of the bug. Run it — it MUST fail. For anything
involving a real message or a real feed record, capture the actual payload as a
fixture and test against that. A bug reproduced from invented data is a bug you
have guessed at.

#### 3.3 GREEN — Fix It
The test from 3.2 must now pass.

#### 3.4 REFACTOR — Address What Allowed It
If the bug was enabled by structure — a decision made in two places, a value
hard-coded away from `config.py`, a stage reaching into another's data — change
the structure so this class of bug becomes unlikely.

#### 3.5 Widen the Net
If 3.1 found the same pattern elsewhere, write tests for those cases and fix
them in the same change.

### Design Heuristics

Apply as concrete constraints during every REFACTOR:
- **Functions**: under 5–8 lines where possible. One level of abstraction each.
- **Modules**: one job each, matching the stage split in §5 of the build plan.
- **Parameters**: no more than 4. If you need more, pass the `Event` or a small
  object.
- **Configuration**: thresholds, URLs, model names, limits and paths live in
  `config.py`. Never inline. A matching threshold buried in a function body is a
  decision nobody can find.
- **Dependencies**: point inward toward the `Event` model, not outward toward
  Discord or the feed.

### Implementation Rules

- Follow the conventions already in the repo
- Use existing constants — never hard-code a value that already has a name
- Never skip input validation on anything that came from outside the process
- Every network call gets a timeout and a retry, and handles 429 with
  `Retry-After`
- Log enough to diagnose a failed run you did not watch — this job runs
  unattended on a schedule, and a silent failure is the normal way this project
  breaks
- Update the todo list as you go

### The hazards specific to this project

Not concurrency. These four, and they are worth writing down before implementing
anything that touches them:

**1. Re-running must be safe.** The job runs every three hours and will re-process, re-fetch
and rebuild. State the answer before you code: what does this do the second time
it sees the same message? The rule is that a rebuild replaces, never appends.

```
# WRONG: a fresh identifier each run
uid = uuid4()                     # every rebuild creates a NEW calendar entry
                                  # symptom: the same event four times by Thursday

# CORRECT: derived from the event itself
uid = f"{event.event_id}@pogo-event-calendar"
```

Never derive a `UID` from a timestamp, a hash of the description, a counter, or
anything that changes when the wording changes. Subscribed calendars are
read-only — duplicates cannot be deleted by hand, only regenerated away.

**2. The cursor must never outrun the work.** It records the last message
successfully processed. Advancing it past a message that failed loses that post
permanently, because nothing will ever look at it again.

```
# WRONG: cursor advanced regardless
for msg in messages:
    try: process(msg)
    except: log(...)
    cursor = msg.id            # the failure is now unreachable forever

# CORRECT: advance only past success, and stop advancing at the first failure
for msg in messages:
    try:
        process(msg)
    except Exception:
        log(...)
        break                  # keep the cursor where it is; retry next hour
    cursor = msg.id
```

Whichever policy is chosen — stop at the failure, or skip it and record it for
retry — it must be a decision written down, not an accident of control flow.

**3. Timezone information leaks in one direction only.** A naive datetime means
floating local time; an aware one means fixed UTC. The conversion happens in one
place. Any code that calls `.astimezone()`, `.replace(tzinfo=...)`,
`datetime.now()` without care, or lets a library attach a local zone is a bug
whether or not a test catches it. Test both directions explicitly, and assert on
the generated ICS text — not on the datetime object, which will look fine.

**4. One bad post must not wedge the run.** Every per-message operation is
wrapped, logged and survivable. The calendar still rebuilds from everything
else. A run that produces nothing because one image was odd is the worst
outcome available, because it looks identical to a run with nothing new.

**Cost and courtesy**: every vision call spends money and every poll hits
somebody else's API. During development, work against saved fixtures. Do not
call the vision model in a loop to see what happens.

**Checkpoint**: All behaviours implemented via Red-Green-Refactor. Tests
passing. Code clean.

---

## Phase 4: Full Test Suite Verification

**Goal**: No regressions.

Run `uv run pytest` in full before committing. Every time.

**If tests fail**:
1. Analyse the failure — do not guess
2. Fix the root cause, not the symptom
3. Re-run
4. Repeat until zero failures

**NEVER commit with failing tests.**

Then run the thing itself. A green suite here proves less than usual: the
fixtures are saved, the network is not exercised, and nothing in the suite can
see a calendar application. Rebuild `docs/pogo.ics` and read it — the event
count, one full `VEVENT`, and the `DTSTART` lines.

**Checkpoint**: Test results (pass count, any failures), and what the rebuilt
calendar contains.

---

## Phase 5: Documentation

**Goal**: Keep the written record in sync with the code.

### 5.1 Documentation Review
When a change affects documented behaviour — a new command, a change to the
`Event` model, a new environment variable, a changed matching rule — update:
- `README.md` if it changes what the owner does or sees
- `CLAUDE.md` if it changes a standing rule
- `docs/PogoCalBuildPlan.md` §8 if you learned something that cost an hour.
  Symptom first: the symptom is what a future reader searches for.

This is not optional. Skipping it when behaviour changes creates drift that
compounds.

### 5.2 Plans
Record what landed in `.claude/plans/plan-of-action.md`, including anything
noticed and deliberately not acted on. See the `update-plans` skill.

### 5.3 Clean Up
Remove dead code — do not comment it out.

**Checkpoint**: Documentation current.

---

## Phase 6: Pre-Commit Review

**Goal**: Final quality gate.

**Self-Review Checklist**:
- [ ] The milestone's acceptance check is addressed, or clearly stated as the
      owner's to run
- [ ] No hard-coded values that belong in `config.py`
- [ ] No assumptions made without verification
- [ ] Edge cases handled
- [ ] Error handling complete; every per-message failure caught and logged
- [ ] **No secret in the diff.** `.env` is not staged; no token, key, guild ID or
      channel ID pasted into code, a test, a fixture or a document. This repo is
      public.
- [ ] **No Discord CDN URL written into calendar output or committed state.**
      They expire in about 24 hours. Grep the diff for `cdn.discordapp.com` and
      `media.discordapp.net`
- [ ] Tests cover the new behaviour
- [ ] Full suite passes
- [ ] Documentation updated where behaviour changed
- [ ] Design heuristics applied
- [ ] Scope respected

**Verify Adversarial Test Coverage**:
Confirm tests exist for each. If any are missing, write them before committing.
- The same input processed twice produces one calendar entry, not two
- Missing, empty, null and malformed input at every boundary the change touches
- A failure partway through a multi-post run leaves the cursor recoverable
- A floating-time event survives the whole pipeline with no timezone attached
- A fixed-time (`Z`) event keeps its `Z`

**Checkpoint**: Ready to commit.

---

## Phase 7: Review the Diff

There is no automated reviewer on this repository, so this step is yours.

```bash
git diff main...HEAD
```

Read every changed line as a critical reviewer. Look for: missing error
handling, a second place deciding something that should be decided once, a value
that should be configuration, a test that would pass against broken code, a
secret, an expiring URL.

Then, if the change touches what the calendar contains, do the check no diff can
do: rebuild it and look at the output beside the previous version.

**Checkpoint**: Diff reviewed, findings resolved.

---

## Summary Output

After completing all phases:

1. **What was built**
2. **Files modified**
3. **Tests added/modified**
4. **Documentation updated**
5. **What the rebuilt calendar contains** — event count and anything that changed
6. **What only the owner can verify** — anything needing their calendar, phone
   or Mac timezone
7. **Next steps** — follow-up work identified

---

## Remember

- **Thoroughness saves time. Cutting corners breaks things.**
- **Every bug is a symptom. Find what allowed it, in the code and in the design.**
- **Never assume code or an external field exists. Verify before referencing.**
- **A green test suite is not a correct calendar.** The output that matters is
  on the owner's phone, and no test here can see it.
- **Stop when the milestone's acceptance check is met and every verification you
  can run has run.** Do not refactor code you were not asked to change. Do not
  add tests for pre-existing issues. Do not skip ahead to the next milestone.
  Note follow-up work in the summary and move on.
