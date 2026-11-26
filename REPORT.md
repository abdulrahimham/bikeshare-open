# MA6 Report: Forecasting Daily Bikeshare Rides

Abdulrahim Ham, DSC 180A, Fall 2026

The goal is to predict how many bikeshare rides happen each day (`cnt`).
- **Train:** 2011 (348 days).
- **Validation:** the first half of 2012 (182 days).
- **Test:** the second half of 2012 (184 days).

All numbers come from `make all` (`reports/metrics.json`) unless I say otherwise.

## Results

"Before" is the starter code with 14 features. "After" adds my new feature, `cnt_roll_std_7`, for 15 features. The
"after" rows are exactly what is in `reports/metrics.json`.

| Model | Feature set | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | after | 0.7224 | 700.4 | 0.6356 | 840.3 |
| hgb | after | 0.0977 | 1381.6 | -0.6959 | 2108.4 |

The two baselines don't use my feature, so their numbers don't change. I decided whether to keep the feature by looking
at the validation columns only. I first saw the "after" test numbers in the final `make all`.

## Headline finding

If you give the model `casual` and `registered`, it gets a test R² of 1.000, but that result is fake: those two columns
add up to `cnt`, so the model is just doing addition. With a proper time-based split, the honest results are:
- **Mean baseline:** test R² of -2.14. Riders in late 2012 were way above the 2011 average.
- **Ridge:** R² of 0.636, which beats "predict yesterday's count" (persistence, 0.510). But on average error they are
  basically tied: 840.3 vs 840.1 rides.
- **Gradient boosting:** -0.696. It still beats the mean baseline but nothing else. A tree model can't predict higher
  than the biggest number it saw in training (6,043 rides in 2011), and 56.5% of test days are above that.

My feature, `cnt_roll_std_7` (how much rides bounced around over the past week), raised ridge's validation R² from
0.648 to 0.722 and its test R² from 0.583 to 0.636, so I kept it. It made gradient boosting worse.

## Exercise 4: target transformation

**The question:** can a different target help the tree model deal with the growth in riders?

I tried two targets, each measured against something we already know on the day we predict. The model predicts the new
target, and then I convert it back to rides before scoring. The code is in `src/train.py` behind a `--target` option.
`reports/metrics.json` still uses the normal target.
- **diff:** predict today minus yesterday (`cnt - cnt_lag_1`).
- **ratio:** predict today divided by last week's average (`cnt / cnt_roll_7`).

Validation results:

| Target | ridge R² / MAE | hgb R² / MAE |
|---|---|---|
| raw | 0.7224 / 700.4 | 0.0977 / 1381.6 |
| diff | 0.7220 / 699.9 | 0.5642 / 885.8 |
| ratio | 0.6128 / 857.3 | 0.7483 / 685.5 |

Ratio works best for the tree. It now predicts "how today compares to last week", and that number doesn't keep growing,
because the growth is already built into last week's average. I picked ratio using validation, then ran the test set
**one time**. (The first time, the numbers were wrong because of an old, stale feature file left over from fault 4.
I re-ran the same choice on the correct data and report those numbers here. Details are in `docs/DECISIONS.md`.)
- **hgb with ratio:** R² 0.6280, MAE 832.8.
- **Persistence:** R² 0.5099, MAE 840.1.
- **Normal ridge:** R² 0.6356, MAE 840.3.

**Is this fair, or just a trick to win?** I think it's fair, but it's not a big win.
- **Why it's fair:** last week's average is known before the day we predict, so nothing leaks. The improvement also has
  a clear reason behind it (trees can't go above their training range).
- **Why it's not a big win:** I chose ratio after trying two options on the same 182 validation days. On test it only
  beats persistence by about 7 rides, and it doesn't beat normal ridge on R². So it makes the tree competitive, but
  I wouldn't say "boosting wins".

## Exercise 5: ridge vs persistence

I think ridge is worth using over "just predict yesterday", but only as a small improvement, and its bias has to be
mentioned.

**For ridge, on test:**
- **Typical error is a tie:** MAE is 840.3 for ridge vs 840.1 for persistence.
- **Ridge has fewer big misses:** higher R² (0.636 vs 0.510) and lower RMSE (1,051 vs 1,219). It was off by more than
  2,000 rides on 10 days, while persistence was off by that much on 17 days.
- **Ridge uses the weather:** after the lag features, its biggest effects are temperature (+363) and bad weather
  (-249). Persistence can't know a storm is coming, and storm days are exactly when a good forecast matters for moving
  bikes around or scheduling staff.

**Against ridge:**
- Persistence is closer on more days. Ridge is closer on only 43.5% of test days.
- On test, persistence has the smaller median error (506 vs 743).
- Ridge guesses too low by 372 rides a day on average on test, because it learned from 2011 when there were fewer riders.

So if every missed ride costs the same, the two are about equal. If big misses cost more, ridge is better. Fixing that
372-ride bias is the next step. (These extra numbers come from the same models and test predictions. I didn't change
anything after seeing them.)

## Attribution

I used `claude-opus-5-5` through Claude Code, on an Anthropic plan instead of a local Ollama model (the README allows
this), and the same model the whole time. I skipped the optional Exercise 6.

**What Claude Code did:**
- implemented the `cnt_roll_std_7` feature and wrote its test
- wrote the extra tests in `tests/`:
  - the raw-column check
  - the raw-data hash check
  - the renamed-leak check
  - the weather-label check
  - the `cnt_lag_7` check
- seeded and repaired the four faults (run in an identical copy of the repo, then moved here; see
  `docs/SEEDED_FAULTS.md`)
- added the `--target` option in `src/train.py` for Exercise 4
- wrote the `/seed-fault` skill
- ran `agent/audit.py` on my repo and the `leakage-auditor` on bscruzin's repo
- drafted the docs and this report

**What I did:** I directed the work, reviewed the results and the write-ups, and managed the repository.

**My decisions** (Claude showed me the options and the numbers; I made each choice. Each one has a line in
`docs/DECISIONS.md`):
1. **What to predict:** daily `cnt`, one day ahead.
2. **What counts as leakage:** `casual`, `registered`, and any renamed copy of them, checked using the data.
3. **How to split:** by date, looking at test only once per question.
4. **Which baselines:** mean and persistence, every time.
5. **My feature:** keep `cnt_roll_std_7`, based on validation.
6. **Protecting the data:** every raw column listed in the config, and the raw file locked with a hash.
7. **Whether the answers are believable:**
   - Exercise 4's ratio target is fair but not a big win.
   - Ridge is worth using only if its bias is mentioned.

**Running `agent/audit.py` on my repo.** The first two runs found three real problems, and I fixed them before the run
saved in `reports/audit.jsonl`:
1. `reports/metrics.json` wasn't saved in git. I committed it.
2. `CLAUDE.md` said `--target` runs should never touch test, but Exercise 4 asks you to check test once. I changed the
   rule to "use validation while trying things, then check test once and write it down". The auditor's warning still
   makes sense: don't compare ratio-hgb's test score to ridge as if it was picked blind. Exercise 4 above doesn't do that.
3. The README said there were 14 tests, but there are 20. I fixed it.

The final run found nothing (no leakage, correct split, baselines reported, reproducible, high confidence). That's just a
quick check, though, not proof that everything is right.
