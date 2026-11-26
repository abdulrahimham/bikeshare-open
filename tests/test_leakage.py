"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import numpy as np
import pandas as pd
import pytest

from src.config import FORBIDDEN, LEAKAGE_COLS, TARGET
from src.features import build_features, encode_weather, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


def test_no_feature_restates_a_leakage_column(feats):
    """Catches leakage from the *data*, not from names.

    test_no_forbidden_features only checks names, and feature_columns() is a
    denylist, so `out["riders_a"] = out["casual"]` sails straight through it.
    This fails if any feature is an affine copy of a LEAKAGE_COLS column, or
    if the features jointly reproduce the target exactly (e.g. casual and
    registered both smuggled in under new names: their sum *is* cnt).
    """
    cols = feature_columns(feats)
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
    assert not restated, f"features that restate a leakage column: {restated}"

    # 2. All features plus an intercept must not reproduce the target exactly.
    A = np.column_stack([np.ones(len(X)), X.to_numpy()])
    y = feats[TARGET].astype(float).to_numpy()
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    max_resid = np.abs(y - A @ coef).max()
    assert max_resid >= 1e-6, (
        f"features reproduce {TARGET} exactly by least squares "
        f"(max |residual| = {max_resid:.2e}): some combination of feature "
        "columns is an arithmetic identity for the target"
    )


def test_lags_are_true_calendar_lags(feats):
    """cnt_lag_1 for date d must equal cnt on d-1, in calendar days."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_1.items():
        prev = date - pd.Timedelta(days=1)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


def test_rolling_mean_excludes_today(feats):
    """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
    by_date = feats.set_index("dteday")[TARGET]
    date = feats.dteday.iloc[200]
    window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
    if all(d in by_date.index for d in window):
        expected = sum(by_date[d] for d in window) / 7
        assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)


def test_rolling_std_excludes_today(feats):
    """cnt_roll_std_7 must be the sample std (ddof=1) of the 7 calendar days
    *before* today, never including today's count."""
    import statistics

    by_date = feats.set_index("dteday")[TARGET]
    date = pd.Timestamp("2011-08-01")
    window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
    # Fail, don't skip, if the window is incomplete: a silent skip verifies nothing.
    assert date in by_date.index and all(d in by_date.index for d in window)
    expected = statistics.stdev(by_date[d] for d in window)
    assert "cnt_roll_std_7" in feats.columns, "cnt_roll_std_7 not built"
    assert feats.set_index("dteday").cnt_roll_std_7[date] == pytest.approx(expected)


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique


def test_weather_encoder_rejects_unknown_labels():
    """The real data only holds GOOD/MISTY/BAD, so no data-driven test can
    see a missing guard. An unseen label must raise, not silently become NaN
    and get dropped by dropna()."""
    with pytest.raises(ValueError):
        encode_weather(pd.Series(["GOOD", "STORM", "BAD"]))
