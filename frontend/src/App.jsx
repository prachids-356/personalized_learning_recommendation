import { useState, useEffect, useCallback } from "react";
import StudentProfile from "./components/StudentProfile";
import SimulationPanel from "./components/SimulationPanel";
import KnowledgeGraph from "./components/KnowledgeGraph";
import ForgettingCurve from "./components/ForgettingCurve";
import ProfileSetup from "./components/ProfileSetup";
import "./App.css";

const PREREQUISITES = {
  "Arrays": [],
  "Strings": ["Arrays"],
  "Hashing": ["Arrays"],
  "Sliding Window": ["Strings"],
  "Two Pointers": ["Strings"],
  "Trees": ["Arrays"],
  "Graphs": ["Trees"],
  "Dynamic Programming": ["Trees", "Arrays"]
};

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const [selectedStudentId] = useState(1);
  const [studentDetails, setStudentDetails] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [retentionData, setRetentionData] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState("Arrays");
  const [loading, setLoading] = useState(true);
  const [backendOffline, setBackendOffline] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [learningProfile, setLearningProfile] = useState(null);
  const [profileChecked, setProfileChecked] = useState(false);
  const [showProfileSetup, setShowProfileSetup] = useState(false);
  const [githubOAuthConfigured, setGithubOAuthConfigured] = useState(false);

  // Fetch student list on startup
  const fetchStudents = async () => {
    try {
      setBackendOffline(false);
      const res = await fetch(`${API_BASE}/api/students`);
      if (!res.ok) throw new Error("Failed to load student profiles");
      await res.json();
    } catch (err) {
      console.error(err);
      setBackendOffline(true);
    }
  };

  // Fetch full student dashboard details
  const fetchDashboardData = useCallback(async (studentId) => {
    if (backendOffline) return;
    setLoading(true);
    try {
      const [studentRes, recsRes, retentionRes] = await Promise.all([
        fetch(`${API_BASE}/api/student/${studentId}`),
        fetch(`${API_BASE}/api/recommendations/${studentId}`),
        fetch(`${API_BASE}/api/retention/${studentId}`)
      ]);

      if (!studentRes.ok || !recsRes.ok || !retentionRes.ok) {
        throw new Error("Failed to load dashboard statistics");
      }

      const details = await studentRes.json();
      const recs = await recsRes.json();
      const retention = await retentionRes.json();

      setStudentDetails(details);
      setRecommendations(recs);
      setRetentionData(retention);
      
      // Auto select first ready topic if current isn't ready
      if (details.topics) {
        const current = details.topics.find(t => t.topic === selectedTopic);
        if (!current || current.status === "Locked") {
          const firstReady = details.topics.find(t => t.status === "Ready" || t.status === "Learning");
          if (firstReady) {
            setSelectedTopic(firstReady.topic);
          }
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [backendOffline, selectedTopic]);

  useEffect(() => {
    // Data loading is an external synchronization boundary.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchStudents();
    fetch(`${API_BASE}/api/auth/me`, { credentials: "include" })
      .then(res => res.json())
      .then(data => setCurrentUser(data.user))
      .catch(err => console.error("Error loading signed-in user:", err));
    fetch(`${API_BASE}/api/profile`, { credentials: "include" })
      .then(res => res.json())
      .then(data => {
        const savedProfile = data || JSON.parse(localStorage.getItem("eduprime-learning-profile") || "null");
        setLearningProfile(savedProfile);
        setShowProfileSetup(!savedProfile && localStorage.getItem("eduprime-profile-skipped") !== "true");
        setProfileChecked(true);
      })
      .catch(err => {
        console.error("Error loading learning profile:", err);
        setProfileChecked(true);
      });
    fetch(`${API_BASE}/api/auth/github/status`)
      .then(res => res.json())
      .then(data => setGithubOAuthConfigured(data.oauth_configured))
      .catch(() => setGithubOAuthConfigured(false));
  }, []);

  useEffect(() => {
    if (selectedStudentId) {
      // Data loading is an external synchronization boundary.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchDashboardData(selectedStudentId);
    }
  }, [selectedStudentId, fetchDashboardData]);

  const handleGitHubLogin = () => {
    if (githubOAuthConfigured) {
      window.location.href = `${API_BASE}/api/auth/github/login`;
      return;
    }
    setShowProfileSetup(true);
  };

  const handleLogout = async () => {
    await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
    setCurrentUser(null);
  };

  const handleProfileComplete = async profile => {
    setLearningProfile(profile);
    setShowProfileSetup(false);
    localStorage.setItem("eduprime-learning-profile", JSON.stringify(profile));
    localStorage.removeItem("eduprime-profile-skipped");
    await fetchDashboardData(selectedStudentId);
  };

  const handleProfileSkip = () => {
    localStorage.setItem("eduprime-profile-skipped", "true");
    setShowProfileSetup(false);
  };

  const handlePracticeCompleted = async () => {
    await fetchDashboardData(selectedStudentId);
  };

  if (backendOffline) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col justify-center items-center text-zinc-100 p-6">
        <div className="glass-panel p-8 max-w-md text-center border border-red-500/20 bg-zinc-900/50">
          <svg className="w-16 h-16 text-red-500 mx-auto mb-4 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h1 className="text-2xl font-bold text-white mb-2">Backend Server Offline</h1>
          <p className="text-zinc-400 text-sm mb-6 leading-relaxed">
            The FastAPI recommendation engine is not accessible. Please ensure you have run the backend server on port 8000 using uvicorn.
          </p>
          <button
            onClick={() => { fetchStudents(); }}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold text-sm transition-all"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (profileChecked && showProfileSetup) {
    return (
      <ProfileSetup
        apiBase={API_BASE}
        initialProfile={learningProfile}
        onComplete={handleProfileComplete}
        onSkip={handleProfileSkip}
      />
    );
  }

  return (
    <div className="min-h-screen text-zinc-100 p-4 md:p-6 lg:p-8 max-w-7xl mx-auto flex flex-col gap-6">
      {/* Header Bar */}
      <header className="app-header">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400 bg-clip-text text-transparent">
            EduPrime AI
          </h1>
          <p className="text-zinc-400 text-sm mt-0.5 font-medium">
            Personalized Learning Paths & Spaced Memory Retention Engine
          </p>
          {learningProfile && (
            <p className="text-xs text-cyan-400/80 mt-2">
              Tuned for {learningProfile.goal || `${learningProfile.experience} practice`} using {[
                learningProfile.github && "GitHub",
                learningProfile.leetcode && "LeetCode",
                learningProfile.hackerrank && "HackerRank",
                learningProfile.geeksforgeeks && "GeeksforGeeks"
              ].filter(Boolean).join(", ") || "your dashboard activity"}.
            </p>
          )}
          {learningProfile?.github_analysis?.status === "analyzed" && (
            <p className="text-xs text-emerald-400/80 mt-1">
              GitHub signal: {learningProfile.github_analysis.public_repositories} public repos, focused on {learningProfile.github_analysis.languages.join(", ") || "no detected languages"}.
            </p>
          )}
          {learningProfile?.github_analysis?.status === "unavailable" && (
            <p className="text-xs text-yellow-400/80 mt-1">GitHub is connected, but its public data could not be reached yet. Your goal and linked platforms are still being used.</p>
          )}
        </div>
        
        <div className="flex items-center gap-3">
          {currentUser ? (
            <>
              <span className="text-xs text-zinc-400">Signed in as @{currentUser.login}</span>
              <button onClick={handleLogout} className="text-xs text-zinc-400 hover:text-white transition-colors">
                Sign out
              </button>
            </>
          ) : (
            <button onClick={handleGitHubLogin} className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">
              {learningProfile?.github ? "GitHub connected" : githubOAuthConfigured ? "Connect GitHub" : "Add GitHub profile"}
            </button>
          )}
          <button onClick={() => setShowProfileSetup(true)} className="text-xs text-zinc-400 hover:text-white transition-colors">
            {learningProfile ? "Edit profile" : "Set up profile"}
          </button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 bg-zinc-900/50 border border-zinc-800 px-3 py-1.5 rounded-full text-xs text-zinc-400">
            <svg className="animate-spin h-3.5 w-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Updating Dashboard State...
          </div>
        )}
      </header>

      {/* Main Grid Layout */}
      <main className="grid-container">
        {/* Left Column - Student Profile & Stats */}
        <div className="sidebar-column">
          <StudentProfile
            studentDetails={studentDetails}
            retentionInfo={retentionData?.retention_status}
            onSelectTopic={setSelectedTopic}
          />
          <SimulationPanel
            selectedTopic={selectedTopic}
            studentId={selectedStudentId}
            topics={studentDetails?.topics}
            onPracticeCompleted={handlePracticeCompleted}
          />
        </div>

        {/* Right Column - Recommendation Roadmap & Visualizations */}
        <div className="main-column">
          {/* Top Recommendations Banner */}
          <div className="glass-panel p-5 bg-gradient-to-br from-zinc-900/40 to-blue-950/10 border border-zinc-800">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-400 mb-3">
              AI Next-Item Study Recommendations
            </h3>
            
            <div className="recommendations-list">
              {recommendations && recommendations.length > 0 ? (
                recommendations.map((rec, idx) => (
                  <div
                    key={`rec-${rec.topic}`}
                    onClick={() => setSelectedTopic(rec.topic)}
                    className={`recommendation-row ${
                      selectedTopic === rec.topic ? "active-row" : ""
                    }`}
                  >
                    {/* Left Section: Rank and Topic */}
                    <div className="rec-left-section">
                      <span className="rank-badge">Rank #{idx + 1}</span>
                      <div>
                        <h4 className="rec-title">{rec.topic}</h4>
                        <span className="rec-status-tag">{rec.status}</span>
                      </div>
                    </div>

                    {/* Middle Section: Prerequisites */}
                    <div className="rec-mid-section">
                      <span className="rec-label">Prerequisites:</span>
                      <span className="rec-val">
                        {PREREQUISITES[rec.topic]?.join(" → ") || "None"}
                      </span>
                    </div>

                    {/* Right Section: SVD & Readiness Scores */}
                    <div className="rec-right-section">
                      <div>
                        <span className="score-label">SVD Pref:</span>
                        <span className="score-val">{Math.round(rec.cf_score * 100)}%</span>
                      </div>
                      <div>
                        <span className="score-label">Readiness:</span>
                        <span className="score-val">{Math.round(rec.readiness * 100)}%</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-zinc-500 text-xs py-4 text-center">
                  All concepts fully mastered!
                </div>
              )}
            </div>
          </div>

          {/* Knowledge Graph Card */}
          <div className="glass-panel p-5 bg-zinc-900/60 border border-zinc-800">
            <KnowledgeGraph
              topics={studentDetails?.topics}
              selectedTopic={selectedTopic}
              onSelectTopic={setSelectedTopic}
              recommendations={recommendations}
            />
          </div>

          {/* Forgetting Curve Graph Card */}
          <div className="glass-panel p-5 bg-zinc-900/60 border border-zinc-800">
            <ForgettingCurve
              curves={retentionData?.forgetting_curves}
              selectedTopic={selectedTopic}
              retentionStatus={retentionData?.retention_status}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
