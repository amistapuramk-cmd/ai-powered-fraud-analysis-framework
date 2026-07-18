"""
Rule-based fraud detection engine.

Each rule inspects a single transaction (as a dict/row) and returns a
(triggered: bool, weight: float, label: str) tuple. Weights are summed
and normalized to a 0-100 "rule_score" so it can be blended with the
ML anomaly score downstream.

Rules are intentionally simple and transparent (this is the "explainable"
half of the framework) - each flag is human-readable so analysts can see
exactly why a transaction was scored the way it was.
"""

RULES = []


def rule(weight, label):
    """Decorator to register a rule function with its weight and label."""
    def decorator(fn):
        RULES.append((fn, weight, label))
        return fn
    return decorator


@rule(weight=25, label="Unusually large amount")
def high_amount(txn):
    return txn["amount"] > 800


@rule(weight=15, label="Odd-hour transaction (12am-5am)")
def odd_hour(txn):
    return txn["txn_hour"] in (0, 1, 2, 3, 4)


@rule(weight=20, label="High transaction velocity (rapid repeat charges)")
def high_velocity(txn):
    return txn["velocity_last_hour"] >= 4


@rule(weight=20, label="Far from customer's home location")
def location_mismatch(txn):
    return txn["distance_from_home_km"] > 250


@rule(weight=15, label="Card-not-present with high amount")
def card_not_present_high_amount(txn):
    return txn["card_present"] == 0 and txn["amount"] > 300


@rule(weight=10, label="Unfamiliar merchant category for this customer")
def new_merchant_category(txn):
    return txn["is_new_merchant_category"] == 1


MAX_POSSIBLE_WEIGHT = sum(w for _, w, _ in RULES)


def evaluate(txn):
    """
    Runs all registered rules against a transaction dict.
    Returns (rule_score_0_100, list_of_triggered_labels)
    """
    triggered_weight = 0
    triggered_labels = []
    for fn, weight, label in RULES:
        try:
            if fn(txn):
                triggered_weight += weight
                triggered_labels.append(label)
        except KeyError:
            # Missing field for this rule - skip rather than crash the batch
            continue

    rule_score = round((triggered_weight / MAX_POSSIBLE_WEIGHT) * 100, 2) if MAX_POSSIBLE_WEIGHT else 0
    return rule_score, triggered_labels
