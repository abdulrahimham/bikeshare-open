# Audit of a teammate's repo (Exercise 3)

**Repo audited:** https://github.com/bscruzin/DSC180A-Methodology-6 (commit `1a8d28f`, the last commit on 2026-11-25)

**How I ran it:**
- I cloned his repo and ran the `leakage-auditor` subagent from my repo on it.
- The model was `claude-opus-5-5` through Claude Code.
- The auditor ran `make all` and `make test` in his repo, then checked the code itself.

## Auditor output (verbatim)

The only change: the path of the auditor's scratch script is shortened to `<scratchpad>`.

The pipeline and the code are sound, and every reported number reproduces. One conclusion in REPORT.md is wrong: Exercise 5 recommends persistence because of a test-set comparison, but the validation set ranks ridge first.

## Build and tests

- **`make all`: PASS.** Ingest read 728 rows (2011-01-03 to 2012-12-31). Features built 714 rows and 15 features, including `cnt_roll_3`. Train wrote `reports/metrics.json` with mean, persistence, ridge and HGB scores for valid and test. No errors.
- **`make test`: PASS.** `18 passed in 1.31s`.

I ran both from the teammate repo using its `.venv`. The diff I reviewed is starter commit `c6126e9` to HEAD `1a8d28f`. In code, it adds `cnt_roll_3`, the `ResidualTarget` model with the `--residual` and `--residual-test` modes, and new tests. I also wrote my own check script and ran it against the repo: `<scratchpad>/verify.py`

## The five checks (verified by running code)

1. **Target leakage: pass.** None of `casual`, `registered`, `cnt`, `cnt_2d_bfr` or the time indexes reach the model. A linear fit of `cnt` on all 15 features over every row scores R² 0.83, not about 1.0, so no feature rebuilds the target. `ResidualTarget` only uses `cnt_lag_1`, which is known the day before.
2. **Temporal ordering: pass.** Every lag and rolling mean shifts by one day before it aggregates (`src/features.py:74-81`). The split is by date: train 2011-01-10 to 2011-12-31, valid 2012-01-01 to 06-30, test 2012-07-01 to 12-31. The ridge scaler is fit on training rows only; its means match the training means exactly.
3. **Calendar gaps: pass.** I compared all four lag features on all 714 rows against the raw calendar and found 0 mismatches. The missing day 2011-03-10 becomes an explicit empty row, and the 7 days after it are dropped.
4. **Silent row loss: pass.** 14 rows are lost: the first 7 days plus 2011-03-11 to 03-17. The raw data has no missing values. `tests/test_contract.py:28-43` caps the loss at exactly 14.
5. **Baselines: pass for the main pipeline.** Both baselines appear in `metrics.json` and in the main REPORT tables. The Exercise 4 code and table leave out the mean baseline (see the minor note below).

Every number in REPORT.md matches what I reproduced: both the "Original" (without `cnt_roll_3`) and "Updated" rows, the residual HGB row (0.6251 / 805.4 / 0.5670 / 883.8), and the derived differences (0.0036, 0.0202, 0.4268, 38.6%, 106.1).

## Findings

**1. Exercise 5 recommends a model based on the test set, and validation disagrees.** Severity: medium, because it changes the conclusion.
- **Where:** `REPORT.md:128-141`.
- **What it says:** recommend persistence because its test MAE (840.1) beats ridge's (946.2).
- **What validation says:** ridge wins on both measures, R² 0.6439 vs 0.4507 and MAE 836.5 vs 900.6.
- **Why it matters:** the repo's own rule (CLAUDE.md) is to choose using validation and never tune on test. Followed honestly, that rule picks ridge. Using the test set to choose makes the test score biased, and it is the only reason the recommendation flips.
- **Fix:** base the recommendation on validation (ridge). Keep test as a one-time held-out estimate, and report "ridge lost to persistence on test MAE" as a finding about how ridge generalises, not as the reason to pick persistence. The same applies to the residual HGB: it is best on validation MAE (805.4) but loses to persistence on test MAE (883.8 vs 840.1). The table shows this, but the text never says it.

**Minor (no number or conclusion changes): no mean baseline in Exercise 4.**
- **Where:** `src/train.py:128-135` and `src/train.py:164-169` (the two lineups), and the table at `REPORT.md:96-101`.
- **Fix:** add `MODELS["baseline_mean"]` to both lineups and a Mean row to the table.

Nothing went unrun or unchecked.

## My verdict

**Do any findings change a number?** No. The auditor reproduced every number in his report and `make test` passed
(18 tests), and I got the same `reports/metrics.json` when I ran `make all` myself.

**Finding 1 (Exercise 5 uses test numbers to pick persistence): I partly agree.**
- **What I agree with:** validation ranks ridge first (R² 0.6439 vs 0.4507, MAE 836.5 vs 900.6). So "pick persistence"
  only comes from the test set, and his report should say that.
- **What I disagree with:** I wouldn't call it tuning on test. Exercise 5 itself is framed around the test numbers
  ("ridge beats persistence by 0.07 R² and loses to it on MAE"). His conclusion also depends on which error matters
  most, which he says, and he doesn't change the model because of it.
- **So:** it's a fair point about how the recommendation is worded, not something that makes a result invalid.

**Minor finding (no mean baseline in his Exercise 4 table): I agree.** It doesn't change a number, but the assignment
asks for both baselines next to every score.

**Things the auditor didn't list but I noticed, also with no number changes:**
- He kept `cnt_roll_3` in the final pipeline even though he recommends dropping it. He explains why in his
  `DECISIONS.md`, so it's a documented choice, not a hidden one.
- His repo has no `docs/AUDIT.md` or `reports/audit.jsonl` yet. His report says both are still pending.
