from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

def _get_stemmer():
    try:
        from nltk.stem import PorterStemmer
        return PorterStemmer()
    except Exception:
        return None


def _caps_ratio(text: str) -> float:
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return 0.0
    caps_words = [w for w in words if w.isupper() and len(w) > 3]
    return len(caps_words) / max(1, len(words))


def _contains_any(text_lower: str, needles: List[str]) -> List[str]:
    hits = []
    for n in needles:
        if n in text_lower:
            hits.append(n)
    return hits


def _style_signals(text_raw: str) -> Dict[str, Any]:
    text_lower = text_raw.lower()

    exclamations = text_raw.count("!")
    questions = text_raw.count("?")
    caps_ratio = _caps_ratio(text_raw)

    # Common clickbait / chain-message signals (kept simple and human-centric)
    clickbait_terms = [
        "breaking",
        "urgent",
        "shocking",
        "miracle",
        "secret",
        "hidden",
        "one weird trick",
        "click here",
        "share",
        "forward",
        "before it",
        "before it's",
        "too late",
        "act fast",
        "don't ignore",
        "limited time",
        "only",
        "now",
        "exclusive",
        "god bless",
        "cure",
        "doctors reveal",
        "scientists discovered",
        "they don't want you to know",
    ]
    hits = _contains_any(text_lower, clickbait_terms)

    signals = []
    if caps_ratio >= 0.18:
        signals.append(f"High emphasis using ALL-CAPS ({int(caps_ratio * 100)}% caps words).")
    if exclamations >= 5:
        signals.append(f"Very excited formatting (found {exclamations} exclamation marks).")
    if questions >= 6:
        signals.append(f"Strong engagement style (found {questions} question marks).")
    if hits:
        # Keep it short for UI.
        show = hits[:6]
        signals.append("Clickbait / viral language detected: " + ", ".join(show) + ("..." if len(hits) > 6 else "") + ".")

    if not signals:
        signals.append("No major clickbait/formatting red-flags detected from writing style alone.")

    return {
        "caps_ratio": caps_ratio,
        "exclamation_count": exclamations,
        "question_count": questions,
        "clickbait_hits": hits[:12],
        "signals": signals,
    }


def _find_highlight_spans(
    text_raw: str,
    fake_keywords: List[str],
    real_keywords: List[str],
) -> List[Dict[str, Any]]:
    """
    Find spans in raw text that match model keywords (which may be stemmed).
    Returns list of {start, end, type, keyword} sorted by start.
    """
    spans: List[Dict[str, Any]] = []
    seen: set = set()

    def add_span(start: int, end: int, span_type: str, keyword: str) -> None:
        key = (start, end)
        if key in seen:
            return
        seen.add(key)
        spans.append({"start": start, "end": end, "type": span_type, "keyword": keyword})

    for kw_list, span_type in [(fake_keywords, "fake"), (real_keywords, "real")]:
        for kw in kw_list:
            k = (kw.get("keyword") if isinstance(kw, dict) else kw) if kw else ""
            k = str(k).strip() if k else ""
            if not k:
                continue
            k_lower = k.lower()
            for m in re.finditer(r"\b\w+\b", text_raw):
                word = m.group()
                start, end = m.span()
                w_lower = word.lower()
                stemmer = _get_stemmer()
                if stemmer:
                    stemmed = stemmer.stem(w_lower)
                    kw_stem = stemmer.stem(k_lower) if " " not in k_lower else k_lower
                    match = stemmed == kw_stem or kw_stem in stemmed or stemmed in kw_stem
                else:
                    match = k_lower == w_lower or k_lower in w_lower or w_lower in k_lower
                if match:
                    add_span(start, end, span_type, k)
                    break

            if " " in k:
                pattern = re.escape(k)
                for mm in re.finditer(pattern, text_raw, re.IGNORECASE):
                    add_span(mm.start(), mm.end(), span_type, k)

    spans.sort(key=lambda x: (x["start"], -x["end"]))
    merged: List[Dict[str, Any]] = []
    for s in spans:
        if merged and s["start"] < merged[-1]["end"]:
            continue
        merged.append(s)
    return merged


def _build_why_sentence(
    verdict: str,
    fact_warnings: List[str],
    style: Dict[str, Any],
    keyword_evidence: Dict[str, Any],
) -> str:
    """Generate a single 'Why FAKE?' or 'Why REAL?' sentence."""
    if verdict == "UNCERTAIN":
        parts = []
        if fact_warnings:
            parts.append("fact-checking raised some concerns")
        fake_d = keyword_evidence.get("fake_drivers") or []
        real_d = keyword_evidence.get("real_drivers") or []
        if len(fake_d) and len(real_d):
            parts.append("the text contains both fake-leaning and real-leaning linguistic signals")
        if not parts:
            return "The model could not confidently classify this as fake or real because the signals are mixed."
        return "This news is UNCERTAIN because " + ", ".join(parts) + "."

    parts: List[str] = []
    is_fake = verdict == "FAKE NEWS"

    if fact_warnings:
        count = len(fact_warnings)
        if count == 1:
            parts.append("fact-checking detected a problematic claim")
        else:
            parts.append(f"fact-checking detected {count} problematic claims")

    style_signals = style.get("signals", [])
    clickbait = [s for s in style_signals if "clickbait" in s.lower() or "caps" in s.lower()]
    if clickbait:
        parts.append("the writing uses sensational or clickbait-style language")

    drivers = (
        keyword_evidence.get("fake_drivers", [])[:4]
        if is_fake
        else keyword_evidence.get("real_drivers", [])[:4]
    )
    if drivers and keyword_evidence.get("available"):
        kw_phrase = ", ".join(d.get("keyword", "") for d in drivers[:3] if d.get("keyword"))
        if kw_phrase:
            parts.append(
                f"phrases and terms like \"{kw_phrase}\" are associated with "
                + ("fake" if is_fake else "real") + " news patterns"
            )

    if not parts:
        if is_fake:
            return "This news is predicted as FAKE based on the ensemble model analysis and linguistic patterns."
        return "This news is predicted as REAL based on the ensemble model analysis and linguistic patterns."

    why = "This news is predicted as FAKE because " if is_fake else "This news is predicted as REAL because "
    if len(parts) == 1:
        why += parts[0] + "."
    elif len(parts) == 2:
        why += parts[0] + " and " + parts[1] + "."
    else:
        why += ", ".join(parts[:-1]) + ", and " + parts[-1] + "."
    return why


def _unwrap_to_linear_model(model: Any) -> Any:
    """Unwrap CalibratedClassifierCV or similar to get the base estimator with coef_."""
    if hasattr(model, "coef_") and model.coef_ is not None:
        return model
    # CalibratedClassifierCV (used in training) wraps the base estimator
    if hasattr(model, "calibrated_classifiers_") and model.calibrated_classifiers_:
        base = model.calibrated_classifiers_[0]
        inner = getattr(base, "estimator", None) or getattr(base, "base_estimator", base)
        if inner is not None and hasattr(inner, "coef_") and inner.coef_ is not None:
            return inner
    return None


def _linear_model_keyword_evidence(
    *,
    model: Any,
    vectorizer: Any,
    processed_text: str,
    target_class_value: int,
    top_k: int = 8,
) -> Dict[str, Any]:
    """
    For linear models with accessible coef_ (LogisticRegression, Linear SVM).
    Produces top TF-IDF features pushing toward `target_class_value`.
    Handles CalibratedClassifierCV-wrapped models.
    """
    linear_model = _unwrap_to_linear_model(model)
    if linear_model is None:
        return {"available": False, "reason": "Model has no coef_ for keyword attribution."}

    # TF-IDF sparse vector
    x = vectorizer.transform([processed_text])

    # Determine class index mapping (use unwrapped model's classes_)
    if hasattr(linear_model, "classes_"):
        classes = list(linear_model.classes_)
        if target_class_value not in classes:
            # Unexpected mapping: fall back.
            return {"available": False, "reason": "Target class not found in model.classes_."}
        target_idx = classes.index(target_class_value)
    else:
        target_idx = 0

    coef = np.array(linear_model.coef_)
    # Handle binary models:
    # - sklearn LogisticRegression stores coef_ shape (1, n_features) for binary.
    # - coef_ corresponds to class `classes_[1]` in the log-odds sense.
    if coef.ndim == 2:
        if coef.shape[0] == 1:
            # If target is the "positive" class, use coef_[0], else flip sign.
            # This keeps attribution intuitive: positive evidence pushes toward the chosen target class.
            if hasattr(linear_model, "classes_") and len(linear_model.classes_) == 2:
                pos_class = linear_model.classes_[1]
                coef_target = coef[0] if target_class_value == pos_class else (-coef[0])
            else:
                coef_target = coef[0]
        else:
            coef_target = coef[target_idx]
    else:
        coef_target = coef

    # Support both:
    # 1) raw sklearn vectorizer (get_feature_names_out)
    # 2) project wrapper TextVectorizer (get_feature_names / .vectorizer.get_feature_names_out)
    feature_names = None
    if hasattr(vectorizer, "get_feature_names_out"):
        feature_names = vectorizer.get_feature_names_out()
    elif hasattr(vectorizer, "get_feature_names"):
        feature_names = vectorizer.get_feature_names()
    elif hasattr(vectorizer, "vectorizer") and hasattr(vectorizer.vectorizer, "get_feature_names_out"):
        feature_names = vectorizer.vectorizer.get_feature_names_out()

    if feature_names is None:
        return {"available": False, "reason": "Vectorizer does not expose feature names."}

    # Contribution score proxy: coef * tfidf_value
    # x is sparse; multiply broadcasts over features.
    contrib = x.multiply(coef_target).toarray().ravel()

    # Take top positive contributions for target (relaxed threshold for small TF-IDF values)
    pos_idx = np.argsort(contrib)[::-1][: top_k * 3]
    keywords = []
    for i in pos_idx:
        score = float(contrib[i])
        if score <= 0:
            continue
        if abs(score) < 1e-12:
            continue
        feature_names_arr = (
            feature_names if hasattr(feature_names, "__getitem__") else list(feature_names)
        )
        name = feature_names_arr[i] if i < len(feature_names_arr) else f"f{i}"
        keywords.append({"keyword": str(name), "score": round(score, 6)})
        if len(keywords) >= top_k:
            break

    # Fallback: if no contrib-based keywords (e.g. sparse doc), use top coefs for features in doc
    if not keywords:
        x_dense = x.toarray().ravel()
        nonzero_idx = np.where(np.asarray(x_dense) > 0)[0]
        if len(nonzero_idx) > 0:
            coef_arr = np.asarray(coef_target)
            # Sort by coefficient (descending for target class)
            sorted_idx = nonzero_idx[np.argsort(coef_arr[nonzero_idx])[::-1][:top_k]]
            feature_names_arr = (
                feature_names if hasattr(feature_names, "__getitem__") else list(feature_names)
            )
            for i in sorted_idx:
                score = float(coef_arr[i])
                name = feature_names_arr[i] if i < len(feature_names_arr) else f"f{i}"
                keywords.append({"keyword": str(name), "score": round(score, 6)})

    return {
        "available": True,
        "target_class": target_class_value,
        "top_keywords": keywords,
    }


def generate_human_explanation(
    *,
    text_raw: str,
    processed_text: str,
    ensemble_result: Dict[str, Any],
    models: Dict[str, Any],
    vectorizer: Any,
    fact_check_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Human-centric explanation:
    - Writing-style signals (caps, punctuation, clickbait)
    - Model keyword evidence (linear model coef_ feature contributions)
    - Fact-checker warnings if available
    """
    # Prefer final/fact-check verdict if present.
    verdict = ensemble_result.get("final_verdict") or ensemble_result.get("prediction")  # "FAKE NEWS" | "REAL NEWS"
    confidence = ensemble_result.get("adjusted_confidence") if ensemble_result.get("final_verdict") else ensemble_result.get("confidence")

    style = _style_signals(text_raw)

    # Fact-check warnings (already human formatted with emojis)
    fact_warnings = []
    if fact_check_result and isinstance(fact_check_result, dict):
        fact_warnings = list(fact_check_result.get("warnings", []) or [])

    # Prefer Logistic Regression for interpretable keyword evidence
    # Model mapping from your app: key is 'Logistic Regression'
    fake_class_value = 1
    real_class_value = 0

    keyword_evidence = {
        "available": False,
        "fake_drivers": [],
        "real_drivers": [],
        "method": "linear_model_coef",
    }

    for model_key in ("Logistic Regression", "SVM"):
        candidate = models.get(model_key)
        if candidate is None:
            continue
        fake_ev = _linear_model_keyword_evidence(
            model=candidate,
            vectorizer=vectorizer,
            processed_text=processed_text,
            target_class_value=fake_class_value,
            top_k=7,
        )
        real_ev = _linear_model_keyword_evidence(
            model=candidate,
            vectorizer=vectorizer,
            processed_text=processed_text,
            target_class_value=real_class_value,
            top_k=7,
        )
        if fake_ev.get("available") and real_ev.get("available"):
            fake_kw = fake_ev.get("top_keywords", [])[:7]
            real_kw = real_ev.get("top_keywords", [])[:7]
            if fake_kw or real_kw:
                keyword_evidence.update(
                    {
                        "available": True,
                        "fake_drivers": fake_kw,
                        "real_drivers": real_kw,
                        "method": "linear_model_coef",
                        "source_model": model_key,
                    }
                )
                break

    # Turn everything into a compact "top reasons" section.
    top_reasons: List[str] = []

    # 1) Explain any ML -> fact-check adjustment clearly.
    ml_verdict = ensemble_result.get("prediction")
    final_verdict = ensemble_result.get("final_verdict") or ml_verdict

    selected_mode = fact_check_result.get("selected_mode") if isinstance(fact_check_result, dict) else None
    mode_suffix = f" ({selected_mode} mode)" if selected_mode else ""

    fact_checker_available = fact_check_result is not None
    has_fact_issues = bool(fact_warnings)

    if fact_checker_available:
        if has_fact_issues:
            top_reasons.append(
                f"Fact-checker override{mode_suffix}: found {len(fact_warnings)} issue(s), so the verdict was forced to {final_verdict}."
            )
            if ml_verdict and final_verdict and ml_verdict != final_verdict:
                top_reasons.append(f"ML ensemble predicted {ml_verdict}, but fact-checker adjusted it.")

            fact_reason = ensemble_result.get("fact_check_reason")
            if fact_reason:
                top_reasons.append(fact_reason)

            # Keep it concrete but short: include up to 2 warnings
            top_reasons.extend(fact_warnings[:2])
        else:
            top_reasons.append(
                f"Fact-checker found no issues{mode_suffix}, so the final verdict comes from the ML ensemble."
            )
    else:
        top_reasons.append("Fact-checking is not available/configured, so this verdict is based on the ML ensemble only.")

    # 2) Add style signals (1-2 sentences)
    # Pick first 1-2 signals to keep UI clean.
    top_reasons.extend(style.get("signals", [])[:2])

    # 3) Add model keyword evidence as human sentences
    if keyword_evidence["available"]:
        if verdict == "FAKE NEWS":
            drivers = keyword_evidence["fake_drivers"][:4]
            if drivers:
                kw_text = ", ".join([d["keyword"] for d in drivers if d.get("keyword")])
                top_reasons.append(f"Model evidence: keywords like {kw_text} push the prediction toward FAKE.")
        else:
            drivers = keyword_evidence["real_drivers"][:4]
            if drivers:
                kw_text = ", ".join([d["keyword"] for d in drivers if d.get("keyword")])
                top_reasons.append(f"Model evidence: keywords like {kw_text} push the prediction toward REAL.")

    if not top_reasons:
        top_reasons.append("Insufficient textual evidence found to explain the decision clearly. Please try another article text.")

    # Build a plain-language verdict narrative and quantitative evidence summary
    fake_votes = int(ensemble_result.get("fake_votes") or 0)
    real_votes = int(ensemble_result.get("real_votes") or 0)
    total_votes = max(1, fake_votes + real_votes)
    agreement_pct = round((max(fake_votes, real_votes) / total_votes) * 100, 1)
    vote_margin_pct = round((abs(fake_votes - real_votes) / total_votes) * 100, 1)
    final_confidence_pct = round(float(confidence or 0.0), 2)

    style_signal_count = len(style.get("clickbait_hits", []) or [])
    fact_issue_count = len(fact_warnings)
    fake_keywords_count = len(keyword_evidence.get("fake_drivers", []) or [])
    real_keywords_count = len(keyword_evidence.get("real_drivers", []) or [])

    if verdict == "FAKE NEWS":
        verdict_narrative = (
            f"This news is marked as FAKE because the model evidence leans fake "
            f"({fake_votes}/{total_votes} model votes, {agreement_pct}% agreement)"
        )
        if fact_issue_count > 0:
            verdict_narrative += f", and fact-checking detected {fact_issue_count} issue(s)."
        else:
            verdict_narrative += "."
    elif verdict == "UNCERTAIN":
        lean = "real" if real_votes >= fake_votes else "fake"
        verdict_narrative = (
            f"The models leaned toward {lean} ({fake_votes} fake, {real_votes} real votes), "
            f"but overall confidence was too low for a clear verdict, so the result is UNCERTAIN."
        )
        if fact_issue_count > 0:
            verdict_narrative += f" Fact-checking also raised {fact_issue_count} concern(s)."
    else:
        verdict_narrative = (
            f"This news is marked as REAL because the model evidence leans real "
            f"({real_votes}/{total_votes} model votes, {agreement_pct}% agreement)"
        )
        if fact_issue_count > 0:
            verdict_narrative += (
                f", but there are {fact_issue_count} fact-check warning(s) to review."
            )
        else:
            verdict_narrative += ", and fact-checking did not flag major issues."

    fake_kws = [d.get("keyword") for d in (keyword_evidence.get("fake_drivers") or []) if d.get("keyword")]
    real_kws = [d.get("keyword") for d in (keyword_evidence.get("real_drivers") or []) if d.get("keyword")]
    highlighted_spans = _find_highlight_spans(text_raw, fake_kws, real_kws)

    why_sentence = _build_why_sentence(verdict, fact_warnings, style, keyword_evidence)

    shap_attribution: Dict[str, Any] = {"available": False, "reason": "Not computed"}
    lr_for_shap = models.get("Logistic Regression")
    if lr_for_shap is not None:
        from backend.shap_explain import compute_shap_linear_explanation, load_shap_background

        shap_attribution = compute_shap_linear_explanation(
            lr_model_wrapped=lr_for_shap,
            vectorizer=vectorizer,
            processed_text=processed_text,
            background=load_shap_background(),
            top_k=8,
        )

    return {
        "summary": {
            "verdict": verdict,
            "confidence": confidence,
            "narrative": verdict_narrative,
        },
        "human_reasons": top_reasons,
        "writing_style_signals": style,
        "model_keyword_evidence": keyword_evidence,
        "evidence_breakdown": {
            "model_agreement_percent": agreement_pct,
            "vote_margin_percent": vote_margin_pct,
            "final_confidence_percent": final_confidence_pct,
            "style_signal_count": style_signal_count,
            "fact_check_issue_count": fact_issue_count,
            "fake_keyword_count": fake_keywords_count,
            "real_keyword_count": real_keywords_count,
        },
        "fact_check": {
            "available": bool(fact_warnings),
            "warnings": fact_warnings[:8],
        },
        "ensemble_meta": {
            "fake_votes": ensemble_result.get("fake_votes"),
            "real_votes": ensemble_result.get("real_votes"),
            "decision_type": ensemble_result.get("decision_type"),
        },
        "highlighted_spans": highlighted_spans,
        "why_sentence": why_sentence,
        "shap_attribution": shap_attribution,
    }

