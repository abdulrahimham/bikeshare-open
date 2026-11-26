"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train

Exploratory, validation only (never touches reports/metrics.json):
  python -m src.train --target diff  --splits valid
  python -m src.train --target ratio --splits valid
Transforms apply to ridge and hgb; baselines are unchanged. Metrics are
always on the original cnt scale.
"""
import argparse
import json

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, METRICS_TARGET, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


class TargetTransformRegressor(BaseEstimator, RegressorMixin):
    """Fit `estimator` on a target expressed relative to a reference column
    that is known at prediction time, and predict back on the cnt scale.

      diff:  fit y - ref,  predict ref + f(X)
      ratio: fit y / ref,  predict ref * f(X)
    """

    def __init__(self, estimator, mode: str = "diff", reference: str = "cnt_lag_1"):
        self.estimator = estimator
        self.mode = mode
        self.reference = reference

    def _ref(self, X):
        if self.reference not in X.columns:
            raise ValueError(f"target transform needs column {self.reference!r}")
        return X[self.reference].to_numpy(dtype=float)

    def fit(self, X, y):
        ref, y = self._ref(X), pd.Series(y).to_numpy(dtype=float)
        if self.mode == "diff":
            z = y - ref
        elif self.mode == "ratio":
            if (ref <= 0).any():
                raise ValueError(f"ratio target needs {self.reference!r} > 0")
            z = y / ref
        else:
            raise ValueError(f"unknown mode {self.mode!r}")
        self.estimator_ = clone(self.estimator).fit(X, z)
        return self

    def predict(self, X):
        out, ref = self.estimator_.predict(X), self._ref(X)
        return ref + out if self.mode == "diff" else ref * out


# target name -> reference column. Both are shift(1)-built in src.features.
TARGET_REFERENCE = {"diff": "cnt_lag_1", "ratio": "cnt_roll_7"}
TRANSFORMABLE = ("ridge", "hgb")
SPLITS = ("valid", "test")

MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def build_models(target: str = "raw") -> dict:
    """MODELS unchanged for raw; ridge/hgb wrapped for diff/ratio."""
    if target == "raw":
        return MODELS
    ref = TARGET_REFERENCE[target]
    return {
        name: TargetTransformRegressor(clone(m), mode=target, reference=ref)
        if name in TRANSFORMABLE else m
        for name, m in MODELS.items()
    }


def fit_and_score(target: str = "raw", splits=SPLITS) -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    parts = {"valid": valid, "test": test}

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    if target != "raw":
        results["target"] = target
        results["target_reference"] = TARGET_REFERENCE[target]
        results["splits"] = list(splits)
    for name, model in build_models(target).items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in ((s, parts[s]) for s in splits)
        }
    return results


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--target", choices=["raw", *TARGET_REFERENCE], default="raw")
    p.add_argument("--splits", default=",".join(SPLITS),
                   help="comma-separated subset of: valid,test")
    args = p.parse_args(argv)
    args.splits = tuple(s.strip() for s in args.splits.split(",") if s.strip())
    bad = set(args.splits) - set(SPLITS)
    if bad or not args.splits:
        p.error(f"--splits must be a non-empty subset of {SPLITS}, got {args.splits}")
    return args


if __name__ == "__main__":
    args = parse_args()
    res = fit_and_score(args.target, args.splits)
    out = METRICS if args.target == "raw" else METRICS_TARGET.with_name(
        METRICS_TARGET.name.format(name=args.target))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(f"wrote {out.relative_to(out.parents[1])}")
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
