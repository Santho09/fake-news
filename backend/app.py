from __future__ import annotations

import os
import json
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, cast

from flask import Flask, jsonify
from flask_cors import CORS

from backend import config
from backend.auth import create_access_token, hash_password, require_auth, verify_password
from backend.db import AppDB
from backend.email_service import send_password_reset_email, smtp_is_configured
from backend.explainability import generate_human_explanation
from backend.predictor import predict_text
import backend.predictor as predictor_module


APP_TITLE = "NewsVeritas"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    role_requested = (body.get("role") or "user").strip().lower()
    admin_code = (body.get("admin_code") or "").strip()

    if not username:
        return jsonify({"success": False, "error": "Username is required"}), 400
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "Please enter a valid email"}), 400
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
        existing_email = db.find_user_by_email(email)
        if existing_email:
            return jsonify({"success": False, "error": "Email already exists"}), 409

        user_id = db.create_user(
            username=username, email=email, password_hash=password_hash, role=role_requested
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


@app.post("/api/auth/forgot-password")
def forgot_password() -> Any:
    from flask import request

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "Please enter a valid email"}), 400

    db = _get_db()
    user = db.find_user_by_email(email)

    # Always return success to avoid account enumeration.
    if not user:
        return jsonify({"success": True, "message": "If this email exists, a reset link has been sent."})

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(minutes=int(os.getenv("RESET_TOKEN_EXPIRES_MINUTES", "30")))
    db.save_password_reset_token(user_id=str(user["_id"]), token_hash=token_hash, expires_at=expires_at)

    frontend_base = os.getenv("FRONTEND_RESET_URL", os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")).rstrip("/")
    reset_url = f"{frontend_base}/reset-password?token={raw_token}"

    if smtp_is_configured():
        try:
            send_password_reset_email(to_email=email, reset_url=reset_url)
        except Exception:
            # Don't leak SMTP internals to client.
            pass

    return jsonify({"success": True, "message": "If this email exists, a reset link has been sent."})


@app.post("/api/auth/reset-password")
def reset_password() -> Any:
    from flask import request

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    token = (body.get("token") or "").strip()
    new_password = body.get("new_password") or ""

    if not token:
        return jsonify({"success": False, "error": "Reset token is required"}), 400
    if not new_password:
        return jsonify({"success": False, "error": "New password is required"}), 400

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db = _get_db()
    reset_doc = db.find_valid_password_reset_by_hash(token_hash)
    if not reset_doc:
        return jsonify({"success": False, "error": "Reset link is invalid or expired"}), 400

    try:
        password_hash = hash_password(new_password)
        db.update_user_password(reset_doc["user_id"], password_hash)
        db.mark_password_reset_used(reset_doc["_id"])
        return jsonify({"success": True, "message": "Password reset successful. Please sign in."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


def _resolve_input_text(request) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Resolve text from request: JSON (text / url / rss_url) or multipart (file).
    Returns (text, error, input_meta). input_meta may include input_type, feed fields, etc.
    """
    meta: Dict[str, Any] = {}

    if request.content_type and "multipart/form-data" in request.content_type:
        f = request.files.get("file")
        if not f or not f.filename:
            return "", "No file uploaded.", meta
        if not f.filename.lower().endswith(".txt"):
            return "", "Only .txt files are supported.", meta
        try:
            raw = f.read()
            text = raw.decode("utf-8", errors="replace").strip()
        except Exception as e:
            return "", f"Could not read file: {str(e)[:60]}", meta
        if len(text) < 20:
            return "", "File content is too short. Use at least 20 characters.", meta
        meta["input_type"] = "file"
        meta["filename"] = f.filename
        return text, None, meta

    body: Dict[str, Any] = cast(Dict[str, Any], request.get_json(silent=True) or {})
    text = (body.get("text") or "").strip()
    url = (body.get("url") or "").strip()
    rss_url = (body.get("rss_url") or "").strip()
    youtube_url = (body.get("youtube_url") or "").strip()

    if rss_url and not text:
        from backend.src.rss_fetcher import text_from_rss_feed

        t, err, rss_meta = text_from_rss_feed(rss_url)
        if err:
            return "", err, meta
        meta.update({"input_type": "rss", "rss_feed_url": rss_url, **rss_meta})
        return t or "", None, meta

    if youtube_url and not text:
        from backend.src.youtube_fetcher import fetch_video_text

        t, err, yt_meta = fetch_video_text(youtube_url)
        if err:
            return "", err, meta
        meta.update({"input_type": "youtube", "youtube_url": youtube_url, **yt_meta})
        return t or "", None, meta

    if url and not text:
        from backend.src.article_fetcher import fetch_article_text

        t, err = fetch_article_text(url)
        if err:
            return "", err, meta
        meta["input_type"] = "url"
        meta["article_url"] = url
        return t or "", None, meta

    if text:
        meta["input_type"] = "text"
        return text, None, meta

    return "", "Please provide article text, a URL, a YouTube video URL, an RSS feed URL, or upload a .txt file.", meta


@app.post("/api/predict")
@require_auth()
def predict() -> Any:
    from flask import g
    from flask import request

    text, input_error, input_meta = _resolve_input_text(request)
    if input_error:
        return jsonify({"success": False, "error": input_error}), 400

    fact_check_mode = "wikipedia"
    if request.content_type and "multipart/form-data" in request.content_type:
        fact_check_mode = (request.form.get("fact_check_mode") or "wikipedia").strip().lower()
    else:
        body: Dict[str, Any] = request.get_json(silent=True) or {}
        fact_check_mode = (body.get("fact_check_mode") or "wikipedia").strip().lower()
    if fact_check_mode not in {"wikipedia", "google"}:
        fact_check_mode = "wikipedia"

    try:
        is_short = input_meta.get("input_type") == "youtube"
        pred = predict_text(text=text, fact_check_mode=fact_check_mode, is_short_text=is_short)
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
        pred["analyzed_text"] = text
        pred["input_meta"] = input_meta
        # Don't store processed_text if you prefer; keeping for future re-analysis.
        pred.pop("processed_text", None)

        db = _get_db()
        user_id = g.user["id"]
        submission_payload = {
            "text": text,
            "input_meta": input_meta,
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


@app.get("/api/admin/user-analytics")
@require_auth(expected_roles=("admin",))
def admin_user_analytics() -> Any:
    """Per-user submission analytics for the operations console."""
    db = _get_db()
    users = db.get_admin_user_analytics(limit_users=400)
    return jsonify({"success": True, "users": users})


@app.get("/api/admin/users/<user_id>/submissions")
@require_auth(expected_roles=("admin",))
def admin_user_submissions(user_id: str) -> Any:
    from flask import request

    try:
        limit = int(request.args.get("limit", "2000"))
    except ValueError:
        limit = 2000
    limit = max(1, min(limit, 10000))

    db = _get_db()
    user = db.find_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    uid = str(user["_id"])
    total_matching = db.submissions.count_documents({"user_id": uid})
    subs = db.get_submissions_for_user(uid, limit=limit)
    safe_user = {
        "id": uid,
        "username": user.get("username"),
        "role": user.get("role"),
        "created_at": user["created_at"].isoformat() + "Z"
        if isinstance(user.get("created_at"), datetime)
        else user.get("created_at"),
    }
    return jsonify(
        {
            "success": True,
            "user": safe_user,
            "submissions": subs,
            "submission_meta": {
                "total_in_database": total_matching,
                "returned": len(subs),
                "limit_applied": limit,
                "truncated": total_matching > len(subs),
            },
        }
    )


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

