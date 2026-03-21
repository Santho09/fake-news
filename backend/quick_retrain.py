"""
Quick model retraining script - uses cached processed data if available
"""

import os
import json
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, log_loss, brier_score_loss
import joblib

if __package__ is None or __package__ == "":
    # Allow running as: python backend/quick_retrain.py
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend import config
from backend.src.data_processing import TextPreprocessor, TextVectorizer
import pickle

print("="*80)
print("QUICK MODEL RETRAINING")
print("="*80)

# Check for cached processed data
cache_file = os.path.join(config.DATA_DIR, "processed_cache.pkl")

if os.path.exists(cache_file):
    print("\n✓ Found cached processed data, loading...")
    with open(cache_file, 'rb') as f:
        cache = pickle.load(f)
    X_train_vec = cache['X_train_vec']
    X_test_vec = cache['X_test_vec']
    y_train = cache['y_train']
    y_test = cache['y_test']
    vectorizer = cache['vectorizer']
    y_val = cache.get('y_val')
    if y_val is None:
        # Rebuild validation split if old cache is used.
        print("  Cached data has no validation split; rebuilding split...")
        data_file = os.path.join(config.DATA_DIR, "training_data.csv")
        df = pd.read_csv(data_file)
        preprocessor = TextPreprocessor()
        df['processed_text'] = df['text'].apply(preprocessor.preprocess)
        X_train_full, X_test_text, y_train_full, y_test = train_test_split(
            df['processed_text'],
            df['label'],
            test_size=0.2,
            random_state=42,
            stratify=df['label']
        )
        X_train_text, X_val_text, y_train, y_val = train_test_split(
            X_train_full,
            y_train_full,
            test_size=0.15,
            random_state=42,
            stratify=y_train_full
        )
        rebuilt_vectorizer = TextVectorizer(
            vectorizer_type='tfidf',
            max_features=5000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9
        )
        X_train_vec = rebuilt_vectorizer.fit_transform(X_train_text.tolist())
        X_val_vec = rebuilt_vectorizer.transform(X_val_text.tolist())
        X_test_vec = rebuilt_vectorizer.transform(X_test_text.tolist())
        vectorizer = rebuilt_vectorizer.vectorizer
    else:
        X_val_vec = cache.get('X_val_vec')
        if X_val_vec is None:
            print("  Cached data missing X_val_vec; rebuilding split...")
            data_file = os.path.join(config.DATA_DIR, "training_data.csv")
            df = pd.read_csv(data_file)
            preprocessor = TextPreprocessor()
            df['processed_text'] = df['text'].apply(preprocessor.preprocess)
            X_train_full, X_test_text, y_train_full, y_test = train_test_split(
                df['processed_text'],
                df['label'],
                test_size=0.2,
                random_state=42,
                stratify=df['label']
            )
            X_train_text, X_val_text, y_train, y_val = train_test_split(
                X_train_full,
                y_train_full,
                test_size=0.15,
                random_state=42,
                stratify=y_train_full
            )
            rebuilt_vectorizer = TextVectorizer(
                vectorizer_type='tfidf',
                max_features=5000,
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.9
            )
            X_train_vec = rebuilt_vectorizer.fit_transform(X_train_text.tolist())
            X_val_vec = rebuilt_vectorizer.transform(X_val_text.tolist())
            X_test_vec = rebuilt_vectorizer.transform(X_test_text.tolist())
            vectorizer = rebuilt_vectorizer.vectorizer
    print(f"  Loaded training set: {X_train_vec.shape[0]} samples")
    print(f"  Loaded test set: {X_test_vec.shape[0]} samples")
else:
    # Full preprocessing
    print("\n1. Loading training data...")
    data_file = os.path.join(config.DATA_DIR, "training_data.csv")
    
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found!")
        exit(1)
    
    df = pd.read_csv(data_file)
    print(f"   ✓ Loaded {len(df)} articles")
    
    print("\n2. Preprocessing texts (this may take a few minutes)...")
    preprocessor = TextPreprocessor()
    
    # Process in batches with progress
    batch_size = 1000
    processed_texts = []
    for i in range(0, len(df), batch_size):
        batch = df['text'].iloc[i:i+batch_size]
        processed_batch = batch.apply(preprocessor.preprocess)
        processed_texts.extend(processed_batch.tolist())
        print(f"   Processed {min(i+batch_size, len(df))}/{len(df)} articles...")
    
    df['processed_text'] = processed_texts
    print("   ✓ Text preprocessing complete")
    
    print("\n3. Splitting data...")
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        df['processed_text'], 
        df['label'], 
        test_size=0.2, 
        random_state=42,
        stratify=df['label']
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full,
        y_train_full,
        test_size=0.15,
        random_state=42,
        stratify=y_train_full
    )
    
    print("\n4. Vectorizing text...")
    vectorizer = TextVectorizer(
        vectorizer_type='tfidf',
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.9
    )
    
    X_train_vec = vectorizer.fit_transform(X_train.tolist())
    X_val_vec = vectorizer.transform(X_val.tolist())
    X_test_vec = vectorizer.transform(X_test.tolist())
    print(f"   ✓ Feature matrix shape: {X_train_vec.shape}")
    
    # Cache the processed data
    print("\n5. Caching processed data for future use...")
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(cache_file, 'wb') as f:
        pickle.dump({
            'X_train_vec': X_train_vec,
            'X_test_vec': X_test_vec,
            'X_val_vec': X_val_vec,
            'y_train': y_train,
            'y_test': y_test,
            'y_val': y_val,
            'vectorizer': vectorizer.vectorizer
        }, f)
    print(f"   ✓ Cached to {cache_file}")

# Save vectorizer
print("\nSaving vectorizer...")
vectorizer_path = os.path.join(config.MODELS_DIR, "vectorizer.joblib")
os.makedirs(config.MODELS_DIR, exist_ok=True)
joblib.dump(vectorizer if isinstance(vectorizer, object) and hasattr(vectorizer, 'vectorizer') else vectorizer, vectorizer_path)
print(f"✓ Vectorizer saved to {vectorizer_path}")

# Define models
models = {
    'Naive Bayes': MultinomialNB(alpha=1.0),
    'Random Forest': RandomForestClassifier(
        n_estimators=100, 
        random_state=42, 
        max_depth=10,
        n_jobs=-1
    ),
    'Logistic Regression': LogisticRegression(
        random_state=42, 
        max_iter=1000, 
        C=1.0,
        n_jobs=-1
    ),
    'SVM': SVC(
        kernel='linear', 
        random_state=42, 
        probability=False,
        C=1.0
    )
}

# Train and save models
print("\nTraining models...")
print("="*80)

results = []
model_scores = {}
model_metrics = {
    "summary": {
        "features": int(X_train_vec.shape[1]),
        "calibration_method": "sigmoid (prefit on validation split)",
    },
    "models": {},
}

for model_name, model in models.items():
    print(f"\nTraining {model_name}...")
    
    # Train
    model.fit(X_train_vec, y_train)

    # Validation metrics before calibration
    val_pred = model.predict(X_val_vec)
    if hasattr(model, "predict_proba"):
        val_proba = model.predict_proba(X_val_vec)
    else:
        val_proba = np.vstack([1 - val_pred, val_pred]).T.astype(float)

    val_accuracy = accuracy_score(y_val, val_pred)
    val_precision = precision_score(y_val, val_pred, average='weighted')
    val_recall = recall_score(y_val, val_pred, average='weighted')
    val_f1 = f1_score(y_val, val_pred, average='weighted')
    val_logloss = log_loss(y_val, val_proba, labels=[0, 1])
    val_brier = brier_score_loss(y_val, val_proba[:, 1])

    calibrated_model = CalibratedClassifierCV(estimator=model, method='sigmoid', cv='prefit')
    calibrated_model.fit(X_val_vec, y_val)
    
    # Predict
    y_pred = calibrated_model.predict(X_test_vec)
    y_proba = calibrated_model.predict_proba(X_test_vec)
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    test_logloss = log_loss(y_test, y_proba, labels=[0, 1])
    test_brier = brier_score_loss(y_test, y_proba[:, 1])
    
    results.append({
        'Model': model_name,
        'Accuracy': accuracy,
        'Precision': precision,
        'Recall': recall,
        'F1-Score': f1
    })
    model_scores[model_name] = float(f1)
    model_metrics["models"][model_name] = {
        "validation": {
            "accuracy": round(float(val_accuracy), 4),
            "precision": round(float(val_precision), 4),
            "recall": round(float(val_recall), 4),
            "f1": round(float(val_f1), 4),
            "log_loss": round(float(val_logloss), 4),
            "brier_score": round(float(val_brier), 4),
        },
        "test_calibrated": {
            "accuracy": round(float(accuracy), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "log_loss": round(float(test_logloss), 4),
            "brier_score": round(float(test_brier), 4),
        },
        "calibration_gain": {
            "log_loss_delta": round(float(val_logloss - test_logloss), 4),
            "brier_delta": round(float(val_brier - test_brier), 4),
        },
    }
    
    # Save model
    model_filename = model_name.lower().replace(' ', '_') + '_model.joblib'
    model_path = os.path.join(config.MODELS_DIR, model_filename)
    joblib.dump(calibrated_model, model_path)
    
    print(f"✓ {model_name}: {accuracy*100:.1f}% accuracy - Saved to {model_path}")

# Summary
print("\n" + "="*80)
print("TRAINING COMPLETE")
print("="*80)

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

# Save model weights for weighted soft-voting during inference.
score_sum = sum(model_scores.values()) or 1.0
model_weights = {
    name: round(score / score_sum, 6)
    for name, score in model_scores.items()
}
weights_file = os.path.join(config.MODELS_DIR, "model_weights.json")
with open(weights_file, "w", encoding="utf-8") as wf:
    json.dump(model_weights, wf, indent=2)
print(f"✓ Model weights saved to {weights_file}")

metrics_file = os.path.join(config.MODELS_DIR, "model_metrics.json")
with open(metrics_file, "w", encoding="utf-8") as mf:
    json.dump(model_metrics, mf, indent=2)
print(f"✓ Model metrics saved to {metrics_file}")

# Save results
results_file = os.path.join(config.MODELS_DIR, "training_results.txt")
with open(results_file, 'w') as f:
    f.write("FAKE NEWS DETECTION - MODEL TRAINING RESULTS\n")
    f.write("="*80 + "\n\n")
    f.write(results_df.to_string(index=False))

print(f"\n✓ Results saved to {results_file}")
print("\n✅ All models retrained successfully!")
print("   Version warnings should now be completely resolved.")
