---
name: seed-fault
description: Break the pipeline on purpose in one way, see if the hook and tests catch it, then put it back. Use when I ask to seed a fault or check if the tests would notice a bug.
allowed-tools: Read, Edit, Bash(make*), Bash(python -m pytest*), Bash(git diff*), Bash(git status), Bash(git checkout -- src/*), Bash(git checkout -- tests/*), Bash(git checkout -- data/raw/*)
---

# What's changed right now

!`git status --short`

# Fault to try: $ARGUMENTS

1. **Check that nothing else is changed.** If `git status` above shows edits in
   `src/` or `tests/`, stop and ask me first.
2. **Run `make test`** and write down how many tests pass.
3. **Make the fault.** Make the smallest change that causes it, using the Edit
   tool if the file is in `src/` (so the hook runs). Don't change anything else.
   Show me the `git diff`.
4. **Write down what happened, word for word:**
   - what the hook said after the edit (or that it said nothing)
   - the FAILED / ERROR lines and the pass count from `make test`
5. **Say if it was caught:**
   - **Caught by the hook:** the hook failed right after the edit
   - **Caught by `make test` only:** the hook was quiet but a test failed
   - **Missed:** everything passed. Tell me which test would have caught it,
     but don't write it unless I ask.
6. **Put it back.** Run `git checkout -- <files you changed>`, then `make test`
   and check you get the same pass count as step 2.
7. **Give me a short summary** I can paste into `docs/SEEDED_FAULTS.md`: the fault,
   the diff, the hook output, the test output, whether it was caught, and that it
   was put back.

Don't commit the fault, and don't change a test to make the fault "caught".
