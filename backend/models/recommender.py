import numpy as np
import pandas as pd
from backend.data.generator import PREREQUISITES

class HybridRecommender:
    def __init__(self, n_components=3):
        self.n_components = n_components
        self.mastery_matrix = None
        self.topics = list(PREREQUISITES.keys())
        self.student_ids = []
        self.reconstructed_matrix = None
        
    def fit(self, mastery_matrix_df):
        """
        Fits the SVD collaborative filtering model on student-topic mastery matrix using pure NumPy.
        """
        if mastery_matrix_df.empty:
            return self
            
        self.mastery_matrix = mastery_matrix_df
        self.student_ids = list(mastery_matrix_df.index)
        
        # Ensure all graph topics are represented in columns
        for topic in self.topics:
            if topic not in mastery_matrix_df.columns:
                mastery_matrix_df[topic] = 0.0
                
        # Re-align columns to match predefined topics order
        matrix_data = mastery_matrix_df[self.topics].values
        
        # Compute Singular Value Decomposition (SVD) using NumPy
        # matrix_data shape: (M, N)
        # U shape: (M, M), S shape: (min(M, N),), Vt shape: (N, N)
        U, S, Vt = np.linalg.svd(matrix_data, full_matrices=False)
        
        # Truncate to keep top k latent features
        k = min(self.n_components, matrix_data.shape[1], matrix_data.shape[0])
        k = max(1, k)
        
        U_k = U[:, :k]
        S_k = np.diag(S[:k])
        Vt_k = Vt[:k, :]
        
        # Reconstruct the low-rank approximation of the mastery matrix
        reconstructed = U_k @ S_k @ Vt_k
        
        self.reconstructed_matrix = pd.DataFrame(
            reconstructed,
            index=self.student_ids,
            columns=self.topics
        )
        return self
        
    def compute_prereq_readiness(self, student_id, student_mastery):
        """
        Computes the readiness multiplier (0.0 to 1.0) for all topics for a student.
        A topic is locked or penalized if its prerequisites are not mastered (threshold 0.6).
        """
        readiness = {}
        threshold = 0.60
        
        for topic, prereqs in PREREQUISITES.items():
            if not prereqs:
                readiness[topic] = 1.0
                continue
                
            multiplier = 1.0
            for prereq in prereqs:
                # Get current mastery of prerequisite
                mastery = student_mastery.get(prereq, 0.0)
                if mastery < threshold:
                    # Penalize readiness smoothly based on how far below threshold they are
                    multiplier *= (mastery / threshold) ** 2  # quadratic penalty for strictness
            
            readiness[topic] = max(0.05, multiplier)  # Keep a small minimum so they are not fully dead-ends
            
        return readiness
        
    def recommend(self, student_id, student_mastery_dict, top_k=3):
        """
        Returns ranked list of topic recommendations for a student.
        Combines SVD collaborative filtering preferences with prerequisite readiness.
        """
        # 1. Get CF predicted preference
        cf_preferences = {}
        if self.reconstructed_matrix is not None and student_id in self.reconstructed_matrix.index:
            cf_preferences = self.reconstructed_matrix.loc[student_id].to_dict()
        else:
            # Cold start: default preference is inversely proportional to base topic difficulty
            # (i.e. recommend easier topics first)
            from backend.data.generator import TOPIC_DIFFICULTY
            cf_preferences = {topic: 1.0 - diff for topic, diff in TOPIC_DIFFICULTY.items()}
            
        # 2. Get Prerequisite Readiness
        readiness = self.compute_prereq_readiness(student_id, student_mastery_dict)
        
        recommendations = []
        for topic in self.topics:
            current_mastery = student_mastery_dict.get(topic, 0.0)
            
            # Skip if topic is already highly mastered (e.g. > 85% mastery)
            # as next-item learning is about moving forward.
            if current_mastery >= 0.85:
                continue
                
            pref = cf_preferences.get(topic, 0.5)
            readiness_mult = readiness[topic]
            
            # Combined score: Collaborative preference adjusted by prerequisite readiness
            # and prioritized if current mastery is in the 'sweet spot' (0.1 to 0.7)
            learning_momentum = 1.2 if (0.0 < current_mastery < 0.7) else 1.0
            
            combined_score = pref * readiness_mult * learning_momentum
            
            recommendations.append({
                "topic": topic,
                "cf_score": float(pref),
                "readiness": float(readiness_mult),
                "current_mastery": float(current_mastery),
                "recommendation_score": float(combined_score),
                "status": "Ready" if readiness_mult > 0.7 else ("Locked" if readiness_mult < 0.2 else "Review Prereqs")
            })
            
        # Sort by recommendation score descending
        recommendations = sorted(recommendations, key=lambda x: x["recommendation_score"], reverse=True)
        return recommendations[:top_k]
