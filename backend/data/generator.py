import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

# Define the CS Knowledge Graph (Prerequisites)
PREREQUISITES = {
    "Arrays": [],
    "Strings": ["Arrays"],
    "Hashing": ["Arrays"],
    "Sliding Window": ["Arrays", "Strings"],
    "Two Pointers": ["Arrays", "Strings"],
    "Trees": ["Arrays"],
    "Graphs": ["Trees"],
    "Dynamic Programming": ["Arrays", "Trees"]
}

# Topic difficulties (base error rate or complexity)
TOPIC_DIFFICULTY = {
    "Arrays": 0.20,
    "Strings": 0.25,
    "Hashing": 0.35,
    "Sliding Window": 0.45,
    "Two Pointers": 0.40,
    "Trees": 0.50,
    "Graphs": 0.60,
    "Dynamic Programming": 0.75
}

def generate_synthetic_data(num_students=100, seed=42):
    np.random.seed(seed)
    
    # Student profiles
    students = []
    for student_id in range(1, num_students + 1):
        ability = np.random.normal(1.0, 0.2)  # Mean ability 1.0
        ability = max(0.4, min(1.6, ability))  # Bound ability
        forgetting_rate = np.random.normal(0.1, 0.03)  # Daily decay rate of memory strength
        forgetting_rate = max(0.02, forgetting_rate)
        students.append({
            "student_id": student_id,
            "ability": ability,
            "forgetting_rate": forgetting_rate
        })
    
    students_df = pd.DataFrame(students)
    
    # Track student state: mastery in each topic (0.0 to 1.0)
    # Track last solved timestamp and revision counts
    student_topic_state = {}
    for s_id in range(1, num_students + 1):
        student_topic_state[s_id] = {
            topic: {
                "attempts": 0,
                "successes": 0,
                "revisions": 0,
                "last_practiced": None,
                "half_life": 2.0,  # Base half life in days
                "cumulative_attempts": 0
            }
            for topic in PREREQUISITES.keys()
        }
    
    logs = []
    retention_logs = []
    
    start_date = datetime(2026, 5, 1)
    
    # Simulate day-by-day learning for 30 days
    for day in range(30):
        current_time = start_date + timedelta(days=day)
        
        for student in students:
            s_id = student["student_id"]
            ability = student["ability"]
            f_rate = student["forgetting_rate"]
            
            # Each student has a probability of practicing on a given day
            if np.random.rand() > 0.8:
                continue
                
            # Step 1: Spaced Repetition / Revision check
            # Check if student needs to revise any topic they already practiced
            for topic, state in student_topic_state[s_id].items():
                if state["last_practiced"] is not None:
                    days_since = (current_time - state["last_practiced"]).days
                    if days_since > 0:
                        # Duolingo HLR style memory retention probability
                        # p = 2^(-delta_t / half_life)
                        h_l = state["half_life"]
                        p_recall = 2 ** (-days_since / h_l)
                        
                        # If probability of recall drops below threshold (e.g. 65%), student reviews it
                        if p_recall < 0.65 or np.random.rand() < 0.15:  # Trigger review
                            # Simulate revision attempt
                            correct = 1 if np.random.rand() < p_recall * ability else 0
                            
                            # Record this for retention modeling
                            retention_logs.append({
                                "user_id": s_id,
                                "topic": topic,
                                "revision_count": state["revisions"],
                                "days_since_last_revision": days_since,
                                "prior_accuracy": state["successes"] / max(1, state["attempts"]),
                                "difficulty": TOPIC_DIFFICULTY[topic],
                                "last_attempt_correct": 1 if state["successes"] > 0 and correct == 1 else 0, # simulated proxy
                                "recalled": correct,
                                "timestamp": current_time + timedelta(hours=int(np.random.randint(8, 12)))
                            })
                            
                            # Update state
                            state["revisions"] += 1
                            state["attempts"] += 1
                            state["cumulative_attempts"] += 1
                            if correct:
                                state["successes"] += 1
                                # Memory strength increases after successful revision
                                # half_life = half_life * (1 + 1.2 * revision_count)
                                state["half_life"] = min(30.0, state["half_life"] * (1.5 + 0.5 * state["revisions"]))
                            else:
                                # Reset/lower half life if forgotten
                                state["half_life"] = max(1.0, state["half_life"] * 0.5)
                                
                            state["last_practiced"] = current_time
                            
                            # Add to general interactions log
                            logs.append({
                                "user_id": s_id,
                                "topic": topic,
                                "correct": correct,
                                "attempts_count": 1,
                                "time_taken": int(np.random.lognormal(4.5, 0.5)), # avg ~90s
                                "hints_used": int(np.random.choice([0, 1, 2], p=[0.7, 0.2, 0.1]) if not correct else 0),
                                "is_revision": 1,
                                "timestamp": current_time + timedelta(hours=int(np.random.randint(8, 12)))
                            })
            
            # Step 2: Learning a new topic or practicing an active topic
            # Determine available topics (prerequisites met)
            available_topics = []
            for topic, prereqs in PREREQUISITES.items():
                # Check if all prereqs are "mastered" (e.g., accuracy >= 60% and has been practiced)
                prereqs_met = True
                for prereq in prereqs:
                    prereq_state = student_topic_state[s_id][prereq]
                    if prereq_state["attempts"] == 0:
                        prereqs_met = False
                        break
                    prereq_accuracy = prereq_state["successes"] / prereq_state["attempts"]
                    if prereq_accuracy < 0.60:
                        prereqs_met = False
                        break
                if prereqs_met:
                    available_topics.append(topic)
            
            if not available_topics:
                # Fallback to root (Arrays)
                available_topics = ["Arrays"]
            
            # Select topic to practice. Students prefer topics they have practiced less,
            # but still progress to new topics.
            topic_weights = []
            for t in available_topics:
                state = student_topic_state[s_id][t]
                # Weight inversely proportional to how much they practiced it,
                # with high weight on newly unlocked topics.
                weight = 1.0 / (state["cumulative_attempts"] + 1.0)
                if state["cumulative_attempts"] == 0:
                    weight *= 3.0  # Encourage exploring new topics
                topic_weights.append(weight)
            
            topic_weights = np.array(topic_weights) / sum(topic_weights)
            chosen_topic = np.random.choice(available_topics, p=topic_weights)
            
            # Simulate solving a problem in this topic
            state = student_topic_state[s_id][chosen_topic]
            base_difficulty = TOPIC_DIFFICULTY[chosen_topic]
            
            # Mastery index increases as they practice
            practice_effect = min(0.5, 0.1 * state["cumulative_attempts"])
            
            # Probability of success on this attempt
            p_success = (ability * (1.0 - base_difficulty) + practice_effect)
            p_success = max(0.1, min(0.95, p_success))
            
            correct = 1 if np.random.rand() < p_success else 0
            hints = 0
            attempts_req = 1
            
            if not correct:
                # Student might use hints or try multiple times
                hints = int(np.random.choice([0, 1, 2, 3], p=[0.4, 0.3, 0.2, 0.1]))
                # If hints are used, success probability increases on subsequent attempts
                p_success_hinted = min(0.95, p_success + 0.15 * hints)
                if np.random.rand() < p_success_hinted:
                    correct = 1
                    attempts_req = np.random.randint(2, 4)
                else:
                    attempts_req = np.random.randint(2, 5)
            
            time_taken = int(np.random.lognormal(4.8, 0.6) * (1.0 + 0.2 * hints) * (1.0 + 0.1 * attempts_req))
            time_taken = min(1200, max(15, time_taken))
            
            # Update state
            state["attempts"] += 1
            state["cumulative_attempts"] += 1
            if correct:
                state["successes"] += 1
                # Increase memory half-life based on correct practice
                state["half_life"] = min(30.0, state["half_life"] * 1.3)
            else:
                state["half_life"] = max(1.0, state["half_life"] * 0.8)
                
            state["last_practiced"] = current_time
            
            logs.append({
                "user_id": s_id,
                "topic": chosen_topic,
                "correct": correct,
                "attempts_count": attempts_req,
                "time_taken": time_taken,
                "hints_used": hints,
                "is_revision": 0,
                "timestamp": current_time + timedelta(hours=int(np.random.randint(14, 22)))
            })
            
    # Compile into DataFrames
    logs_df = pd.DataFrame(logs)
    retention_df = pd.DataFrame(retention_logs)
    
    return students_df, logs_df, retention_df

def save_data(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    students_df, logs_df, retention_df = generate_synthetic_data()
    
    students_df.to_csv(os.path.join(dest_dir, "students.csv"), index=False)
    logs_df.to_csv(os.path.join(dest_dir, "student_logs.csv"), index=False)
    retention_df.to_csv(os.path.join(dest_dir, "retention_logs.csv"), index=False)
    
    print(f"Data saved successfully to {dest_dir}")
    print(f"Student logs: {len(logs_df)} rows")
    print(f"Retention logs: {len(retention_df)} rows")

if __name__ == "__main__":
    save_data(".")
