"""Train the annual probability model and keep future outcomes outside the feature table."""
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from data_pipeline import FEATURES, KEY

HORIZON = 12
RF_MONTHLY = 0.001


def build_labels(monthly):
    history = monthly.sort_values(["security_id", "signal_eom"]).copy()
    excess = history.monthly_return - RF_MONTHLY
    by_security = excess.groupby(history.security_id)
    # A window ending at t+12 contains exactly months t+1 through t+12.
    mean = by_security.transform(lambda r: r.rolling(HORIZON).mean().shift(-HORIZON))
    sd = by_security.transform(lambda r: r.rolling(HORIZON).std(ddof=1).shift(-HORIZON))
    sharpe = np.sqrt(12) * mean / sd.where(sd > 1e-12)
    labels = history[KEY].copy()
    labels["target"] = (sharpe >= 0.5).where(sharpe.notna()).astype("Int64")
    labels["label_end"] = (history.signal_eom + pd.offsets.MonthEnd(HORIZON)).where(sharpe.notna())
    return labels


def annual_predictions(panel, labels):
    # Eligibility and cross-sectional ranks are set with signal-month observations only.
    ok = panel.market_cap.gt(0) & panel[FEATURES].notna().sum(axis=1).ge(3)
    frame = panel.loc[ok].merge(labels, on=KEY, how="left", validate="one_to_one").reset_index(drop=True)
    feature_values = frame[FEATURES].fillna(frame.groupby("signal_eom")[FEATURES].transform("median"))
    X = 2 * feature_values.groupby(frame.signal_eom).rank(pct=True) - 1
    X = X.fillna(0.0)  # Neutral rank if a whole cross-section is missing this characteristic.
    fits, predictions = [], []
    for year, test in frame.groupby(frame.effective_date.dt.year, sort=True):
        cutoff = pd.Timestamp(year - 1, 12, 31)
        train = (frame.label_end.between(pd.Timestamp(year - 10, 1, 1), cutoff)
                 & frame.signal_eom.lt(cutoff) & frame.target.notna())
        y = frame.loc[train, "target"].astype(int)
        train_months = frame.loc[train, "signal_eom"].nunique()
        ready = train_months >= 24 and y.nunique() == 2
        fits.append({"model_year": year, "training_cutoff": cutoff, "train_rows": int(train.sum()),
                     "train_months": train_months, "last_label_end": frame.loc[train, "label_end"].max(),
                     "status": "trained" if ready else "warmup"})
        if not ready:
            continue
        estimator = make_pipeline(StandardScaler(), XGBClassifier(n_estimators=40, max_depth=2,
            learning_rate=0.08, min_child_weight=3, n_jobs=1, random_state=23, tree_method="hist",
            objective="binary:logistic", eval_metric="logloss"))
        estimator.fit(X.loc[train], y)
        result = test[[*KEY, "signal_eom", "market_cap"]].copy()
        result["model_year"] = year
        result["probability"] = estimator.predict_proba(X.loc[test.index])[:, 1]
        predictions.append(result)
    if not predictions:
        raise ValueError("Insufficient matured history for the first annual fit (24 signal months and two classes).")
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(fits)
