# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25. Added `cnt_roll_std_7`: how much daily rides bounced around over the 7 days before today. It only uses past days, so it's known when we predict. Validation R^2: ridge 0.6475 -> 0.7224 (MAE 832.9 -> 700.4), hgb 0.2185 -> 0.0977. **Kept it**, because ridge is the model I'd actually use and the gain is way bigger than the 0.01 cutoff. hgb got worse, but it was already broken for the growth reason.
- 2026-11-25. Every column in the raw data has to be listed in `src/config.py`, and `test_every_raw_column_is_classified` checks this. Now a new column makes a test fail instead of quietly ending up in the model.
- 2026-11-25. Fault 3 showed the tests couldn't tell when the weather encoder's error check was removed, because the data has no unknown weather labels. Added a test that gives it a fake label (`"STORM"`).
- 2026-11-25. Locked the raw data with a fingerprint (`RAW_SHA256`) that `load_raw()` and a test both check. In fault 4, a Python copy into `data/raw/` got past the hook and the permission rules, and all tests still passed.
- 2026-11-25. Added `test_no_feature_restates_a_leakage_column`. It checks the actual numbers, because the name-only test misses a leaked column that has been renamed.
- 2026-11-25. My `/seed-fault` skill found that changing `cnt_lag_7` to `shift(6)` broke nothing in the tests. Added `test_lag_7_is_a_true_calendar_lag`.
- 2026-11-25. Exercise 4: tried two targets on validation only. hgb validation R^2 was 0.0977 normal, 0.5642 with diff, 0.7483 with ratio. Picked ratio and checked test once: hgb test R^2 0.6314, MAE 830.5, vs persistence 0.5099 / 840.1. My take: it's fair, since last week's average is known when we predict, but it's not a big win. I picked it after trying two options, and it only beats persistence by about 10 rides. `reports/metrics.json` still uses the normal target.
- 2026-11-25. Exercise 5: ridge is worth using over persistence, but only if its bias is mentioned. On test it ties on MAE (840.3 vs 840.1) but has fewer big misses (R^2 0.6356 vs 0.5099, RMSE 1051 vs 1219, and 10 vs 17 days off by 2,000+ rides). It also guesses too low by 372 rides a day.
- 2026-11-25. Updated `CLAUDE.md`: a rule that the raw data can't be changed, a rule for `--target` runs, my `/seed-fault` skill, and a note that `make all` reproduces `reports/metrics.json`.
- 2026-11-25. Used `claude-opus-5-5` through Claude Code instead of a local Ollama model, because there wasn't time before the deadline to download and test a 7 GB model. The README says this is allowed. I used the same model the whole time.
- 2026-11-25. Fixed what `agent/audit.py` found: committed `reports/metrics.json`, changed the `CLAUDE.md` `--target` rule to "use validation while trying things, check test once and write it down" (the old rule went against Exercise 4), and fixed the test count in the README (14 -> 20).
