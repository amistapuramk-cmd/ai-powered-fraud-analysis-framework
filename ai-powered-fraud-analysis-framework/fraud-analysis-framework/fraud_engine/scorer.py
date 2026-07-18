"""
Combines the rule-based engine and the ML anomaly model into a single
final risk score and risk level per transaction.

final_risk_score = (RULE_WEIGHT * rule_score) + (ML_WEIGHT * ml_anomaly_score)

Both inputs are already normalized 0-100, so the blend stays 0-100.
Weights are tunable - defaulting to an even split so neither the
transparent rules nor the ML model dominates the decision.
"""
from fraud_engine import rules, model as ml_model

RULE_WEIGHT = 0.5
ML_WEIGHT = 0.5

HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 40


def risk_level_for(score):
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def score_batch(transactions, train_fresh_model=True, contamination=0.06):
    """
    transactions: list of transaction dicts (as stored in the DB, pre-scoring)
    Returns a list of dicts with transaction_ref + all score fields, ready
    for db.update_scores().
    """
    if train_fresh_model:
        ml_model.train_model(transactions, contamination=contamination)

    ml_scores = ml_model.score_transactions(transactions)

    results = []
    for txn, ml_score in zip(transactions, ml_scores):
        rule_score, triggered_labels = rules.evaluate(txn)
        final_score = round(RULE_WEIGHT * rule_score + ML_WEIGHT * ml_score, 2)

        results.append({
            "transaction_ref": txn["transaction_ref"],
            "rule_score": rule_score,
            "rule_flags": __import__("json").dumps(triggered_labels),
            "ml_anomaly_score": ml_score,
            "final_risk_score": final_score,
            "risk_level": risk_level_for(final_score),
        })

    return results
