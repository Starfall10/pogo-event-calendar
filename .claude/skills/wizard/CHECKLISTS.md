# Quick Reference Checklists

## Pre-Implementation Checklist

- [ ] Read `CLAUDE.md`
- [ ] Read `docs/PogoCalBuildPlan.md` §5 (architecture, the `Event` model) and the
      milestone in §6
- [ ] Read §8, the gotchas list — every time, not once
- [ ] Read `.claude/plans/plan-of-action.md` for what already landed
- [ ] Assessed complexity (simple / medium / complex)
- [ ] Wrote the plan down somewhere that survives the session
- [ ] Verified every function, field and feed key exists (grep, or a saved fixture)
- [ ] Identified patterns to follow
- [ ] Listed files to modify

## TDD Checklist (New Features)

- [ ] Wrote the failing test FIRST (RED)
- [ ] Test fails for the right reason
- [ ] Implemented minimal code (GREEN)
- [ ] Test passes
- [ ] Refactored: function length, module job, naming, abstraction level
- [ ] Added boundary tests (0, 1, −1, null, empty, threshold ± 0.01)
- [ ] Added side-effect assertions
- [ ] Tests run with no network and no API key

## TDD Checklist (Bug Fixes)

- [ ] Diagnosed the cause and mapped every path that touches the data
- [ ] Checked whether the same pattern exists in another stage
- [ ] Captured the real payload as a fixture rather than inventing one
- [ ] Wrote a test that reproduces the bug (RED)
- [ ] Test fails because of the bug
- [ ] Applied the fix (GREEN)
- [ ] Test passes
- [ ] Refactored to address what allowed it
- [ ] Wrote tests for related instances of the same pattern

## Implementation Checklist

- [ ] Constants in `config.py`, not inline
- [ ] Four stages still separate — poll, extract, reconcile, build
- [ ] The ICS builder still runs against fixtures with no network
- [ ] Every network call has a timeout and a retry, and handles 429
- [ ] Every per-message failure caught, logged and survivable
- [ ] Anything that found nothing logs loudly rather than returning empty
- [ ] Timezone decision made in exactly one place

## Design Heuristics Checklist

- [ ] Functions under 5–8 lines where possible
- [ ] One level of abstraction per function
- [ ] One job per module
- [ ] No more than 4 parameters per function
- [ ] Dependencies point inward toward the `Event` model

## Idempotency Checklist

Run through this for anything that touches state or output.

- [ ] `UID` derived from the event, never from a timestamp, counter or wording hash
- [ ] Running the same input twice produces one calendar entry, not two
- [ ] `revision` / `SEQUENCE` bumps when content changes
- [ ] The cursor never advances past a message that failed
- [ ] Discord results reversed before processing (the API returns newest-first)
- [ ] The calendar is rewritten from state, never appended to
- [ ] A run with nothing new produces no commit

## Pre-Commit Checklist

- [ ] Acceptance check addressed, or stated as the owner's to run
- [ ] No hard-coded values that belong in `config.py`
- [ ] No assumptions made without verification
- [ ] Edge cases handled
- [ ] **No secret in the diff** — `.env` unstaged, no token, key, guild ID or
      channel ID anywhere. This repo is public
- [ ] **No Discord CDN URL** in `src/`, `state/` or `docs/pogo.ics`
- [ ] No `TZID` in the generated calendar
- [ ] Tests cover the new behaviour
- [ ] Full suite passes (`uv run pytest`)
- [ ] Calendar rebuilt and read, not just generated
- [ ] Documentation updated where behaviour changed
- [ ] `.claude/plans/` updated with what landed and what was left
- [ ] Scope respected — nothing changed outside the task

## Adversarial Test Coverage Verification

Before committing, confirm a test exists for each. If any is missing, write it.

1. The same message processed twice — one calendar entry, or two? (test: yes/no)
2. Missing, empty, null, malformed input at each boundary touched (tests: yes/no)
3. A failure partway through a multi-post run — is the cursor recoverable? (test: yes/no)
4. A floating event through the whole pipeline — still no timezone at the end? (test: yes/no)
5. A fixed (`Z`) event through the whole pipeline — still `Z` at the end? (test: yes/no)
6. An event that matches two feed records — which wins, and is it flagged? (test: yes/no)
7. An event that matches none — kept, flagged `low`, `⚠️` on the title? (test: yes/no)
8. A December post announcing a January event — right year? (test: yes/no)
9. The feed unreachable, or its shape changed — does the run fail loudly? (test: yes/no)

## Test Strategy

Run the full suite before every commit. No exceptions.

Tests must run offline: no Discord call, no vision call, no feed fetch. Every
external payload is a saved fixture. A test that needs an API key is a test that
will not run on the evening you need it.

## Useful Commands

```bash
uv run pytest                      # the full suite
uv run pogocal build               # rebuild docs/pogo.ics from state, no network
uv run pogocal poll                # spends API credit and moves the cursor — deliberate use only
git diff --stat                    # what this change touched
grep -c "^BEGIN:VEVENT" docs/pogo.ics
```
