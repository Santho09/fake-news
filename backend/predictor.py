from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple
import json

import joblib

from backend import config
from backend.src.data_processing import TextPreprocessor

# Try to import FactChecker (optional - requires spacy model)
try:
    from backend.src.fact_checker import FactChecker

    FACT_CHECKER_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"Fact Checker not available: {e}")
    FactChecker = None
    FACT_CHECKER_AVAILABLE = False


models: Dict[str, Any] = {}
vectorizer: Any = None
fact_checker: Any = None
model_loaded: bool = False
current_model_name = "Ensemble"
model_weights: Dict[str, float] = {}


def load_all_models() -> bool:
    """
    Load your trained ensemble models + shared TF-IDF vectorizer.
    Kept consistent with the existing `app.py` logic.
    """
    global models, vectorizer, fact_checker, model_loaded, model_weights

    try:
        vectorizer_path = os.path.join(config.MODELS_DIR, "vectorizer.joblib")
        if os.path.exists(vectorizer_path):
            vectorizer = joblib.load(vectorizer_path)
        else:
            print("[WARN] No vectorizer found.")
            return False

        available_models = {
            "Naive Bayes": "naive_bayes_model.joblib",
            "Random Forest": "random_forest_model.joblib",
            "SVM": "svm_model.joblib",
            "Logistic Regression": "logistic_regression_model.joblib",
        }

        models.clear()
        models_loaded = 0
        for model_name, model_file in available_models.items():
            model_path = os.path.join(config.MODELS_DIR, model_file)
            if os.path.exists(model_path):
                models[model_name] = joblib.load(model_path)
                models_loaded += 1
                # Use ASCII only to avoid Windows console encoding issues.
                print(f"[OK] {model_name} model loaded")

        if models_loaded <= 0:
            print("[WARN] No trained models found. Please train models first.")
            return False

        # Optional per-model weights produced by training script.
        # If unavailable, fallback to equal weighting.
        weights_path = os.path.join(config.MODELS_DIR, "model_weights.json")
        model_weights = {}
        if os.path.exists(weights_path):
            try:
                with open(weights_path, "r", encoding="utf-8") as f:
                    raw_weights = json.load(f)
                for model_name in models.keys():
                    w = float(raw_weights.get(model_name, 1.0))
                    model_weights[model_name] = max(0.0, w)
                print("[OK] Loaded model_weights.json")
            except Exception as e:
                print(f"[WARN] Could not load model weights: {e}")
                model_weights = {}

        if not model_weights:
            # Equal weights fallback
            for model_name in models.keys():
                model_weights[model_name] = 1.0

        # Initialize fact checker (optional)
        fact_checker = None
        if FACT_CHECKER_AVAILABLE and FactChecker is not None:
            try:
                google_api_key = config.GOOGLE_FACT_CHECK_API_KEY
                if google_api_key:
                    fact_checker = FactChecker(google_api_key=google_api_key)
                else:
                    fact_checker = FactChecker(google_api_key=None)
                print("[OK] Fact Checker initialized")
            except Exception as e:
                print(f"[WARN] Fact Checker initialization failed: {e}")
                fact_checker = None
        else:
            print("[WARN] Fact Checker not available (spacy not installed)")
            fact_checker = None

        model_loaded = True
        return True
    except Exception as e:
        print(f"Error loading models: {e}")
        return False


model_loaded = load_all_models()


def validate_input(text: str, preprocessor: TextPreprocessor) -> Tuple[bool, str, str]:
    """
    Same input validation rules as your existing Flask app.
    Returns: (is_valid, error_message, warning_message)
    """
    if not text or not text.strip():
        return False, "Please enter some text to analyze.", ""

    if len(text.strip()) < 20:
        return False, "Text is too short. Please enter at least 20 characters of article text.", ""

    url_pattern = r"^(https?://|www\.)\S+$"
    if re.match(url_pattern, text.strip()):
        return False, "Please enter the article text content, not just the URL. Copy the full article text instead.", ""

    english_chars = len(re.findall(r"[a-zA-Z]", text))
    total_chars = len(re.sub(r"\s", "", text))
    if total_chars > 0 and english_chars / total_chars < 0.3:
        return False, "This model only supports English text. Text appears to be in a non-English language.", ""

    preprocessed = preprocessor.preprocess(text)
    if len(preprocessed.strip()) < 10:
        return False, "Text contains insufficient analyzable content after preprocessing. Please provide more meaningful English text.", ""

    warning = ""
    if len(preprocessed.split()) < 5:
        warning = "[WARNING] Very short text detected. Prediction confidence may be low."

    return True, "", warning


def predict_text(*, text: str, fact_check_mode: str = "wikipedia", use_ensemble: bool = True) -> Dict[str, Any]:
    """
    Core prediction path.
    Preserves the ensemble voting + (optional) fact-check override behavior.
    """
    global vectorizer, models, fact_checker, model_weights

    if not model_loaded or vectorizer is None or not models:
        return {"success": False, "error": "Model not loaded. Please train a model first."}

    text = (text or "").strip()
    preprocessor = TextPreprocessor()

    is_valid, error_msg, warning_msg = validate_input(text, preprocessor)
    if not is_valid:
        return {"success": False, "error": error_msg}

    processed_text = preprocessor.preprocess(text)

    text_vectorized = vectorizer.transform([processed_text])

    all_predictions: Dict[str, Any] = {}
    fake_votes = 0
    real_votes = 0
    sum_of_confidences = 0.0
    all_fake_probs = []
    all_real_probs = []
    weighted_fake_sum = 0.0
    weighted_real_sum = 0.0
    total_weight = 0.0

    for model_name, model in models.items():
        prediction = model.predict(text_vectorized)[0]
        prediction_proba = model.predict_proba(text_vectorized)[0]

        # Normalize if unnormalized (kept from app.py)
        if prediction_proba[0] > 1.0 or prediction_proba[1] > 1.0:
            total = prediction_proba[0] + prediction_proba[1]
            prediction_proba = prediction_proba / total if total > 0 else prediction_proba

        # prediction_proba is [prob_class_0, prob_class_1]
        # where class 0 = REAL, class 1 = FAKE
        real_prob = float(prediction_proba[0] * 100)
        fake_prob = float(prediction_proba[1] * 100)

        all_fake_probs.append(fake_prob)
        all_real_probs.append(real_prob)
        model_weight = float(model_weights.get(model_name, 1.0))
        weighted_fake_sum += fake_prob * model_weight
        weighted_real_sum += real_prob * model_weight
        total_weight += model_weight

        all_predictions[model_name] = {
            "prediction": "FAKE NEWS" if prediction == 1 else "REAL NEWS",
            "confidence": fake_prob if prediction == 1 else real_prob,
            "fake_probability": fake_prob,
            "real_probability": real_prob,
            "weight": round(model_weight, 4),
        }

        if prediction == 1:
            fake_votes += 1
            sum_of_confidences += fake_prob
        else:
            real_votes += 1
            sum_of_confidences += real_prob

    num_models = len(models)
    avg_fake_confidence = sum(all_fake_probs) / num_models
    avg_real_confidence = sum(all_real_probs) / num_models
    weighted_fake_confidence = (weighted_fake_sum / total_weight) if total_weight > 0 else avg_fake_confidence
    weighted_real_confidence = (weighted_real_sum / total_weight) if total_weight > 0 else avg_real_confidence

    if fake_votes > 0 and fake_votes == real_votes:
        ensemble_confidence = max(avg_fake_confidence, avg_real_confidence)
    elif fake_votes > real_votes:
        ensemble_confidence = sum_of_confidences / fake_votes
    else:
        ensemble_confidence = sum_of_confidences / real_votes

    # Primary decision: weighted soft-voting (probability-based).
    # Fallback to hard-vote logic if weighted scores are too close.
    prob_gap = abs(weighted_fake_confidence - weighted_real_confidence)
    if weighted_fake_confidence > weighted_real_confidence:
        final_prediction = "FAKE NEWS"
        final_confidence = weighted_fake_confidence
        decision_type = "Weighted Soft Vote"
    elif weighted_real_confidence > weighted_fake_confidence:
        final_prediction = "REAL NEWS"
        final_confidence = weighted_real_confidence
        decision_type = "Weighted Soft Vote"
    else:
        if fake_votes > real_votes:
            final_prediction = "FAKE NEWS"
            final_confidence = ensemble_confidence
            decision_type = "Majority Vote Fallback"
        elif real_votes > fake_votes:
            final_prediction = "REAL NEWS"
            final_confidence = ensemble_confidence
            decision_type = "Majority Vote Fallback"
        else:
            final_prediction = "FAKE NEWS" if avg_fake_confidence > avg_real_confidence else "REAL NEWS"
            final_confidence = max(avg_fake_confidence, avg_real_confidence)
            decision_type = "Tie-Breaker Fallback"

    # Uncertainty thresholding (for safer real-world behavior).
    uncertainty_threshold = float(os.getenv("UNCERTAINTY_CONFIDENCE_THRESHOLD", "60"))
    uncertainty_gap_threshold = float(os.getenv("UNCERTAINTY_GAP_THRESHOLD", "8"))
    is_uncertain = bool(final_confidence < uncertainty_threshold or prob_gap < uncertainty_gap_threshold)
    if is_uncertain:
        final_prediction = "UNCERTAIN"
        decision_type = f"{decision_type} + Uncertainty Threshold"

    result: Dict[str, Any] = {
        "success": True,
        "prediction": final_prediction,
        "confidence": round(float(final_confidence), 2),
        "fake_votes": fake_votes,
        "real_votes": real_votes,
        "decision_type": decision_type,
        "fake_probability": round(float(avg_fake_confidence), 2),
        "real_probability": round(float(avg_real_confidence), 2),
        "weighted_fake_probability": round(float(weighted_fake_confidence), 2),
        "weighted_real_probability": round(float(weighted_real_confidence), 2),
        "is_uncertain": is_uncertain,
        "uncertainty_reason": (
            f"Low confidence/gap (confidence={round(float(final_confidence),2)}%, "
            f"gap={round(float(prob_gap),2)}%)."
            if is_uncertain
            else ""
        ),
        "individual_results": all_predictions,
        "total_models": num_models,
        # For explanation
        "processed_text": processed_text,
    }
    if prob_gap < 6.0:
        result["warning"] = (
            result.get("warning", "") + " " if result.get("warning") else ""
        ) + "[WARNING] Close model scores detected. Treat this result with caution."

    if warning_msg:
        result["warning"] = (
            result.get("warning", "") + " " if result.get("warning") else ""
        ) + warning_msg

    # Optional fact-checking
    if fact_checker is not None:
        try:
            from backend.config import GOOGLE_FACT_CHECK_API_KEY

            if fact_check_mode == "google" and GOOGLE_FACT_CHECK_API_KEY:
                temp_fact_checker = FactChecker(google_api_key=GOOGLE_FACT_CHECK_API_KEY)
                fact_check_result = temp_fact_checker.analyze(text)

                google_checks = fact_check_result.get("google_fact_checks", [])
                if len(google_checks) == 0 and len(fact_check_result.get("warnings", [])) == 0:
                    wikipedia_checker = FactChecker()  # Wikipedia mode
                    fallback_result = wikipedia_checker.analyze(text)

                    fact_check_result["warnings"] = fallback_result.get("warnings", [])
                    fact_check_result["numerical_issues"] = fallback_result.get("numerical_issues", [])
                    fact_check_result["scam_issues"] = fallback_result.get("scam_issues", [])
                    fact_check_result["factual_issues"] = fallback_result.get("factual_issues", [])
                    fact_check_result["verification_results"] = fallback_result.get("verification_results", [])
                    fact_check_result["confidence_adjustment"] = fallback_result.get("confidence_adjustment", 0)
                    fact_check_result["entities"] = fallback_result.get("entities", {})
                    fact_check_result["fallback_used"] = True
            else:
                fact_check_result = fact_checker.analyze(text)

            is_fake: Optional[bool]
            if final_prediction == "UNCERTAIN":
                is_fake = None
            else:
                is_fake = final_prediction == "FAKE NEWS"
            final_verdict = fact_checker.get_verdict(
                ml_prediction=is_fake,
                ml_confidence=float(final_confidence),
                fact_check_result=fact_check_result,
            )

            result["fact_check"] = {
                "entities_found": fact_check_result.get("entities", {}),
                "numerical_issues": fact_check_result.get("numerical_issues", []),
                "verification_results": fact_check_result.get("verification_results", []),
                "warnings": fact_check_result.get("warnings", []),
                "confidence_adjustment": fact_check_result.get("confidence_adjustment", 0),
                "color": final_verdict.get("color", "green"),
                "google_api_enabled": fact_check_result.get("google_api_enabled", False),
                "google_fact_checks": fact_check_result.get("google_fact_checks", []),
                "fallback_used": fact_check_result.get("fallback_used", False),
                "scam_issues": fact_check_result.get("scam_issues", []),
                "factual_issues": fact_check_result.get("factual_issues", []),
                "selected_mode": fact_check_mode,
            }

            result["final_verdict"] = final_verdict.get("verdict")
            result["adjusted_confidence"] = final_verdict.get("adjusted_confidence")
            result["fact_check_reason"] = final_verdict.get("reason")
            result["verdict_color"] = final_verdict.get("color", "green")

        except Exception as fact_error:
            # Prediction still succeeds even if fact-check fails.
            result["fact_check"] = None
            result["fact_check_error"] = str(fact_error)
    else:
        result["fact_check"] = None

    return result

