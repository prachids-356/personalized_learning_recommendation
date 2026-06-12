import os
import shutil
import tempfile
import unittest
import pandas as pd
import numpy as np

# Ensure backend is in import path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.data.generator import generate_synthetic_data, PREREQUISITES
from backend.data.preprocessor import compute_mastery_matrix, prepare_retention_features
from backend.models.recommender import HybridRecommender
from backend.models.retention import SpacedRepetitionModel

class TestLearningEngine(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Generate synthetic data for testing
        print("Generating synthetic data for tests...")
        cls.students_df, cls.logs_df, cls.retention_df = generate_synthetic_data(num_students=5, seed=42)
        
    def test_generator_outputs(self):
        # Verify the structure of the dataframes
        self.assertFalse(self.students_df.empty)
        self.assertFalse(self.logs_df.empty)
        self.assertFalse(self.retention_df.empty)
        
        self.assertIn("student_id", self.students_df.columns)
        self.assertIn("ability", self.students_df.columns)
        
        self.assertIn("user_id", self.logs_df.columns)
        self.assertIn("topic", self.logs_df.columns)
        self.assertIn("correct", self.logs_df.columns)
        
        self.assertIn("user_id", self.retention_df.columns)
        self.assertIn("recalled", self.retention_df.columns)
        self.assertIn("days_since_last_revision", self.retention_df.columns)
        
    def test_preprocessor(self):
        # Mastery matrix
        mastery = compute_mastery_matrix(self.logs_df)
        self.assertFalse(mastery.empty)
        self.assertEqual(len(mastery), 5)  # 5 students
        
        # Verify topics are columns
        for topic in PREREQUISITES.keys():
            self.assertIn(topic, mastery.columns)
            
        # Verify values are between 0 and 1
        self.assertTrue((mastery.values >= 0).all())
        self.assertTrue((mastery.values <= 1).all())
        
        # Retention features
        X, y = prepare_retention_features(self.retention_df)
        self.assertFalse(X.empty)
        self.assertEqual(len(X), len(self.retention_df))
        self.assertIn("revision_count", X.columns)
        self.assertIn("difficulty", X.columns)
        
    def test_recommender(self):
        mastery = compute_mastery_matrix(self.logs_df)
        recommender = HybridRecommender(n_components=2)
        recommender.fit(mastery)
        
        student_id = 1
        student_mastery_dict = mastery.loc[student_id].to_dict()
        
        recs = recommender.recommend(student_id, student_mastery_dict, top_k=3)
        
        self.assertTrue(len(recs) > 0)
        self.assertTrue(len(recs) <= 3)
        
        # Verify recommendation structure
        first_rec = recs[0]
        self.assertIn("topic", first_rec)
        self.assertIn("recommendation_score", first_rec)
        self.assertIn("cf_score", first_rec)
        self.assertIn("readiness", first_rec)
        
        # Recommendations should be sorted by score descending
        scores = [r["recommendation_score"] for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
    def test_retention_model(self):
        X, y = prepare_retention_features(self.retention_df)
        model = SpacedRepetitionModel()
        model.fit(X, y)
        
        test_student_features = {
            "revision_count": 1,
            "prior_accuracy": 0.8,
            "difficulty": 0.3,
            "last_attempt_correct": 1
        }
        
        # Probability of recall should decrease as days elapsed increases
        prob_day1 = model.predict_retention_probability(test_student_features, 1.0)
        prob_day10 = model.predict_retention_probability(test_student_features, 10.0)
        
        print(f"Prob recall day 1: {prob_day1:.4f}, day 10: {prob_day10:.4f}")
        self.assertLessEqual(prob_day10, prob_day1)
        
        # Half life should be a positive float
        half_life = model.predict_half_life(test_student_features)
        print(f"Predicted half life: {half_life} days")
        self.assertGreater(half_life, 0)

if __name__ == "__main__":
    unittest.main()
