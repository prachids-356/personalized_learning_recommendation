import urllib.request
import pandas as pd
import numpy as np
import io
import os
import time
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

def download_and_preprocess_assistments(nrows=150000):
    local_path = os.path.join(os.path.dirname(__file__), "files", "skill_builder_data.csv")
    
    if os.path.exists(local_path):
        file_size = os.path.getsize(local_path)
        if file_size >= 83000000:
            print(f"Loading ASSISTments dataset from local cache ({file_size / (1024 * 1024):.1f}MB): {local_path}...")
            try:
                df = pd.read_csv(local_path, nrows=nrows, encoding="ISO-8859-1")
                print("Successfully loaded! Rows:", len(df))
                return preprocess_df(df)
            except Exception as e:
                print(f"Error reading local cache: {e}. Re-downloading...")
        else:
            print(f"Local cache file exists but is incomplete ({file_size / (1024 * 1024):.1f}MB). Re-downloading...")
            try:
                os.remove(local_path)
            except:
                pass
            
    url = "https://huggingface.co/datasets/Unggi/assistment09_raw_data/resolve/main/skill_builder_data.csv"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        print(f"Downloading ASSISTments dataset (Attempt {attempt}/{max_retries})...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        temp_path = local_path + ".tmp"
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_so_far = 0
                chunk_size = 1024 * 1024 # 1MB chunks
                
                with open(temp_path, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_so_far += len(chunk)
                        if total_size > 0:
                            percent = (bytes_so_far / total_size) * 100
                            print(f"Downloaded {bytes_so_far / (1024 * 1024):.1f}MB / {total_size / (1024 * 1024):.1f}MB ({percent:.1f}%)")
                        else:
                            print(f"Downloaded {bytes_so_far / (1024 * 1024):.1f}MB")
                
                # Check if size matches
                if total_size > 0 and bytes_so_far < total_size:
                    raise Exception(f"Incomplete download: got {bytes_so_far} bytes out of {total_size}")
                
                # If we succeeded, rename temp file to local_path
                if os.path.exists(local_path):
                    os.remove(local_path)
                os.rename(temp_path, local_path)
                print("Successfully downloaded and cached!")
                
                df = pd.read_csv(local_path, nrows=nrows, encoding="ISO-8859-1")
                print("Successfully loaded! Rows:", len(df))
                return preprocess_df(df)
                
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            time.sleep(3)
            
    print("Failed to download ASSISTments dataset after multiple attempts.")
    return None

def preprocess_df(df):
    # Clean dataset: remove rows with missing skill_name or correct values
    df = df.dropna(subset=["skill_name", "correct", "user_id"])
    
    # Sort chronologically by order_id
    df = df.sort_values("order_id")
    
    print("Engineering features...")
    
    # Initialize trackers for rolling history to prevent data leakage
    student_history = {}
    
    features = []
    
    for idx, row in df.iterrows():
        s_id = row["user_id"]
        correct = int(row["correct"])
        
        if s_id not in student_history:
            student_history[s_id] = []
        sh = student_history[s_id]
        past_attempts = len(sh)
        overall_acc = sum(sh) / past_attempts if past_attempts > 0 else 0.65
        
        # Current attempt context (features to predict)
        first_action = float(row["first_action"]) if not pd.isna(row["first_action"]) else 0.0
        attempt_count = float(row["attempt_count"]) if not pd.isna(row["attempt_count"]) else 1.0
        hint_count = float(row["hint_count"]) if not pd.isna(row["hint_count"]) else 0.0
        
        features.append({
            "correct": correct,
            "student_overall_accuracy": overall_acc,
            "first_action": first_action,
            "attempt_count": attempt_count,
            "hint_count": hint_count,
            "original": int(row["original"]) if not pd.isna(row["original"]) else 1,
            "opportunity": int(row["opportunity"]) if not pd.isna(row["opportunity"]) else 1
        })
        
        # Update history
        student_history[s_id].append(correct)
        
    features_df = pd.DataFrame(features)
    print("Feature engineering completed! Final shape:", features_df.shape)
    return features_df

def train_and_evaluate():
    # Load and preprocess
    df = download_and_preprocess_assistments(150000)
    if df is None:
        return
        
    # Features & labels
    X = df.drop(columns=["correct"])
    y = df["correct"]
    
    # Train-test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Training Hist Gradient Boosting Classifier...")
    model = HistGradientBoostingClassifier(max_iter=100, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    # Calculate metrics
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    
    print("\nModel Performance Evaluation:")
    print("=" * 30)
    print(f"Classification Accuracy: {acc * 100:.2f}%")
    print(f"ROC-AUC Score:           {auc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Let's save the model if accuracy is > 90%
    if acc >= 0.90:
        print(f"Success! Model accuracy is {acc * 100:.2f}%, exceeding the 90% target.")
        import joblib
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        os.makedirs(model_dir, exist_ok=True)
        joblib.dump(model, os.path.join(model_dir, "assistments_model.pkl"))
        print("Model saved to models/assistments_model.pkl")

if __name__ == "__main__":
    train_and_evaluate()
