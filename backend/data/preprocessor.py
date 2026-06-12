import pandas as pd
import numpy as np

def compute_mastery_matrix(logs_df):
    """
    Computes a student-topic mastery matrix from interaction logs.
    Mastery score is a combination of accuracy, completion, hints used, and time taken.
    """
    if logs_df.empty:
        return pd.DataFrame()
        
    # Group by student and topic
    grouped = logs_df.groupby(["user_id", "topic"]).agg(
        attempts_sum=("attempts_count", "sum"),
        correct_sum=("correct", "sum"),
        time_avg=("time_taken", "mean"),
        hints_avg=("hints_used", "mean"),
        total_interactions=("correct", "count")
    ).reset_index()
    
    # Calculate raw metrics
    grouped["accuracy"] = grouped["correct_sum"] / grouped["total_interactions"]
    
    # Mastery Score Formula:
    # 1. Base accuracy contribution (0 to 1)
    # 2. Penalty for high hints (up to 20% deduction)
    # 3. Penalty for excessive attempts (up to 10% deduction)
    # 4. Penalty for very slow response (up to 10% deduction)
    
    hint_penalty = np.minimum(0.2, grouped["hints_avg"] * 0.05)
    attempt_penalty = np.minimum(0.1, (grouped["attempts_sum"] / grouped["total_interactions"] - 1) * 0.05)
    time_penalty = np.minimum(0.1, np.maximum(0.0, (grouped["time_avg"] - 60) / 600) * 0.1) # penalty starts above 60s
    
    mastery = grouped["accuracy"] * (1.0 - hint_penalty - attempt_penalty - time_penalty)
    grouped["mastery_score"] = np.clip(mastery, 0.0, 1.0)
    
    # Pivot to create student-topic matrix
    mastery_matrix = grouped.pivot(index="user_id", columns="topic", values="mastery_score").fillna(0.0)
    return mastery_matrix

def prepare_retention_features(retention_df):
    """
    Prepares features and targets for training the spaced repetition model.
    """
    if retention_df.empty:
        return pd.DataFrame(), pd.Series()
        
    # Select features for the model
    feature_cols = [
        "revision_count",
        "days_since_last_revision",
        "prior_accuracy",
        "difficulty",
        "last_attempt_correct"
    ]
    
    X = retention_df[feature_cols].copy()
    y = retention_df["recalled"].copy()
    
    return X, y
