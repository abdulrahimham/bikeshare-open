# Seeded faults (Exercise 2)

**Setup:**
- I used Claude Code 2.1.332 with `claude-opus-5-5`, not a local Ollama model. The README says that's allowed.
- I ran the faults in a copy of the repo made from `bikeshare-starter.zip`. Its code, tests, hook and data are exactly
  the same as the open starter's. I then moved the commits over to this repo in the same order.
- To make sure the hook works the same here, I broke fault 1 again in `bikeshare-open`. The hook caught it, with two tests
  failing: `FAILED tests/test_leakage.py::test_no_forbidden_features` and
  `FAILED tests/test_leakage.py::test_no_feature_restates_a_leakage_column`.

**Where the output comes from:**
- The hook output is copied from each agent session's log.
- The `make test` output was saved right after each fault was added.
- The only thing I changed in the pasted output is shortening the long repo path to `<repo>`.

**"Turns to fix"** is how many turns a brand-new agent session needed:
- **Faults 1 and 2:** it was only told "make test is failing, find and fix it".
- **Faults 3 and 4:** no test failed, so I had to tell it what was wrong.

| # | Fault | Hook fired? | `make test` | Turns to fix |
|---|---|---|---|---|
| 1 | `"casual"` appended to `feature_columns()` | Yes, exit 2 | 1 failed | 5 |
| 2 | `.shift(1)` deleted from `cnt_roll_7` | Yes, exit 2 | 1 failed | 6 |
| 3 | `raise` removed from `encode_weather` | No (exit 0) | **all passed** | 8 (included writing the missing test) |
| 4 | Raw CSV overwritten from Bash | No (hook never ran) | **all passed** | 11 (included writing the hash guard) |

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

**Fix:** **5 turns**. The agent removed `+ ["casual"]`. One catch: I committed the fault first, and the agent read
the commit message, which gave away the answer. So it probably had it easier than a real fix. For the later faults,
I ran the fix before committing.

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

**Fix:** **6 turns**. The agent ran the tests, looked at `git diff`, and put `.shift(1)` back before `.rolling()`.

One thing I noticed: the starter test only checks one date, and it quietly skips the check if any day in the week is
missing. That works here, but my new test for `cnt_roll_std_7` fails instead of skipping, which is safer.

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

**Hook stderr:** the hook ran but passed, so the agent got no warning.

```
exit_code: 0
--- stderr ---
(empty)
```

**`make test`:** all passed.

```
python -m pytest tests/ -q
................                                                         [100%]
16 passed in 1.35s
```

**This was the surprise.** The starter tests can't catch this fault at all. The real data only has `GOOD`, `MISTY`
and `BAD` weather, so the error check never runs, and the tests pass whether it's there or not. To test a check for bad
data, you have to give it bad data on purpose.

**Fix (8 turns):** the agent added `test_weather_encoder_rejects_unknown_labels`. It gives the encoder a made-up label,
`"STORM"`, and expects an error. With the broken encoder, it failed:

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

Then it put the `raise` back, and all the tests passed. To make sure the hook now catches this, I broke it again after
adding the test. This time the hook fired:

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

**Change:** I made an edited copy of the data, with the temperature for 2012-07-04 changed from 29.09 to 15.0. Then I
had the agent copy it over `data/raw/bike_daily.csv` using a Bash command.

**What happened.** The tutorial says the `Write(./data/raw/**)` rule doesn't block `cp`. In Claude Code 2.1.332 it
actually did:

```
$ cp bike_daily_fixed.csv data/raw/bike_daily.csv
Permission to use Bash with command cp bike_daily_fixed.csv data/raw/bike_daily.csv has been denied.
```

So this version of Claude Code is a bit smarter than the tutorial says. The main point still holds, though: doing the
same copy through Python went right through, with no block and no hook:

```
$ python -c "import shutil; shutil.copy('bike_daily_fixed.csv', 'data/raw/bike_daily.csv')"
(Bash completed with no output)
```

- **Hook:** never ran. It only watches `Edit` and `Write`, and this was a `Bash` command.
- **Raw file fingerprint (hash):** changed from `a6bed1577f6e4de5...` to `42fa208b2fa85612...`.
- **`make test`:** still passed.

```
.................                                                        [100%]
17 passed in 1.19s
```

Nothing noticed that the data had changed.

**What would catch it:**
- **A hash check on the raw file** (I added this one). It catches any change, no matter how it was made.
- **A `PreToolUse` hook on Bash** that blocks commands mentioning `data/raw/`. But you could get around it by building
  the path in code.
- **A `Stop` hook** that runs `make test`. It only helps if some test can see the change, so it needs the hash check anyway.
- **Making the folder read-only** (`chmod -w data/raw/`). That blocks every kind of write, but the agent could undo it.
- **`git status`**, which would show the file as changed.

**What I added (11 turns):**
- the correct fingerprint, `RAW_SHA256`, in `src/config.py`
- a check in `load_raw()` that refuses to load the data if the fingerprint doesn't match
- a test, `test_raw_data_is_unchanged`

Diff:

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

**`make test` on the changed file, with the check added:**

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

The 14 errors are all the tests that load the data. They all fail with the same error, so `make features` and
`make train` would refuse to run too. Afterwards I put the original file back with `git checkout`. Its fingerprint
starts with `a6bed1577f6e4de5` again, and all tests pass.

---

## Extra: a leaked column renamed to something innocent

The starter test only checks column names. So if someone wrote `out["riders_a"] = out["casual"]`, the leaked column
would get into the model under a new name and every test would pass. I added
`test_no_feature_restates_a_leakage_column`. It looks at the actual numbers and fails if:
- any feature is basically a copy of a leaked column, or
- the features can rebuild `cnt` exactly.

Hook output with `riders_a` added:

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

---

## Extra: the first run of the `/seed-fault` skill

The first time I used my skill, `/seed-fault change cnt_lag_7 to use shift(6) instead of shift(LAG_WARMUP)`, it came
back **Missed**:
- **Hook:** no warning.
- **`make test`:** 19 passed, the same as before.
- **Why:** the starter only tests `cnt_lag_1`, not `cnt_lag_7`.

The skill put the file back. Then I added `test_lag_7_is_a_true_calendar_lag`, and when I broke it again, the hook caught it:

```
--- stderr ---
Leakage tests failed after editing <repo>/src/features.py:
        The 7 is hard-coded on purpose: the feature is built with
        shift(LAG_WARMUP), so deriving the expected offset from config would let
        a changed LAG_WARMUP move the feature and the test together."""
        by_date = feats.set_index("dteday")[TARGET]
        checked = 0
        for date, lag in feats.set_index("dteday").cnt_lag_7.items():
            prev = date - pd.Timedelta(days=7)
            if prev in by_date.index:
>               assert lag == pytest.approx(by_date[prev]), f"bad lag_7 at {date.date()}"
E               AssertionError: bad lag_7 at 2011-01-17
E               assert 1263.0 == 1321.0 ± 0.001321
E                 
E                 comparison failed
E                 Obtained: 1263.0
E                 Expected: 1321.0 ± 0.001321

tests/test_leakage.py:94: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_lag_7_is_a_true_calendar_lag - AssertionEr...
1 failed, 10 passed in 0.37s
```
