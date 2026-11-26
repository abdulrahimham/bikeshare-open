# Seeded faults (Exercise 2)

Each fault was seeded by a headless Claude Code session (`claude -p`, Claude Code 2.1.332) running in this repo, so the
project's `.claude/settings.json` hook fired exactly as it would in an interactive session. The hook output below is the
`stderr` the hook sent back to the agent, copied from the session's `stream-json` transcript. The `make test` output was
captured right after each fault was seeded. The only edit to the pasted text: the absolute path of the repo is shortened to `<repo>`.

"Turns to fix" is `num_turns` from a separate, fresh Claude Code session that was told only "make test is failing in this
repo. Find the cause and fix it" (faults 1 and 2), or was told what the fault was (faults 3 and 4, where no test was red).

| # | Fault | Hook fired? | `make test` | Turns to fix |
|---|---|---|---|---|
| 1 | `"casual"` appended to `feature_columns()` | Yes, exit 2 | 1 failed | 5 |
| 2 | `.shift(1)` deleted from `cnt_roll_7` | Yes, exit 2 | 1 failed | 6 |
| 3 | `raise` removed from `encode_weather` | No (exit 0) | **green** | 8 (included writing the missing test) |
| 4 | Raw CSV overwritten from Bash | No (hook never ran) | **green** | 11 (included writing the hash guard) |

---

## Fault 1: a forbidden column added to `feature_columns`

**Change** (commit "Seed fault 1"):

```diff
diff --git a/src/features.py b/src/features.py
index e51b20d..aff0666 100644
--- a/src/features.py
+++ b/src/features.py
@@ -82,7 +82,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

**Hook stderr** (PostToolUse on Edit):

```
exit_code: 2
--- stderr ---
Leakage tests failed after editing <repo>/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_7   cnt_roll_7 cnt_roll_std_7
0   2011-01-10     10.0  WINTER  ...     1...857     886.694316
713 2012-12-31    731.0  WINTER  ...      920.0  1531.428571     887.135250

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_roll_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.38s
```

**`make test`:**

```
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'cnt_roll_std_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 1.27s
make: *** [Makefile:15: test] Error 1
```

**Fix:** a fresh session found it in **5 turns** and removed `+ ["casual"]`. One caveat: I committed the fault before
running the fixer, and it read the commit message ("Seed fault 1: add forbidden column casual..."), so this count is
lower than a blind fix would be. For faults 2 and 3, I ran the fixer before committing.

---

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

**Change:**

```diff
diff --git a/src/features.py b/src/features.py
index e51b20d..2e1a0a0 100644
--- a/src/features.py
+++ b/src/features.py
@@ -73,7 +73,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
     out["cnt_roll_std_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).std()
 
     return out.dropna().reset_index(drop=True)
```

**Hook stderr:**

```
exit_code: 2
--- stderr ---
Leakage tests failed after editing <repo>/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.41s
```

**`make test`:**

```
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 1.18s
make: *** [Makefile:15: test] Error 1
```

**Fix:** **6 turns**. The fixer ran the tests, read `git diff` (the fault was still uncommitted), and put `.shift(1)`
back before `.rolling()`.

Note that the failing test checks a single date (row 200). The 7-day rolling mean is wrong on every row once the shift
is gone, so one date is enough here. But the starter test wraps its check in `if all(d in by_date.index ...)`, which means
it would silently pass if that window ever hit a missing day. My new `test_rolling_std_excludes_today` asserts the
window is complete instead of skipping.

---

## Fault 3: the weather encoder's `raise` removed

**Change:**

```diff
diff --git a/src/features.py b/src/features.py
index e51b20d..99838af 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
```

**Hook stderr:** the hook ran and passed, so nothing reached the agent.

```
exit_code: 0
--- stderr ---
(empty)
```

**`make test`:** green.

```
python -m pytest tests/ -q
................                                                         [100%]
16 passed in 1.35s
```

**This is the finding.** The starter suite cannot see this fault. The real data only contains `GOOD`, `MISTY` and `BAD`,
so the encoder never meets an unknown label, the guard is never exercised, and every test passes with or without it.
The guard only protects against data we do not have yet, so it needs a test that feeds it data we do not have.

**Fix (8 turns):** a session added `test_weather_encoder_rejects_unknown_labels`, which calls `encode_weather` on a
series containing `"STORM"` and expects `ValueError`. Run against the faulty encoder, it failed:

```
python -m pytest tests/ -q
.............F...                                                        [100%]
=================================== FAILURES ===================================
_________________ test_weather_encoder_rejects_unknown_labels __________________

    def test_weather_encoder_rejects_unknown_labels():
        """The real data only holds GOOD/MISTY/BAD, so no data-driven test can
        see a missing guard. An unseen label must raise, not silently become NaN
        and get dropped by dropna()."""
>       with pytest.raises(ValueError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:88: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 16 passed in 1.23s
make: *** [Makefile:15: test] Error 1
```

It then restored the `raise`, and all tests passed. To confirm the hook now covers this fault, I seeded it a second time
after the new test was committed. This time the hook fired:

```
exit_code: 2
--- stderr ---
Leakage tests failed after editing <repo>/src/features.py:
........F                                                                [100%]
=================================== FAILURES ===================================
_________________ test_weather_encoder_rejects_unknown_labels __________________

    def test_weather_encoder_rejects_unknown_labels():
        """The real data only holds GOOD/MISTY/BAD, so no data-driven test can
        see a missing guard. An unseen label must raise, not silently become NaN
        and get dropped by dropna()."""
>       with pytest.raises(ValueError):
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:88: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 8 passed in 0.36s
```

---

## Fault 4: the raw data overwritten from Bash (the one the hook cannot see)

**Change:** an edited copy of the CSV (the `temp` for 2012-07-04 changed from 29.09 to 15.0, re-saved with Python's
`csv` writer) was copied over `data/raw/bike_daily.csv` from a Bash command.

**What happened.** The tutorial says a `cp` is not stopped by the `Write(./data/raw/**)` deny rule. In Claude Code
2.1.332, it was:

```
$ cp bike_daily_fixed.csv data/raw/bike_daily.csv
Permission to use Bash with command cp bike_daily_fixed.csv data/raw/bike_daily.csv has been denied.
```

So this version of Claude Code checks the target of a plain `cp` against the deny rules. The point of the exercise still
holds one step further out. The same write done through Python went straight through, with no denial and no hook:

```
$ python -c "import shutil; shutil.copy('bike_daily_fixed.csv', 'data/raw/bike_daily.csv')"
(Bash completed with no output)
```

- **Hook:** never ran. The `PostToolUse` matcher is `Edit|Write`, and this was a `Bash` call.
- **Raw file hash:** changed from `a6bed1577f6e4de5...` to `42fa208b2fa85612...`.
- **`make test`:** still green.

```
.................                                                        [100%]
17 passed in 1.19s
```

Nothing in the pipeline noticed that its input data had changed.

**What would catch it:**
- **A hash check on the raw file** (implemented). This one doesn't care how the file was changed.
- **A `PreToolUse` hook on `Bash`** that refuses any command mentioning `data/raw/`. It can be bypassed by building the path in code.
- **A `Stop` hook** that runs `make test`. It only helps once a test can see the change, which needs the hash check anyway.
- **A filesystem permission** (`chmod -w data/raw/`), which stops every write method, but can be undone by the agent with `chmod`.
- **`git status`**, which shows the file as modified.

**Implemented (11 turns):** `RAW_SHA256` in `src/config.py`, `load_raw()` refusing a file whose sha256 does not
match, and `test_raw_data_is_unchanged` in `tests/test_contract.py`. Diff:

```diff
diff --git a/src/config.py b/src/config.py
index f3232d4..3da6de5 100644
--- a/src/config.py
+++ b/src/config.py
@@ -6,6 +6,11 @@ RAW = ROOT / "data" / "raw" / "bike_daily.csv"
 PROCESSED = ROOT / "data" / "processed" / "features.parquet"
 METRICS = ROOT / "reports" / "metrics.json"
 
+# sha256 of the committed raw file (git show HEAD:data/raw/bike_daily.csv).
+# load_raw() refuses to read a file that does not match. If the raw data is
+# deliberately replaced, update this hash in the same commit.
+RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
+
 # Daily Capital Bikeshare counts (Fanaee-T & Gama). Canonical home:
 #   https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
 # We use the processed copy from Molnar's "Interpretable Machine Learning"
diff --git a/src/ingest.py b/src/ingest.py
index 6654075..fc4ca90 100644
--- a/src/ingest.py
+++ b/src/ingest.py
@@ -2,12 +2,13 @@
 
 Run: python -m src.ingest
 """
+import hashlib
 import sys
 import urllib.request
 
 import pandas as pd
 
-from src.config import DATA_URL, RAW
+from src.config import DATA_URL, RAW, RAW_SHA256
 
 EXPECTED_MIN_ROWS = 700
 REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}
@@ -20,7 +21,18 @@ def download(force: bool = False) -> None:
     urllib.request.urlretrieve(DATA_URL, RAW)
 
 
+def sha256_of(path) -> str:
+    return hashlib.sha256(path.read_bytes()).hexdigest()
+
+
 def load_raw() -> pd.DataFrame:
+    actual = sha256_of(RAW)
+    if actual != RAW_SHA256:
+        raise ValueError(
+            f"{RAW} has changed: sha256 is {actual}, expected {RAW_SHA256}. "
+            "Restore it with `git checkout -- data/raw/bike_daily.csv`, or if the "
+            "change is intended, update RAW_SHA256 in src/config.py."
+        )
     df = pd.read_csv(RAW, parse_dates=["dteday"])
     missing = REQUIRED_COLS - set(df.columns)
     if missing:
diff --git a/tests/test_contract.py b/tests/test_contract.py
index 13eb495..b71ac71 100644
--- a/tests/test_contract.py
+++ b/tests/test_contract.py
@@ -8,11 +8,12 @@ from src.config import (
     LAG_WARMUP,
     RAW,
     RAW_FEATURE_COLS,
+    RAW_SHA256,
     SOURCE_COLS,
     TARGET,
 )
 from src.features import build_features, feature_columns, reindex_to_calendar
-from src.ingest import load_raw
+from src.ingest import load_raw, sha256_of
 from src.train import MODELS, temporal_split
 
 
@@ -33,6 +34,15 @@ def unclassified_columns(path) -> set[str]:
     return header - FORBIDDEN - RAW_FEATURE_COLS - SOURCE_COLS - {"dteday"}
 
 
+def test_raw_data_is_unchanged():
+    """data/raw/ is read-only. Any edit, however it was made (editor, script,
+    shutil.copy), changes the hash and must fail here, not slip through."""
+    actual = sha256_of(RAW)
+    assert actual == RAW_SHA256, (
+        f"{RAW} sha256 is {actual}, expected {RAW_SHA256}"
+    )
+
+
 def test_every_raw_column_is_classified():
     """feature_columns() is a denylist: a new numeric raw column would become
     a model feature with no one deciding it should. Every raw column must be
```

**`make test` against the overwritten file, with the guard in place:**

```
__________________________ test_raw_data_is_unchanged __________________________

    def test_raw_data_is_unchanged():
        """data/raw/ is read-only. Any edit, however it was made (editor, script,
        shutil.copy), changes the hash and must fail here, not slip through."""
        actual = sha256_of(RAW)
>       assert actual == RAW_SHA256, (
            f"{RAW} sha256 is {actual}, expected {RAW_SHA256}"
        )
E       AssertionError: <repo>/data/raw/bike_daily.csv sha256 is 42fa208b2fa85612018a7303df5d885a25945909be7e18101346d59256439fdf, expected a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
E       assert '42fa208b2fa8...6d59256439fdf' == 'a6bed1577f6e...0c86a0b5ad9dc'
E         
E         - a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
E         + 42fa208b2fa85612018a7303df5d885a25945909be7e18101346d59256439fdf

tests/test_contract.py:41: AssertionError
```

```
FAILED tests/test_contract.py::test_raw_data_is_unchanged - AssertionError: /...
ERROR tests/test_contract.py::test_calendar_is_complete_before_lagging - Valu...
ERROR tests/test_contract.py::test_only_expected_rows_are_dropped - ValueErro...
ERROR tests/test_contract.py::test_beats_the_mean_baseline - ValueError: /tmp...
ERROR tests/test_leakage.py::test_leakage_identity_holds - ValueError: /tmp/c...
ERROR tests/test_leakage.py::test_no_forbidden_features - ValueError: /tmp/cl...
ERROR tests/test_leakage.py::test_lags_are_true_calendar_lags - ValueError: /...
ERROR tests/test_leakage.py::test_lag_is_not_the_target - ValueError: /tmp/cl...
ERROR tests/test_leakage.py::test_rolling_mean_excludes_today - ValueError: /...
ERROR tests/test_leakage.py::test_rolling_std_excludes_today - ValueError: /t...
ERROR tests/test_leakage.py::test_no_missing_values - ValueError: /tmp/claude...
ERROR tests/test_leakage.py::test_dates_are_sorted_and_unique - ValueError: /...
ERROR tests/test_split.py::test_splits_non_empty - ValueError: /tmp/claude-0/...
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: /tmp...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: /tmp/claud...
1 failed, 3 passed, 14 errors in 1.28s
make: *** [Makefile:15: test] Error 1
```

The 14 errors are every test that loads the raw file. They fail with the same `ValueError` from `load_raw()`, so
`make features` and `make train` would refuse to run too. The raw file was then restored with
`git checkout -- data/raw/bike_daily.csv`. Its sha256 begins `a6bed1577f6e4de5` again, and `make test` passes.

---

## Extra: a leaked column renamed to something innocent

`test_no_forbidden_features` only checks names, and `feature_columns()` is a denylist, so
`out["riders_a"] = out["casual"]` would reach the model with every test green. I added
`test_no_feature_restates_a_leakage_column`. It fails if any feature is an exact affine copy of a leakage column, or if
the features reproduce `cnt` exactly by least squares. Hook output with `riders_a` added:

```
exit_code: 2
--- stderr ---
Leakage tests failed after editing <repo>/src/features.py:
        X = feats[cols].astype(float)
    
        # 1. No single feature is an exact affine function of a leakage column.
        restated = []
        for f in cols:
            x = X[f].to_numpy()
            if np.std(x) == 0:
                continue  # a constant restates nothing, and corrcoef would be NaN
            for leak in sorted(LEAKAGE_COLS):
                r = np.corrcoef(x, feats[leak].astype(float).to_numpy())[0, 1]
                if abs(r) > 0.9999:
                    restated.append(f"{f} ~ {leak} (r={r:+.6f})")
>       assert not restated, f"features that restate a leakage column: {restated}"
E       AssertionError: features that restate a leakage column: ['riders_a ~ casual (r=+1.000000)']
E       assert not ['riders_a ~ casual (r=+1.000000)']

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_feature_restates_a_leakage_column - Ass...
1 failed, 9 passed in 0.38s
```
