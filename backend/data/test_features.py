import os
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

def test():
    local_path = os.path.join(os.path.dirname(__file__), "files", "skill_builder_data.csv")
    if not os.path.exists(local_path):
        print("Dataset not found!")
        return
        
    print("Loading data...")
    df = pd.read_csv(local_path, nrows=150000, encoding="ISO-8859-1")
    df = df.dropna(subset=["skill_name", "correct", "user_id"])
    df = df.sort_values("order_id")
    
    print("Computing features including current attempt characteristics...")
    features = []
    
    student_history = {}
    
    for idx, row in df.iterrows():
        s_id = row["user_id"]
        correct = int(row["correct"])
        
        # Historical feature
        if s_id not in student_history:
            student_history[s_id] = []
        sh = student_history[s_id]
        past_attempts = len(sh)
        overall_acc = sum(sh) / past_attempts if past_attempts > 0 else 0.65
        
        # Current attempt features
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
        
        student_history[s_id].append(correct)
        
    features_df = pd.DataFrame(features)
    
    X = features_df.drop(columns=["correct"])
    y = features_df["correct"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Training model...")
    model = HistGradientBoostingClassifier(max_iter=100, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc * 100:.2f}%")

if __name__ == "__main__":
    test()
