# Signal Room — AI-Powered Fraud Analysis Framework

A base project for analyzing transactions for potential fraud using a
**hybrid detection approach**: a transparent, explainable rule engine
combined with an unsupervised machine learning anomaly model
(Isolation Forest). The two signals are blended into a single 0–100
risk score per transaction, with a dashboard to review and drill into
flagged cases.

## Why this architecture

Real fraud teams rarely rely on ML alone — pure "black box" scores are
hard to act on or explain to a customer/regulator. This framework pairs:

- **Rule engine** (`fraud_engine/rules.py`) — fast, human-readable checks
  (unusual amount, odd hour, high velocity, location mismatch, card-not-present
  + high amount, unfamiliar merchant category). Every flag that fires is
  visible to the analyst.
- **ML anomaly model** (`fraud_engine/model.py`) — a scikit-learn
  `IsolationForest`, which doesn't need labeled fraud examples. It learns
  what "normal" looks like across the current transaction batch and scores
  how isolated/unusual each point is.
- **Scorer** (`fraud_engine/scorer.py`) — blends both signals 50/50 into
  a final risk score and Low / Medium / High risk level.

## Tech stack
- **Backend:** Python + Flask
- **ML:** scikit-learn (IsolationForest), pandas, numpy
- **Database:** SQLite (single file, no setup)
- **Frontend:** Server-rendered HTML (Jinja2) + vanilla JS dashboard

## Project structure
```
fraud-analysis-framework/
├── app.py                     # Flask app + API routes
├── db.py                      # SQLite schema + queries
├── requirements.txt
├── fraud_engine/
│   ├── rules.py               # Rule-based fraud checks (explainable)
│   ├── model.py                # IsolationForest wrapper (train/score)
│   ├── scorer.py                # Combines rules + ML into final risk score
│   └── data_generator.py        # Synthetic transaction generator for demos
├── models/                     # Trained model file is saved here (.joblib)
├── data/                        # (place your own CSVs here if useful)
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    ├── index.html               # Dashboard: stats + transaction ledger
    ├── upload.html               # Generate sample data / upload CSV
    └── transaction_detail.html    # Full risk breakdown for one transaction
```

## Getting started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   python app.py
   ```

3. Open **http://localhost:5000**

4. On the "Load data" page, click **Generate & analyze** to create a batch
   of synthetic transactions (with a small % of injected fraud-like
   outliers) and see the framework score them immediately — no setup needed.

## Using your own data

Upload a CSV with these columns from the "Load data" page (a template is
downloadable there too):

```
transaction_ref, customer_id, timestamp, amount, merchant_category,
card_present, distance_from_home_km, txn_hour, velocity_last_hour,
is_new_merchant_category
```

`card_present` and `is_new_merchant_category` are 0/1 flags. If you don't
have real values for `distance_from_home_km` or `velocity_last_hour`,
approximate them (or set to 0) — the rule engine and ML model will still run,
just with less signal on those specific checks.

## Tuning the framework

- **Rule weights/thresholds** — edit `fraud_engine/rules.py`. Each rule is
  a small function decorated with `@rule(weight, label)`; add, remove, or
  reweight freely.
- **Blend ratio** — `RULE_WEIGHT` / `ML_WEIGHT` in `fraud_engine/scorer.py`
  (defaults to 50/50).
- **Risk thresholds** — `HIGH_THRESHOLD` / `MEDIUM_THRESHOLD` in
  `fraud_engine/scorer.py` (defaults: ≥70 High, ≥40 Medium, else Low).
- **Contamination** — the expected fraud rate passed to IsolationForest;
  set this close to your real-world fraud base rate for best results.

## Extending this base project
- Swap IsolationForest for a supervised model (e.g. XGBoost) once you have
  labeled fraud/not-fraud outcomes to train on.
- Add a feedback loop: let analysts mark a flagged transaction as
  "confirmed fraud" or "false positive" and store that for future retraining.
- Add authentication so only authorized analysts can view the dashboard.
- Add batch/scheduled scoring (e.g. via a cron job or task queue) for
  live transaction streams instead of manual generate/upload.
- Add per-customer historical baselines instead of the synthetic profile
  approach used in the demo data generator.

## Important note on scope

This is a **base/demo framework** to build on, not a production fraud
system. Real deployments need: real transaction data (not synthetic),
proper model validation against labeled outcomes, monitoring for model
drift, and a compliance/audit review appropriate to your jurisdiction
and industry (e.g. PCI-DSS if handling card data).
