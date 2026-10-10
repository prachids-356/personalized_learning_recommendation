# EduPrime AI: Personalized Learning Path Recommender & Spaced Memory Engine

EduPrime AI is a production-grade educational engine that combines **hybrid collaborative filtering + prerequisite knowledge graph recommendations** with **machine learning spaced repetition forecasting** to deliver optimized study pathways. 

The system leverages the real-world **Kaggle ASSISTments 2009-2010 dataset** to predict student task outcomes with high precision.

---

## 🚀 Key Features

1. **AI Performance Predictor (91.21% Accuracy)**:
   - Built with a `HistGradientBoostingClassifier` trained on **150,000 learning interactions** from the ASSISTments dataset.
   - Computes sequential student metrics: global skill accuracy, historical student success rate, first action (hints request tracking), and concept experience count (`opportunity`).
   - Evaluated on unseen test logs with **91.21% classification accuracy** and **0.9116 ROC-AUC**.

2. **CS Prerequisite Knowledge Graph**:
   - Models CS algorithm topics: `Arrays` $\rightarrow$ `Strings` $\rightarrow$ `Hashing` $\rightarrow$ `Sliding Window` $\rightarrow$ `Two Pointers` $\rightarrow$ `Trees` $\rightarrow$ `Graphs` $\rightarrow$ `Dynamic Programming`.
   - Recommends topics by scaling latent user preferences with prerequisite mastery coefficients (smooth quadratic penalty for strictness).

3. **Memory Decay & Spaced Repetition**:
   - Implements Duolingo's **Half-Life Regression (HLR)** model in pure NumPy using gradient descent to predict concept recall half-lives:
     $$P(\text{recall}) = 2^{-\Delta t / h}$$
   - Monitors student memory levels and automatically routes fading concepts (<60% retention probability) into a revision queue.

4. **Aesthetic Responsive Dashboard**:
   - Dark-mode dashboard built with React + Vite and custom glassmorphism Vanilla CSS.
   - Renders interactive SVGs of the CS prerequisite roadmap and Ebbinghaus forgetting curves.
   - Includes a sandbox simulation terminal to practice concepts, fast-forward time (time travel), and see predictions adjust dynamically.

---

## 📂 Project Structure

```text
personalized-learning-engine/
├── backend/
│   ├── main.py                 # FastAPI application & API router
│   ├── requirements.txt        # Backend dependencies
│   ├── data/
│   │   ├── files/              # Local dataset caches and logs
│   │   ├── generator.py        # Synthetic student state & graph simulator
│   │   ├── preprocessor.py     # Feature engineering pipeline
│   │   └── train_assistments.py# ASSISTments GBDT training script
│   ├── models/
│   │   ├── assistments_model.pkl # Trained classifier binary
│   │   ├── recommender.py      # Collaborative SVD + Knowledge Graph
│   │   └── retention.py        # HLR Memory spaced repetition model
│   └── tests/
│       └── test_engine.py      # Unit testing suites
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ForgettingCurve.jsx # SVG memory decay charts
│   │   │   ├── KnowledgeGraph.jsx  # Interactive CS topic graph
│   │   │   ├── SimulationPanel.jsx # Practice simulator & AI predictor
│   │   │   └── StudentProfile.jsx  # Mastery metrics & GBDT stats
│   │   ├── App.jsx
│   │   ├── index.css           # Responsive Flexbox grid & styling
│   │   └── main.jsx
│   ├── index.html
│   └── vite.config.js
├── render.yaml                 # One-click Render configuration
└── README.md
```

---

## 🛠️ Local Setup Instructions

### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the ML pipeline to download the ASSISTments dataset, engineer sequential features, train the GBDT classifier, and save the binary locally:
   ```bash
   python data/train_assistments.py
   ```
4. Start the FastAPI uvicorn server:
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

The API creates `backend/data/files/learning_engine.db` on first startup and imports the generated CSV seed data into SQLite. Set `DATABASE_PATH` to place the database elsewhere. For managed PostgreSQL, set `DATABASE_URL`; it takes precedence over SQLite. Set `FRONTEND_ORIGIN` to the exact deployed frontend origin, such as `https://your-dashboard.onrender.com`.

### 2. Frontend Setup (React + Vite)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Start the local Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to [http://localhost:5173/](http://localhost:5173/).

---

## 🌐 API Endpoints

### Performance Predictor (ASSISTments)
* `GET /api/performance/model-info`: Exposes training metrics (accuracy, ROC-AUC) and feature mappings.
* `POST /api/performance/predict`: Predicts target success likelihood for an attempt given context variables.
  - Payload: `{"student_id": 1, "topic": "Arrays", "hints_used": 0, "attempts_count": 1}`

### Recommendation & Spaced Repetition Engine
* `GET /api/students`: Lists active student profiles.
* `GET /api/student/{student_id}`: Returns mastery scores, completion metrics, and readiness logs.
* `GET /api/recommendations/{student_id}`: Returns top-3 ranked CS learning suggestions.
* `GET /api/retention/{student_id}`: Returns forgetting curves and revision schedules.
* `POST /api/practice`: Adds student logs, adjusts timestamps (time-travel simulator), and triggers model retraining.

---

## ☁️ Free-Tier Cloud Deployment Guide

### Backend: FastAPI on Render (No card required)
1. Register on **[Render.com](https://render.com/)** and log in.
2. Select **New +** -> **Web Service**.
3. Link your GitHub repository.
4. Set configurations:
   - **Build Command**: `pip install -r backend/requirements.txt && python backend/data/train_assistments.py`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Select the **Free** tier.
5. Configure `FRONTEND_ORIGIN` with the deployed frontend URL.
6. Keep the persistent disk enabled in `render.yaml`. Without it, SQLite data is lost whenever the service is redeployed or restarted.
7. Verify `https://your-backend-url/health` returns `{"status":"ok"}`.

### Frontend: Vite on Vercel (No card required)
1. Sign up/log in on **[Vercel.com](https://vercel.com/)** using your GitHub account.
2. Click **Add New** -> **Project** and import your repository.
3. Configure the settings:
   - **Root Directory**: Select `frontend`.
    - **Environment Variables**: Add one variable:
     - **Name**: `VITE_API_URL`
     - **Value**: Your Render backend URL (e.g., `https://personalized-learning-backend.onrender.com`)
4. Click **Deploy**.

### Production notes

- Streamlit is not needed for this product. The React dashboard is the user-facing application and the FastAPI service owns model inference and learning state.
- SQLite with a persistent disk is suitable for a single backend instance. For multiple instances, concurrent writes, or a larger user base, set `DATABASE_URL` to managed PostgreSQL.
- The `/health` endpoint is intended for Render health checks and uptime monitoring.
- Add authentication and authorization before exposing student records to real users; the current demo API intentionally has no identity layer.
- GitHub sign-in is available through `/api/auth/github/login`. Create a GitHub OAuth App and configure `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `SESSION_SECRET`, and `COOKIE_SECURE=true`. The callback URL must be `https://your-backend-url/api/auth/github/callback`.

### Continuous integration

GitHub Actions runs on pushes and pull requests through `.github/workflows/ci.yml`. It compiles the backend, runs the Python test suite, lints and builds the frontend, and audits production npm dependencies.

### Learner onboarding

The dashboard opens with a profile setup view where learners can provide a goal, experience level, and any combination of GitHub, LeetCode, HackerRank, and GeeksforGeeks profile URLs. The profile is stored in the current session and can be edited later from the dashboard. External profile analysis is the next personalization layer; the current simulator data remains available through “Use demo profile for now.”

GitHub profiles are analyzed through the public GitHub API for public repository count, followers, and detected repository languages. LeetCode, HackerRank, and GeeksforGeeks links are recorded as connected sources and used as context; their private or anti-automated activity is not scraped. Unavailable external APIs do not block the learner experience.
