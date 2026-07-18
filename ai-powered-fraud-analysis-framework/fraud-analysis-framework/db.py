"""
Database layer for the Fraud Analysis Framework.
Uses SQLite for simplicity - stores raw transactions plus computed
rule-based and ML-based fraud scores for each one.
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "fraud_analysis.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_ref TEXT UNIQUE NOT NULL,
        customer_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        amount REAL NOT NULL,
        merchant_category TEXT NOT NULL,
        card_present INTEGER NOT NULL,
        distance_from_home_km REAL NOT NULL,
        txn_hour INTEGER NOT NULL,
        velocity_last_hour INTEGER NOT NULL,
        is_new_merchant_category INTEGER NOT NULL,

        rule_score REAL,
        rule_flags TEXT,           -- JSON list of triggered rule names
        ml_anomaly_score REAL,     -- normalized 0-100, higher = more anomalous
        final_risk_score REAL,     -- combined 0-100
        risk_level TEXT,           -- Low / Medium / High
        analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS model_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trained_at TEXT DEFAULT CURRENT_TIMESTAMP,
        training_rows INTEGER,
        contamination REAL,
        notes TEXT
    );
    """)
    conn.commit()
    conn.close()


def clear_transactions():
    conn = get_connection()
    conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()


def insert_transactions(rows):
    """rows: list of dicts matching the transactions schema (pre-scoring fields only)"""
    conn = get_connection()
    cur = conn.cursor()
    for r in rows:
        cur.execute("""
            INSERT OR IGNORE INTO transactions
            (transaction_ref, customer_id, timestamp, amount, merchant_category,
             card_present, distance_from_home_km, txn_hour, velocity_last_hour,
             is_new_merchant_category)
            VALUES (:transaction_ref, :customer_id, :timestamp, :amount, :merchant_category,
                    :card_present, :distance_from_home_km, :txn_hour, :velocity_last_hour,
                    :is_new_merchant_category)
        """, r)
    conn.commit()
    conn.close()


def update_scores(scored_rows):
    """scored_rows: list of dicts with transaction_ref + score fields"""
    conn = get_connection()
    cur = conn.cursor()
    for r in scored_rows:
        cur.execute("""
            UPDATE transactions
            SET rule_score = :rule_score,
                rule_flags = :rule_flags,
                ml_anomaly_score = :ml_anomaly_score,
                final_risk_score = :final_risk_score,
                risk_level = :risk_level
            WHERE transaction_ref = :transaction_ref
        """, r)
    conn.commit()
    conn.close()


def get_all_transactions(risk_level=None, limit=500):
    conn = get_connection()
    if risk_level and risk_level != "all":
        rows = conn.execute(
            "SELECT * FROM transactions WHERE risk_level = ? ORDER BY final_risk_score DESC LIMIT ?",
            (risk_level, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY final_risk_score DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transaction(transaction_ref):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM transactions WHERE transaction_ref = ?", (transaction_ref,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) c FROM transactions").fetchone()["c"]
    scored = conn.execute("SELECT COUNT(*) c FROM transactions WHERE final_risk_score IS NOT NULL").fetchone()["c"]
    high = conn.execute("SELECT COUNT(*) c FROM transactions WHERE risk_level = 'High'").fetchone()["c"]
    medium = conn.execute("SELECT COUNT(*) c FROM transactions WHERE risk_level = 'Medium'").fetchone()["c"]
    low = conn.execute("SELECT COUNT(*) c FROM transactions WHERE risk_level = 'Low'").fetchone()["c"]
    avg_score = conn.execute("SELECT AVG(final_risk_score) a FROM transactions WHERE final_risk_score IS NOT NULL").fetchone()["a"]
    total_amount_flagged = conn.execute(
        "SELECT COALESCE(SUM(amount),0) s FROM transactions WHERE risk_level = 'High'"
    ).fetchone()["s"]
    last_run = conn.execute("SELECT * FROM model_runs ORDER BY trained_at DESC LIMIT 1").fetchone()
    conn.close()
    return {
        "total_transactions": total,
        "scored_transactions": scored,
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "avg_risk_score": round(avg_score, 2) if avg_score else 0,
        "total_amount_flagged_high_risk": round(total_amount_flagged, 2),
        "last_model_run": dict(last_run) if last_run else None
    }


def record_model_run(training_rows, contamination, notes=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO model_runs (training_rows, contamination, notes) VALUES (?, ?, ?)",
        (training_rows, contamination, notes)
    )
    conn.commit()
    conn.close()
