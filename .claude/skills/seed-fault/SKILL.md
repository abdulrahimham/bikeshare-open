---
name: seed-fault
description: Deliberately break the pipeline in one described way, record whether the hook and the tests catch it, then restore. Use when asked to seed, inject, or test a fault, or to check whether the suite would notice a specific bug.
allowed-tools: Read, Edit, Bash(make*), Bash(python -m pytest*), Bash(git diff*), Bash(git status), Bash(git checkout -- src/*), Bash(git checkout -- tests/*), Bash(git checkout -- data/raw/*)
---

# Current state

!`git status --short`

# Seeding a fault: $ARGUMENTS

Work in this order. The point is to find out what the guards miss, so
never weaken a test to make the fault "caught".

1. **Start clean.** If `git status` above shows uncommitted changes under
   `src/` or `tests/`, stop and ask. A fault seeded on top of other edits
   cannot be cleanly restored.
2. **Run `make test` first** and confirm it is green. Record the pass count.
3. **Make the smallest edit that produces the fault**, with the Edit tool
   when the fault lives in `src/` (so the PostToolUse hook runs). Change
   nothing else. Show the `git diff`.
4. **Record what fired, verbatim:**
   - the hook feedback you received after the edit (or "hook exit 0, no
     feedback" / "hook did not run" if the change was not an Edit to src/),
   - the summary lines of `make test` (FAILED / ERROR lines and the count).
5. **Classify the result** in one line:
   - `CAUGHT by hook` (exit 2 on the edit itself),
   - `CAUGHT by make test only` (hook silent, suite red),
   - `MISSED` (everything green). A miss is a finding: name the test that
     would have caught it, but do not write it unless asked.
6. **Restore.** `git checkout -- <the files you changed>`, then run
   `make test` and confirm the pass count from step 2. If raw data was
   touched, check its sha256 still begins `a6bed1577f6e4de5`.
7. **Report** a short block that can be pasted into
   `docs/SEEDED_FAULTS.md`: fault, diff, hook output, test output,
   classification, restored yes/no.

Never commit a seeded fault from this skill and never edit
`data/raw/bike_daily.csv` with Edit or Write (the settings deny it).
