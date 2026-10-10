from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import httpx
import logging
import pandas as pd
import numpy as np
import os
from urllib.parse import urlencode
from urllib.parse import urlparse
from datetime import datetime, timedelta

from backend.data.generator import save_data, PREREQUISITES, TOPIC_DIFFICULTY
from backend.data.preprocessor import compute_mastery_matrix, prepare_retention_features
from backend.models.recommender import HybridRecommender
from backend.models.retention import SpacedRepetitionModel
from backend.database import initialize_from_csv, load_dataframes, save_dataframes


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("learning_engine")

app = FastAPI(title="Personalized Learning Recommendation & Spaced Retention Engine")

frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "local-development-session-secret"),
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "false").lower() == "true",
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
        
    initialize_from_csv(STUDENTS_CSV, LOGS_CSV, RETENTION_CSV)
    students_df, logs_df, retention_df = load_dataframes()
    
    # Convert timestamps to datetime objects
    logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"], format="mixed")
    retention_df["timestamp"] = pd.to_datetime(retention_df["timestamp"], format="mixed")
    
    # 2. Train Recommender Model
    logger.info("Training hybrid recommender")
    mastery_matrix = compute_mastery_matrix(logs_df)
    recommender.fit(mastery_matrix)
    
    # 3. Train Spaced Repetition Model
    logger.info("Training spaced repetition model")
    X, y = prepare_retention_features(retention_df)
    retention_model.fit(X, y)
    
    # 4. Load ASSISTments Performance Predictor Model if exists
    if os.path.exists(ASSISTMENTS_MODEL_PATH):
        logger.info("Loading ASSISTments performance predictor model")
        try:
            assistments_model = joblib.load(ASSISTMENTS_MODEL_PATH)
            logger.info("ASSISTments performance predictor model loaded")
        except Exception as e:
            logger.exception("Error loading ASSISTments model")
            
    logger.info("Models successfully trained and loaded")

@app.on_event("startup")
def startup_event():
    load_and_train()

@app.get("/health")
def health_check():
    return {"status": "ok", "models_loaded": students_df is not None}


@app.get("/api/auth/me")
def get_current_user(request: Request):
    return {"authenticated": "github_user" in request.session, "user": request.session.get("github_user")}


@app.get("/api/auth/github/login")
def github_login(request: Request):
    client_id = os.getenv("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    callback_url = f"{str(request.base_url).rstrip('/')}/api/auth/github/callback"
    request.session["github_oauth_state"] = os.urandom(24).hex()
    params = {
        "client_id": client_id,
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", callback_url),
        "scope": "read:user user:email",
        "state": request.session["github_oauth_state"],
    }
    query = urlencode(params)
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@app.get("/api/auth/github/status")
def github_auth_status():
    return {"oauth_configured": bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"))}


@app.get("/api/auth/github/callback")
async def github_callback(request: Request, code: str = "", state: str = ""):
    if not code or state != request.session.pop("github_oauth_state", None):
        raise HTTPException(status_code=400, detail="Invalid GitHub OAuth callback")

    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={"client_id": client_id, "client_secret": client_secret, "code": code},
            headers={"Accept": "application/json"},
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub did not return an access token")

        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        user_response.raise_for_status()
        user = user_response.json()

    request.session["github_user"] = {
        "id": user["id"],
        "login": user["login"],
        "name": user.get("name"),
        "avatar_url": user.get("avatar_url"),
        "html_url": user.get("html_url"),
    }
    return RedirectResponse(frontend_origins[0])


@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"authenticated": False}


class LearningProfile(BaseModel):
    goal: str = Field(default="", max_length=160)
    experience: str = Field(default="beginner", max_length=40)
    github: str = Field(default="", max_length=300)
    leetcode: str = Field(default="", max_length=300)
    hackerrank: str = Field(default="", max_length=300)
    geeksforgeeks: str = Field(default="", max_length=300)


async def analyze_github_profile(profile_url):
    if not profile_url:
        return None

    parsed = urlparse(profile_url if "://" in profile_url else f"https://{profile_url}")
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return {"status": "invalid", "message": "Use a github.com profile URL."}

    username = parsed.path.strip("/").split("/")[0]
    if not username:
        return {"status": "invalid", "message": "GitHub username is missing."}

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "EduPrime-AI"}
    async with httpx.AsyncClient(timeout=10) as client:
        user_response = await client.get(f"https://api.github.com/users/{username}", headers=headers)
        if user_response.status_code == 404:
            return {"status": "not_found", "message": "GitHub profile was not found."}
        user_response.raise_for_status()
        user = user_response.json()

        repos_response = await client.get(
            f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated",
            headers=headers,
        )
        repos_response.raise_for_status()
        repositories = repos_response.json()

    language_counts = {}
    for repository in repositories:
        language = repository.get("language")
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1

    return {
        "status": "analyzed",
        "username": user.get("login"),
        "public_repositories": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "languages": sorted(language_counts, key=language_counts.get, reverse=True)[:6],
        "recent_repository_count": len(repositories),
    }


@app.get("/api/profile")
def get_learning_profile(request: Request):
    return request.session.get("learning_profile", None)


@app.post("/api/profile")
async def save_learning_profile(profile: LearningProfile, request: Request):
    saved_profile = profile.model_dump()
    saved_profile["sources"] = {
        "github": bool(profile.github),
        "leetcode": bool(profile.leetcode),
        "hackerrank": bool(profile.hackerrank),
        "geeksforgeeks": bool(profile.geeksforgeeks),
    }
    try:
        saved_profile["github_analysis"] = await analyze_github_profile(profile.github)
    except httpx.HTTPError:
        saved_profile["github_analysis"] = {"status": "unavailable", "message": "GitHub analysis is temporarily unavailable."}
    request.session["learning_profile"] = saved_profile
    return saved_profile

class PracticeSubmission(BaseModel):
    student_id: int
    topic: str
    correct: int = Field(ge=0, le=1)
    attempts_count: int = Field(ge=1)
    time_taken: int = Field(ge=0)
    hints_used: int = Field(ge=0)
    days_elapsed: float = Field(default=0.0, ge=0.0)

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
def get_recommendations(student_id: int, request: Request):
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
    profile = request.session.get("learning_profile", {})
    profile_text = " ".join([
        profile.get("goal", ""),
        profile.get("experience", ""),
        " ".join(key for key in ("github", "leetcode", "hackerrank", "geeksforgeeks") if profile.get(key)),
        " ".join(profile.get("github_analysis", {}).get("languages", [])),
    ]).lower()
    topic_keywords = {
        "Arrays": ("array", "data structure", "leetcode", "hackerrank", "geeksforgeeks"),
        "Strings": ("string", "text", "frontend"),
        "Hashing": ("hash", "backend", "api", "python", "javascript", "typescript"),
        "Trees": ("tree", "backend", "system design"),
        "Graphs": ("graph", "network", "backend", "java", "go", "c++"),
        "Dynamic Programming": ("dynamic", "optimization", "interview"),
    }
    for recommendation in recommendations:
        matches = topic_keywords.get(recommendation["topic"], ())
        boost = 1.08 if any(keyword in profile_text for keyword in matches) else 1.0
        recommendation["personalization_boost"] = boost
        recommendation["recommendation_score"] *= boost
    recommendations.sort(key=lambda item: item["recommendation_score"], reverse=True)
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

    if students_df[students_df["student_id"] == student_id].empty:
        raise HTTPException(status_code=404, detail="Student not found")
    if topic not in PREREQUISITES:
        raise HTTPException(status_code=400, detail="Unknown topic")
    
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
    save_dataframes(students_df, logs_df, retention_df)
    
    # 4. Retrain models on the new data incrementally
    logger.info("Retraining after practice: student=%s topic=%s", student_id, topic)
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
    hints_used: int = Field(ge=0)
    attempts_count: int = Field(ge=1)

@app.post("/api/performance/predict")
def predict_performance(req: PerformancePredictionRequest):
    global logs_df, assistments_model
    if logs_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    if students_df[students_df["student_id"] == req.student_id].empty:
        raise HTTPException(status_code=404, detail="Student not found")
    if req.topic not in PREREQUISITES:
        raise HTTPException(status_code=400, detail="Unknown topic")
        
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
            logger.exception("Error predicting with ASSISTments model")
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
