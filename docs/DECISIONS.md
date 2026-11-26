# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25. Added `cnt_roll_std_7`, the standard deviation of `cnt` over the 7 calendar days before d. Availability: it uses only d-7 to d-1, all known before d. Validation R^2: ridge 0.6475 -> 0.7224 (MAE 832.9 -> 700.4), hgb 0.2185 -> 0.0977. **Kept**, because ridge is the model I would deploy and its gain is about 7x the 0.01 floor. hgb gets worse, but it was already failing for the extrapolation reason.
- 2026-11-25. Every raw column must be named in `src/config.py` (`FORBIDDEN`, `RAW_FEATURE_COLS`, `SOURCE_COLS` or `dteday`), and `test_every_raw_column_is_classified` enforces it. `feature_columns()` stays a denylist, so a new raw column now fails loudly instead of entering the model silently. That is the failure I would rather have.
- 2026-11-25. Seeding fault 3 showed the suite cannot see a missing `raise` in `encode_weather`, because the data has no unknown labels. Added a test that feeds it `"STORM"`.
- 2026-11-25. Raw data is guarded by `RAW_SHA256` in `load_raw()` and `test_raw_data_is_unchanged`. A Python write into `data/raw/` from Bash got past both the hook and the deny rules (fault 4), and the tests stayed green.
- 2026-11-25. Added `test_no_feature_restates_a_leakage_column`, a check on the data (correlation and exact least-squares identity), because the name-based test cannot see a leaked column under a new name.
- 2026-11-25. `/seed-fault` found that changing `cnt_lag_7` to `shift(6)` was missed by every test. Added `test_lag_7_is_a_true_calendar_lag`.
- 2026-11-25. Exercise 4: compared `diff` (y - cnt_lag_1) and `ratio` (y / cnt_roll_7) targets on validation only. Validation R^2 for hgb: raw 0.0977, diff 0.5642, ratio 0.7483. Chose ratio and touched test once: hgb test R^2 0.6314, MAE 830.5, vs persistence 0.5099 / 840.1. My verdict: defensible as a forecasting setup, since `cnt_roll_7` is known at prediction time and fixes the extrapolation problem for a real reason. But it was picked after comparing two options on validation, and it beats persistence by only 9.6 rides of MAE on test. Not adopted: the committed `reports/metrics.json` stays on the raw target.
- 2026-11-25. Exercise 5: ridge is worth deploying over persistence, but only with its bias stated. It ties persistence on test MAE (840.3 vs 840.1), wins on R^2 (0.6356 vs 0.5099) and RMSE (1051 vs 1219), and has 10 days off by more than 2,000 rides vs 17. It is also biased low by 372 rides a day on test, so the trend still needs handling.
- 2026-11-25. Updated `CLAUDE.md`: added the raw-data rule, the rule that `--target` runs are validation-only, the `/seed-fault` skill, and that `make all` reproduces `reports/metrics.json`.
- 2026-11-25. Agent model: used `claude-opus-5-5` through Claude Code (Anthropic plan, set in the git-ignored `.claude/settings.local.json`) instead of a local Ollama model, because the deadline left no time to download and test a 7 GB local model. The README allows this setup. All agent runs used the same model.
- 2026-11-25. Acted on `agent/audit.py` findings: committed `reports/metrics.json`; reworded the `CLAUDE.md` `--target` rule to "iterate on validation, score test once per question after logging the choice" (the old wording contradicted Exercise 4); fixed the README's test count (14 -> 20). `CLAUDE.md` is now 50 lines.
