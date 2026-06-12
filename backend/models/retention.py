import numpy as np
import pandas as pd

class SpacedRepetitionModel:
    def __init__(self, alpha=0.01, lr=0.05, epochs=500):
        self.alpha = alpha  # L2 regularization strength
        self.lr = lr        # learning rate
        self.epochs = epochs
        self.theta = None   # Model weights: [revision_count, prior_accuracy, difficulty, last_attempt_correct, bias]
        self.is_trained = False
        
    def _extract_matrices(self, X_df, y_series):
        # Extract features
        revision_count = X_df["revision_count"].values
        prior_accuracy = X_df["prior_accuracy"].values
        difficulty = X_df["difficulty"].values
        last_attempt_correct = X_df["last_attempt_correct"].values
        
        # Add bias term (column of 1s)
        bias = np.ones_like(revision_count)
        
        # Design matrix X_mat of shape (M, 5)
        X_mat = np.column_stack([
            revision_count,
            prior_accuracy,
            difficulty,
            last_attempt_correct,
            bias
        ])
        
        # delta_t is the days since last practice
        delta_t = X_df["days_since_last_revision"].values
        y = y_series.values
        
        return X_mat, delta_t, y

    def fit(self, X, y):
        """
        Trains the Duolingo style Half-Life Regression (HLR) model using pure NumPy Gradient Descent.
        """
        if X.empty or len(y) == 0:
            return self
            
        X_mat, delta_t, y_val = self._extract_matrices(X, y)
        M, D = X_mat.shape
        
        # Initialize weights
        # We initialize bias weight to 1.0 so the baseline memory half-life is 2^1.0 = 2.0 days
        self.theta = np.zeros(D)
        self.theta[4] = 1.0  # bias
        
        ln2 = np.log(2.0)
        
        for epoch in range(self.epochs):
            # Compute predicted half-life: h = 2^(theta . x)
            # Clip h to prevent division by zero or overflows
            h = 2.0 ** (X_mat @ self.theta)
            h = np.clip(h, 0.1, 100.0)
            
            # Compute predicted recall probability: p = 2^(-delta_t / h)
            p = 2.0 ** (-delta_t / h)
            p = np.clip(p, 1e-6, 1.0 - 1e-6)
            
            # Loss derivative w.r.t theta:
            # L = sum((p - y)^2) + alpha * ||theta||^2
            # dp/dtheta = p * (ln 2)^2 * delta_t / h * x
            error = p - y_val
            grad_coef = 2.0 * error * p * (ln2 ** 2) * (delta_t / h)
            
            # Gradient w.r.t theta
            grad = (X_mat.T @ grad_coef) + 2.0 * self.alpha * self.theta
            
            # Update weights
            self.theta -= self.lr * grad
            
        self.is_trained = True
        return self
        
    def predict_half_life(self, student_features_dict):
        """
        Directly predicts the memory half-life (h) in days: h = 2^(theta . x).
        """
        if not self.is_trained:
            return float(self._heuristic_half_life(
                student_features_dict.get("revision_count", 0),
                student_features_dict.get("prior_accuracy", 0.8),
                student_features_dict.get("difficulty", 0.3)
            ))
            
        # Build features vector: [revision_count, prior_accuracy, difficulty, last_attempt_correct, bias]
        x = np.array([
            student_features_dict.get("revision_count", 0),
            student_features_dict.get("prior_accuracy", 0.8),
            student_features_dict.get("difficulty", 0.3),
            student_features_dict.get("last_attempt_correct", 1),
            1.0  # bias
        ])
        
        h = 2.0 ** np.dot(self.theta, x)
        return float(np.clip(h, 0.5, 90.0))  # Bound between 12 hours and 90 days
        
    def predict_retention_probability(self, student_features_dict, days_elapsed):
        """
        Predicts the recall probability after days_elapsed using p = 2^(-days_elapsed / h).
        """
        h = self.predict_half_life(student_features_dict)
        prob = 2.0 ** (-days_elapsed / h)
        return float(prob)
        
    def _heuristic_half_life(self, revision_count, prior_accuracy, difficulty):
        """
        Fall-back heuristic Duolingo HLR model.
        Memory half-life increases with revision count, is higher for high accuracy,
        and is lower for complex concepts.
        """
        base_h = 2.0  # base half-life of 2 days
        difficulty_penalty = 1.0 - (difficulty * 0.5)  # up to 50% penalty for hard topics
        accuracy_bonus = 0.5 + prior_accuracy  # e.g., 100% accuracy = 1.5x bonus
        
        h = base_h * (1.8 ** revision_count) * difficulty_penalty * accuracy_bonus
        return max(1.0, min(90.0, h)) # Clamp between 1 day and 90 days
