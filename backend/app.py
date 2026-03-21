from __future__ import annotations

import os
import json
from typing import Any, Dict

from flask import Flask, jsonify
from flask_cors import CORS

from backend import config
from backend.auth import create_access_token, hash_password, require_auth, verify_password
from backend.db import AppDB
from backend.explainability import generate_human_explanation
from backend.predictor import predict_text
import backend.predictor as predictor_module


APP_TITLE = "NewsVeritas"

app = Flask(__name__)
app.json.sort_keys = False

# Keep CORS aligned with your React dev server
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip()
CORS(app, resources={r"/api/*": {"origins": _frontend_origin}}, supports_credentials=True)


def _get_db() -> AppDB:
    # Lazy init so missing env doesn't crash module import immediately.
    if not hasattr(app, "_db"):
        app._db = AppDB()  # type: ignore[attr-defined]
    return app._db  # type: ignore[attr-defined]


@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "healthy", "service": APP_TITLE})


@app.post("/api/auth/signup")
def signup() -> Any:
    """
    Signup for BOTH admin and user.
    - Normal users can create only `role='user'`
    - Admin role requires `ADMIN_SIGNUP_CODE` match (safer by default)
    """
    # Use flask request safely
    from flask import request

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    role_requested = (body.get("role") or "user").strip().lower()
    admin_code = (body.get("admin_code") or "").strip()

    if not username:
        return jsonify({"success": False, "error": "Username is required"}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required"}), 400

    if role_requested not in {"admin", "user"}:
        role_requested = "user"

    if role_requested == "admin":
        expected = os.getenv("ADMIN_SIGNUP_CODE", "").strip()
        if not expected:
            return jsonify({"success": False, "error": "Admin signup is disabled. Set ADMIN_SIGNUP_CODE in backend/.env"}), 403
        if not admin_code or admin_code != expected:
            return jsonify({"success": False, "error": "Invalid admin_code"}), 403

    try:
        password_hash = hash_password(password)
        db = _get_db()

        existing = db.find_user_by_username(username)
        if existing:
            return jsonify({"success": False, "error": "Username already exists"}), 409

        user_id = db.create_user(
            username=username, password_hash=password_hash, role=role_requested
        )

        token = create_access_token(user_id=user_id, username=username, role=role_requested)
        return jsonify({"success": True, "token": token, "role": role_requested})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.post("/api/auth/login")
def login() -> Any:
    from flask import request

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required"}), 400

    try:
        db = _get_db()
        user = db.find_user_by_username(username)
        if not user:
            return jsonify({"success": False, "error": "Invalid credentials"}), 401

        if not verify_password(password, user["password_hash"]):
            return jsonify({"success": False, "error": "Invalid credentials"}), 401

        token = create_access_token(
            user_id=str(user["_id"]),
            username=user["username"],
            role=user["role"],
        )
        return jsonify({"success": True, "token": token, "role": user["role"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.get("/api/auth/me")
@require_auth()
def me() -> Any:
    from flask import g

    return jsonify({"success": True, "user": {"id": g.user["id"], "username": g.user["username"], "role": g.user["role"]}})


@app.post("/api/predict")
@require_auth()
def predict() -> Any:
    from flask import g
    from flask import request

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    fact_check_mode = (body.get("fact_check_mode") or "wikipedia").strip().lower()
    if fact_check_mode not in {"wikipedia", "google"}:
        fact_check_mode = "wikipedia"

    try:
        pred = predict_text(text=text, fact_check_mode=fact_check_mode)
        if not pred.get("success"):
            return jsonify(pred), 400

        processed_text = pred.get("processed_text", "")
        fact_check_result = pred.get("fact_check")

        explanation = generate_human_explanation(
            text_raw=text,
            processed_text=processed_text,
            ensemble_result=pred,
            models=predictor_module.models,  # reuse loaded models
            vectorizer=predictor_module.vectorizer,
            fact_check_result=fact_check_result,
        )

        pred["explanation"] = explanation
        # Don't store processed_text if you prefer; keeping for future re-analysis.
        pred.pop("processed_text", None)

        db = _get_db()
        user_id = g.user["id"]
        submission_payload = {
            "text": text,
            "fact_check_mode": fact_check_mode,
            "ml_input_processed": processed_text,
            "verdict": (pred.get("final_verdict") or pred.get("prediction")),
            "verdict_color": pred.get("verdict_color"),
            "confidence": pred.get("adjusted_confidence") if pred.get("final_verdict") else pred.get("confidence"),
            "ml_confidence": pred.get("confidence"),
            "prediction": pred.get("prediction"),
            "fake_votes": pred.get("fake_votes"),
            "real_votes": pred.get("real_votes"),
            "individual_results": pred.get("individual_results"),
            "decision_type": pred.get("decision_type"),
            "explanation": explanation,
            "fact_check": pred.get("fact_check"),
            # timestamps come from db
        }
        db.add_submission(user_id=user_id, payload=submission_payload)

        return jsonify(pred)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/api/history")
@require_auth()
def history() -> Any:
    from flask import g

    db = _get_db()
    submissions = db.get_submissions_for_user(g.user["id"], limit=50)
    return jsonify({"success": True, "submissions": submissions})


@app.get("/api/admin/overview")
@require_auth(expected_roles=("admin",))
def admin_overview() -> Any:
    db = _get_db()
    return jsonify({"success": True, "overview": db.get_admin_overview(limit=20)})


@app.get("/api/admin/users")
@require_auth(expected_roles=("admin",))
def admin_users() -> Any:
    db = _get_db()
    return jsonify({"success": True, "users": db.get_admin_users(limit=200)})


@app.get("/api/admin/submissions")
@require_auth(expected_roles=("admin",))
def admin_submissions() -> Any:
    db = _get_db()
    subs = db.get_recent_submissions_admin(limit=50)
    return jsonify({"success": True, "submissions": subs})


@app.get("/api/admin/model-metrics")
@require_auth(expected_roles=("admin",))
def admin_model_metrics() -> Any:
    metrics_path = os.path.join(config.MODELS_DIR, "model_metrics.json")
    if not os.path.exists(metrics_path):
        return jsonify(
            {
                "success": False,
                "error": "model_metrics.json not found. Run retraining first.",
            }
        ), 404

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        return jsonify({"success": True, "metrics": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)

