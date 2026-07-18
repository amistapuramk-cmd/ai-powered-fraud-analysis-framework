"""
Generates realistic synthetic transaction data for demo/testing purposes,
with a small injected percentage of "fraud-like" outlier transactions so
the framework has something interesting to detect.
"""
import random
import uuid
from datetime import datetime, timedelta

MERCHANT_CATEGORIES = [
    "Grocery", "Electronics", "Dining", "Travel", "Fuel",
    "Online Retail", "Entertainment", "Pharmacy", "Utilities", "Jewelry"
]

NUM_CUSTOMERS_DEFAULT = 40


def _random_timestamp(days_back=30):
    now = datetime.now()
    delta = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    return now - delta


def generate_transactions(n=500, fraud_ratio=0.06, num_customers=NUM_CUSTOMERS_DEFAULT, seed=None):
    """Returns a list of transaction dicts ready for db.insert_transactions()."""
    if seed is not None:
        random.seed(seed)

    customer_ids = [f"CUST-{1000+i}" for i in range(num_customers)]
    # Give each customer a "home" spending profile so anomalies are relative
    customer_profiles = {
        cid: {
            "avg_amount": random.uniform(20, 150),
            "usual_categories": random.sample(MERCHANT_CATEGORIES, k=random.randint(2, 4))
        }
        for cid in customer_ids
    }

    rows = []
    n_fraud = int(n * fraud_ratio)
    fraud_indices = set(random.sample(range(n), n_fraud)) if n_fraud > 0 else set()

    for i in range(n):
        customer_id = random.choice(customer_ids)
        profile = customer_profiles[customer_id]
        ts = _random_timestamp()
        is_fraud_like = i in fraud_indices

        if is_fraud_like:
            # Simulate classic fraud patterns: unusually large amount,
            # odd hour, far from home, card-not-present, unfamiliar merchant,
            # and a burst of rapid transactions (high velocity).
            amount = round(profile["avg_amount"] * random.uniform(6, 20) + random.uniform(50, 400), 2)
            txn_hour = random.choice([1, 2, 3, 4, 23])
            distance_from_home = round(random.uniform(300, 5000), 1)
            card_present = 0
            merchant_category = random.choice(
                [c for c in MERCHANT_CATEGORIES if c not in profile["usual_categories"]] or MERCHANT_CATEGORIES
            )
            velocity = random.randint(4, 12)
            is_new_category = 1
        else:
            amount = round(max(2, random.gauss(profile["avg_amount"], profile["avg_amount"] * 0.35)), 2)
            txn_hour = ts.hour
            distance_from_home = round(random.uniform(0, 40), 1)
            card_present = random.choice([1, 1, 1, 0])
            merchant_category = random.choice(profile["usual_categories"])
            velocity = random.randint(0, 2)
            is_new_category = 0

        rows.append({
            "transaction_ref": f"TXN-{uuid.uuid4().hex[:10].upper()}",
            "customer_id": customer_id,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "merchant_category": merchant_category,
            "card_present": card_present,
            "distance_from_home_km": distance_from_home,
            "txn_hour": txn_hour,
            "velocity_last_hour": velocity,
            "is_new_merchant_category": is_new_category
        })

    return rows
