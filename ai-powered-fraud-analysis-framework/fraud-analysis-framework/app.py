"""
AI-Powered Fraud Analysis Framework
Flask application entry point - API routes + dashboard serving.
"""
import io
import csv
import json
from flask import Flask, jsonify, request, render_template

import db
from fraud_engine import data_generator, scorer

app = Flask(__name__)

REQUIRED_CSV_COLUMNS = [
    "transaction_ref", "customer_id", "timestamp", "amount", "merchant_category",
    "card_present", "distance_from_home_km", "txn_hour", "velocity_last_hour",
    "is_new_merchant_category"
]


# ---------------------------------------------------------------------------
# Page routes (dashboard UI)
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/upload")
def upload_page():
    return render_template("upload.html")


@app.route("/transaction/<ref>")
def transaction_detail_page(ref):
    return render_template("transaction_detail.html", ref=ref)


# ---------------------------------------------------------------------------
# API: sample data generation + analysis
# ---------------------------------------------------------------------------
@app.route("/api/transactions/generate-sample", methods=["POST"])
def generate_sample():
    body = request.get_json(silent=True) or {}
    n = int(body.get("count", 500))
    fraud_ratio = float(body.get("fraud_ratio", 0.06))
    n = max(20, min(n, 5000))
    fraud_ratio = max(0.0, min(fraud_ratio, 0.5))

    db.clear_transactions()
    rows = data_generator.generate_transactions(n=n, fraud_ratio=fraud_ratio)
    db.insert_transactions(rows)

    scored = scorer.score_batch(rows, train_fresh_model=True, contamination=fraud_ratio)
    db.update_scores(scored)
    db.record_model_run(len(rows), fraud_ratio, notes="Trained on generated sample batch")

    return jsonify({"message": f"Generated and analyzed {len(rows)} transactions.", "count": len(rows)})


@app.route("/api/transactions/upload", methods=["POST"])
def upload_transactions():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Attach a CSV under field name 'file'."}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only .csv files are supported."}), 400

    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        return jsonify({"error": f"CSV is missing required columns: {', '.join(missing)}"}), 400

    rows = []
    for r in reader:
        try:
            rows.append({
                "transaction_ref": r["transaction_ref"],
                "customer_id": r["customer_id"],
                "timestamp": r["timestamp"],
                "amount": float(r["amount"]),
                "merchant_category": r["merchant_category"],
                "card_present": int(r["card_present"]),
                "distance_from_home_km": float(r["distance_from_home_km"]),
                "txn_hour": int(r["txn_hour"]),
                "velocity_last_hour": int(r["velocity_last_hour"]),
                "is_new_merchant_category": int(r["is_new_merchant_category"]),
            })
        except (ValueError, KeyError) as e:
            return jsonify({"error": f"Malformed row for transaction_ref={r.get('transaction_ref')}: {e}"}), 400

    if not rows:
        return jsonify({"error": "CSV contained no data rows."}), 400

    db.clear_transactions()
    db.insert_transactions(rows)

    contamination = float(request.form.get("contamination", 0.06))
    scored = scorer.score_batch(rows, train_fresh_model=True, contamination=contamination)
    db.update_scores(scored)
    db.record_model_run(len(rows), contamination, notes=f"Trained on uploaded file: {file.filename}")

    return jsonify({"message": f"Uploaded and analyzed {len(rows)} transactions.", "count": len(rows)})


@app.route("/api/transactions/rescore", methods=["POST"])
def rescore():
    """Re-runs scoring on whatever transactions are currently stored,
    without regenerating/re-uploading data. Useful after tuning rules."""
    rows = db.get_all_transactions(limit=100000)
    if not rows:
        return jsonify({"error": "No transactions loaded yet."}), 400

    body = request.get_json(silent=True) or {}
    contamination = float(body.get("contamination", 0.06))
    train_fresh = bool(body.get("retrain_model", True))

    scored = scorer.score_batch(rows, train_fresh_model=train_fresh, contamination=contamination)
    db.update_scores(scored)
    if train_fresh:
        db.record_model_run(len(rows), contamination, notes="Rescored with retrained model")

    return jsonify({"message": f"Rescored {len(rows)} transactions."})


# ---------------------------------------------------------------------------
# API: read endpoints
# ---------------------------------------------------------------------------
@app.route("/api/transactions", methods=["GET"])
def list_transactions():
    risk_level = request.args.get("risk_level", "all")
    limit = int(request.args.get("limit", 500))
    rows = db.get_all_transactions(risk_level=risk_level, limit=limit)
    for r in rows:
        r["rule_flags"] = json.loads(r["rule_flags"]) if r.get("rule_flags") else []
    return jsonify({"transactions": rows})


@app.route("/api/transactions/<ref>", methods=["GET"])
def transaction_detail(ref):
    row = db.get_transaction(ref)
    if not row:
        return jsonify({"error": "Transaction not found"}), 404
    row["rule_flags"] = json.loads(row["rule_flags"]) if row.get("rule_flags") else []
    return jsonify({"transaction": row})


@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(db.get_stats())


@app.route("/api/sample-csv-template", methods=["GET"])
def sample_csv_template():
    """Returns a small example CSV so users know the expected upload format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(REQUIRED_CSV_COLUMNS)
    writer.writerow(["TXN-EXAMPLE01", "CUST-1000", "2026-07-18 14:32:00", "45.50",
                      "Grocery", "1", "3.2", "14", "1", "0"])
    csv_data = output.getvalue()
    return app.response_class(csv_data, mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=transaction_template.csv"
    })


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
