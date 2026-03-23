"""
SHAP LinearExplainer for the calibrated Logistic Regression path.
Requires models/shap_background.joblib (from training or build_shap_background).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend import config


def _unwrap_lr(model: Any) -> Any:
    if hasattr(model, "coef_") and model.coef_ is not None:
        return model
    if hasattr(model, "calibrated_classifiers_") and model.calibrated_classifiers_:
        base = model.calibrated_classifiers_[0]
        inner = getattr(base, "estimator", None) or getattr(base, "base_estimator", base)
        if inner is not None and hasattr(inner, "coef_") and inner.coef_ is not None:
            return inner
    return None


def shap_background_path() -> str:
    return os.path.join(config.MODELS_DIR, "shap_background.joblib")


_bg_cache: Optional[Any] = None
_bg_mtime: Optional[float] = None

_explainer_cache: Optional[Any] = None
_explainer_meta: Optional[Tuple[int, float]] = None


def load_shap_background() -> Optional[Any]:
    global _bg_cache, _bg_mtime
    path = shap_background_path()
    if not os.path.exists(path):
        return None
    try:
        import joblib

        mtime = os.path.getmtime(path)
        if _bg_cache is not None and _bg_mtime == mtime:
            return _bg_cache
        _bg_cache = joblib.load(path)
        _bg_mtime = mtime
        return _bg_cache
    except Exception:
        return None


def _get_linear_explainer(linear: Any, background: Any) -> Any:
    global _explainer_cache, _explainer_meta
    import shap

    path = shap_background_path()
    mtime = os.path.getmtime(path) if os.path.isfile(path) else 0.0
    meta = (id(linear), mtime)
    if _explainer_cache is None or _explainer_meta != meta:
        _explainer_cache = shap.LinearExplainer(linear, background)
        _explainer_meta = meta
    return _explainer_cache


def _feature_names(vectorizer: Any) -> Optional[np.ndarray]:
    if hasattr(vectorizer, "get_feature_names_out"):
        return vectorizer.get_feature_names_out()
    if hasattr(vectorizer, "get_feature_names"):
        return vectorizer.get_feature_names()
    if hasattr(vectorizer, "vectorizer") and hasattr(vectorizer.vectorizer, "get_feature_names_out"):
        return vectorizer.vectorizer.get_feature_names_out()
    return None


def compute_shap_linear_explanation(
    *,
    lr_model_wrapped: Any,
    vectorizer: Any,
    processed_text: str,
    background: Any,
    top_k: int = 8,
) -> Dict[str, Any]:
    """
    SHAP values for unwrapped sklearn LogisticRegression vs background distribution.
    Positive SHAP (margin for positive class) = pushes toward label 1 (FAKE in this project).
    """
    try:
        import shap
    except ImportError as e:
        return {"available": False, "reason": f"SHAP not available: {e}"}

    linear = _unwrap_lr(lr_model_wrapped)
    if linear is None or not hasattr(linear, "coef_"):
        return {"available": False, "reason": "Logistic Regression model not usable for SHAP."}

    if background is None:
        return {"available": False, "reason": "Missing shap_background.joblib. Retrain your model pipeline to regenerate SHAP background data."}

    names = _feature_names(vectorizer)
    if names is None:
        return {"available": False, "reason": "Vectorizer has no feature names."}

    try:
        x = vectorizer.transform([processed_text])
        explainer = _get_linear_explainer(linear, background)
        sv = explainer.shap_values(x)
    except Exception as e:
        return {"available": False, "reason": str(e)[:120]}

    # Binary: array or list of arrays per class
    if isinstance(sv, list):
        pos_class = 1
        if hasattr(linear, "classes_") and len(linear.classes_) == 2:
            pos_idx = list(linear.classes_).index(pos_class) if pos_class in linear.classes_ else 1
        else:
            pos_idx = 1
        sv_arr = np.asarray(sv[pos_idx]).ravel()
    else:
        sv_arr = np.asarray(sv).ravel()
        if sv_arr.size != x.shape[1]:
            sv_arr = np.asarray(sv).reshape(-1, x.shape[1])[0]

    x_dense = np.asarray(x.toarray()).ravel()
    n = min(len(sv_arr), len(names), len(x_dense))

    # Prefer features present in this document; fall back to all features by |shap|
    doc_idx = np.where(x_dense[:n] > 0)[0]
    if len(doc_idx) < top_k:
        doc_idx = np.arange(n)

    def top_positive(indices: np.ndarray) -> List[Dict[str, Any]]:
        sub = [(int(i), float(sv_arr[i])) for i in indices if i < n]
        sub.sort(key=lambda t: t[1], reverse=True)
        out = []
        for i, s in sub:
            if s <= 0:
                break
            out.append({"feature": str(names[i]), "shap": round(s, 6)})
            if len(out) >= top_k:
                break
        return out

    def top_negative(indices: np.ndarray) -> List[Dict[str, Any]]:
        sub = [(int(i), float(sv_arr[i])) for i in indices if i < n]
        sub.sort(key=lambda t: t[1])
        out = []
        for i, s in sub:
            if s >= 0:
                break
            out.append({"feature": str(names[i]), "shap": round(s, 6)})
            if len(out) >= top_k:
                break
        return out

    fake_push = top_positive(doc_idx)
    real_push = top_negative(doc_idx)

    if not fake_push and not real_push:
        by_mag = sorted(range(n), key=lambda i: abs(sv_arr[i]), reverse=True)[: top_k * 2]
        fake_push = top_positive(np.array(by_mag))
        real_push = top_negative(np.array(by_mag))

    return {
        "available": True,
        "method": "shap.LinearExplainer",
        "model": "Logistic Regression (base estimator)",
        "toward_fake": fake_push,
        "toward_real": real_push,
        "note": "Positive SHAP increases log-odds for the fake class (label 1); negative values favor real.",
    }
