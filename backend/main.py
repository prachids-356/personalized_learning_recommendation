from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

from backend.data.generator import save_data, PREREQUISITES, TOPIC_DIFFICULTY
from backend.data.preprocessor import compute_mastery_matrix, prepare_retention_features
from backend.models.recommender import HybridRecommender
from backend.models.retention import SpacedRepetitionModel

app = FastAPI(title="Personalized Learning Recommendation & Spaced Retention Engine")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "files")
STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")
LOGS_CSV = os.path.join(DATA_DIR, "student_logs.csv")
RETENTION_CSV = os.path.join(DATA_DIR, "retention_logs.csv")

import joblib

# Global variables for models and data
students_df = None
logs_df = None
retention_df = None
recommender = HybridRecommender()
retention_model = SpacedRepetitionModel()
assistments_model = None
ASSISTMENTS_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "assistments_model.pkl")

def load_and_train():
    global students_df, logs_df, retention_df, recommender, retention_model, assistments_model
    
    # 1. Generate data if not exists
    if not os.path.exists(STUDENTS_CSV) or not os.path.exists(LOGS_CSV) or not os.path.exists(RETENTION_CSV):
        print("Data files not found. Generating synthetic dataset...")
        save_data(DATA_DIR)
        
    students_df = pd.read_csv(STUDENTS_CSV)
    logs_df = pd.read_csv(LOGS_CSV)
    retention_df = pd.read_csv(RETENTION_CSV)
    
    # Convert timestamps to datetime objects
    logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])
    retention_df["timestamp"] = pd.to_datetime(retention_df["timestamp"])
    
    # 2. Train Recommender Model
    print("Training Hybrid Recommender (SVD Collaborative Filtering)...")
    mastery_matrix = compute_mastery_matrix(logs_df)
    recommender.fit(mastery_matrix)
    
    # 3. Train Spaced Repetition Model
    print("Training Spaced Repetition (Random Forest Retention) Model...")
    X, y = prepare_retention_features(retention_df)
    retention_model.fit(X, y)
    
    # 4. Load ASSISTments Performance Predictor Model if exists
    if os.path.exists(ASSISTMENTS_MODEL_PATH):
        print("Loading ASSISTments performance predictor model...")
        try:
            assistments_model = joblib.load(ASSISTMENTS_MODEL_PATH)
            print("ASSISTments performance predictor model loaded successfully!")
        except Exception as e:
            print(f"Error loading ASSISTments model: {e}")
            
    print("Models successfully trained and loaded!")

@app.on_event("startup")
def startup_event():
    load_and_train()

class PracticeSubmission(BaseModel):
    student_id: int
    topic: str
    correct: int  # 0 or 1
    attempts_count: int
    time_taken: int
    hints_used: int
    days_elapsed: float = 0.0  # Simulate time passing since last activity

@app.get("/api/students")
def get_students():
    if students_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    return students_df.to_dict(orient="records")

@app.get("/api/student/{student_id}")
def get_student_details(student_id: int):
    global logs_df, students_df
    if logs_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
        
    # Check if student exists
    student_record = students_df[students_df["student_id"] == student_id]
    if student_record.empty:
        raise HTTPException(status_code=404, detail="Student not found")
        
    student_logs = logs_df[logs_df["user_id"] == student_id]
    
    # Compute current mastery for each topic
    mastery_matrix = compute_mastery_matrix(student_logs)
    mastery_dict = {}
    
    if not mastery_matrix.empty and student_id in mastery_matrix.index:
        mastery_dict = mastery_matrix.loc[student_id].to_dict()
    else:
        mastery_dict = {topic: 0.0 for topic in PREREQUISITES.keys()}
        
    # Fill missing topics with 0.0
    for topic in PREREQUISITES.keys():
        if topic not in mastery_dict:
            mastery_dict[topic] = 0.0
            
    # Compute summary statistics
    total_attempts = int(student_logs["attempts_count"].sum()) if not student_logs.empty else 0
    correct_attempts = int(student_logs["correct"].sum()) if not student_logs.empty else 0
    avg_accuracy = float(correct_attempts / len(student_logs)) if not student_logs.empty else 0.0
    avg_time = float(student_logs["time_taken"].mean()) if not student_logs.empty else 0.0
    
    # Compute prerequisite readiness status for each topic
    readiness = recommender.compute_prereq_readiness(student_id, mastery_dict)
    
    topics_status = []
    for topic in PREREQUISITES.keys():
        mastery = mastery_dict.get(topic, 0.0)
        ready_score = readiness.get(topic, 1.0)
        
        status = "Locked"
        if ready_score >= 0.7:
            status = "Ready" if mastery < 0.6 else "Mastered" if mastery >= 0.8 else "Learning"
        elif ready_score >= 0.2:
            status = "Review Prereqs"
            
        topics_status.append({
            "topic": topic,
            "mastery": float(mastery),
            "readiness": float(ready_score),
            "status": status,
            "prerequisites": PREREQUISITES[topic]
        })
        
    return {
        "student_id": student_id,
        "ability": float(student_record["ability"].values[0]),
        "forgetting_rate": float(student_record["forgetting_rate"].values[0]),
        "stats": {
            "total_attempts": total_attempts,
            "solved_count": len(student_logs[student_logs["correct"] == 1]),
            "avg_accuracy": avg_accuracy,
            "avg_time_seconds": avg_time
        },
        "topics": topics_status
    }

@app.get("/api/recommendations/{student_id}")
def get_recommendations(student_id: int):
    global logs_df
    if logs_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
        
    student_logs = logs_df[logs_df["user_id"] == student_id]
    mastery_matrix = compute_mastery_matrix(student_logs)
    
    mastery_dict = {}
    if not mastery_matrix.empty and student_id in mastery_matrix.index:
        mastery_dict = mastery_matrix.loc[student_id].to_dict()
    else:
        mastery_dict = {topic: 0.0 for topic in PREREQUISITES.keys()}
        
    recommendations = recommender.recommend(student_id, mastery_dict, top_k=3)
    return recommendations

@app.get("/api/retention/{student_id}")
def get_retention_curves(student_id: int):
    global logs_df, retention_df
    if logs_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
        
    student_logs = logs_df[logs_df["user_id"] == student_id]
    
    retention_info = []
    forgetting_curves = {}
    
    # We evaluate retention for topics the student has practiced at least once
    practiced_topics = student_logs["topic"].unique() if not student_logs.empty else []
    
    now = datetime.now()
    
    for topic in PREREQUISITES.keys():
        topic_logs = student_logs[student_logs["topic"] == topic]
        
        if topic_logs.empty:
            continue
            
        # Get student parameters on this topic
        revision_count = len(topic_logs[topic_logs["is_revision"] == 1])
        prior_correct = len(topic_logs[topic_logs["correct"] == 1])
        prior_accuracy = prior_correct / len(topic_logs)
        last_attempt_correct = int(topic_logs.sort_values("timestamp").iloc[-1]["correct"])
        
        # Calculate days since last practice
        last_practice_time = topic_logs["timestamp"].max()
        days_since = max(0.0, (now - last_practice_time).total_seconds() / (24 * 3600))
        
        # Build features dict
        student_features = {
            "revision_count": revision_count,
            "prior_accuracy": prior_accuracy,
            "difficulty": TOPIC_DIFFICULTY[topic],
            "last_attempt_correct": last_attempt_correct
        }
        
        # Predict half-life and current retention probability
        half_life = retention_model.predict_half_life(student_features)
        retention_prob = retention_model.predict_retention_probability(student_features, days_since)
        
        retention_info.append({
            "topic": topic,
            "revision_count": revision_count,
            "days_since_last_practice": float(days_since),
            "predicted_half_life_days": float(half_life),
            "retention_probability": float(retention_prob),
            "should_revise": bool(retention_prob < 0.60),
            "difficulty": TOPIC_DIFFICULTY[topic]
        })
        
        # Generate 14-day projection data points for charts
        curve_points = []
        for day in range(15):
            prob = retention_model.predict_retention_probability(student_features, day)
            curve_points.append({"day": day, "probability": float(prob)})
        forgetting_curves[topic] = curve_points
        
    return {
        "student_id": student_id,
        "retention_status": retention_info,
        "forgetting_curves": forgetting_curves
    }

@app.post("/api/practice")
def submit_practice(submission: PracticeSubmission):
    global logs_df, retention_df
    if logs_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
        
    student_id = submission.student_id
    topic = submission.topic
    
    # 1. Update previous timestamps for student's practice to simulate elapsed days
    if submission.days_elapsed > 0:
        # Shift past records back in time
        delta = timedelta(days=submission.days_elapsed)
        logs_df.loc[logs_df["user_id"] == student_id, "timestamp"] -= delta
        retention_df.loc[retention_df["user_id"] == student_id, "timestamp"] -= delta
        
    # 2. Get state prior to this attempt to log spaced repetition features if it's a revision
    student_logs = logs_df[logs_df["user_id"] == student_id]
    topic_logs = student_logs[student_logs["topic"] == topic]
    
    is_revision = 0 if topic_logs.empty else 1
    
    now = datetime.now()
    
    if is_revision:
        # Create a retention record
        revision_count = len(topic_logs[topic_logs["is_revision"] == 1])
        prior_correct = len(topic_logs[topic_logs["correct"] == 1])
        prior_accuracy = prior_correct / len(topic_logs)
        last_attempt_correct = int(topic_logs.sort_values("timestamp").iloc[-1]["correct"])
        
        last_practice_time = topic_logs["timestamp"].max()
        days_since = max(0.1, (now - last_practice_time).total_seconds() / (24 * 3600))
        
        new_retention_row = pd.DataFrame([{
            "user_id": student_id,
            "topic": topic,
            "revision_count": revision_count,
            "days_since_last_revision": float(days_since),
            "prior_accuracy": prior_accuracy,
            "difficulty": TOPIC_DIFFICULTY[topic],
            "last_attempt_correct": last_attempt_correct,
            "recalled": submission.correct,
            "timestamp": now
        }])
        retention_df = pd.concat([retention_df, new_retention_row], ignore_index=True)
        retention_df.to_csv(RETENTION_CSV, index=False)
        
    # 3. Create general log row
    new_log_row = pd.DataFrame([{
        "user_id": student_id,
        "topic": topic,
        "correct": submission.correct,
        "attempts_count": submission.attempts_count,
        "time_taken": submission.time_taken,
        "hints_used": submission.hints_used,
        "is_revision": is_revision,
        "timestamp": now
    }])
    logs_df = pd.concat([logs_df, new_log_row], ignore_index=True)
    logs_df.to_csv(LOGS_CSV, index=False)
    
    # 4. Retrain models on the new data incrementally
    print(f"Incremental retraining triggered by practice on {topic} for student {student_id}...")
    mastery_matrix = compute_mastery_matrix(logs_df)
    recommender.fit(mastery_matrix)
    
    X, y = prepare_retention_features(retention_df)
    retention_model.fit(X, y)
    
    return {"status": "success", "message": f"Practice interaction added and models retrained."}

@app.get("/api/performance/model-info")
def get_model_info():
    model_loaded = assistments_model is not None
    return {
        "model_loaded": model_loaded,
        "model_name": "Hist Gradient Boosting Classifier",
        "dataset": "ASSISTments 2009-2010 (150k rows)",
        "accuracy": 0.9121,
        "auc_score": 0.9116,
        "features": [
            "student_overall_accuracy",
            "first_action",
            "attempt_count",
            "hint_count",
            "original",
            "opportunity"
        ]
    }

class PerformancePredictionRequest(BaseModel):
    student_id: int
    topic: str
    hints_used: int
    attempts_count: int

@app.post("/api/performance/predict")
def predict_performance(req: PerformancePredictionRequest):
    global logs_df, assistments_model
    if logs_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
        
    student_logs = logs_df[logs_df["user_id"] == req.student_id]
    
    # Compute overall accuracy
    if not student_logs.empty:
        overall_acc = len(student_logs[student_logs["correct"] == 1]) / len(student_logs)
        opportunity = len(student_logs[student_logs["topic"] == req.topic]) + 1
    else:
        overall_acc = 0.65
        opportunity = 1
        
    # Current attempt context features
    first_action = 1.0 if req.hints_used > 0 else 0.0
    attempt_count = float(req.attempts_count)
    hint_count = float(req.hints_used)
    
    features = np.array([[
        overall_acc,
        first_action,
        attempt_count,
        hint_count,
        1, # original
        opportunity
    ]])
    
    prob = 0.95  # Default fallback
    prediction = 1
    
    if assistments_model is not None:
        try:
            prob = float(assistments_model.predict_proba(features)[0, 1])
            prediction = int(assistments_model.predict(features)[0])
        except Exception as e:
            print(f"Error predicting with ASSISTments model: {e}")
            prob = 0.95 if (req.hints_used == 0 and req.attempts_count == 1) else 0.05
            prediction = 1 if prob >= 0.5 else 0
    else:
        # Fallback heuristic
        prob = 0.95 if (req.hints_used == 0 and req.attempts_count == 1) else 0.05
        prediction = 1 if prob >= 0.5 else 0
        
    return {
        "success": True,
        "prediction": prediction,
        "probability_correct": prob,
        "accuracy_reference": 0.9121
    }
