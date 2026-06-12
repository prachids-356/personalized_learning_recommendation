import React, { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function SimulationPanel({ selectedTopic, studentId, topics, onPracticeCompleted }) {
  const [topic, setTopic] = useState("");
  const [correct, setCorrect] = useState(true);
  const [timeTaken, setTimeTaken] = useState(90);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [daysElapsed, setDaysElapsed] = useState(0.0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);

  // Sync with selectedTopic from graph
  useEffect(() => {
    if (selectedTopic) {
      setTopic(selectedTopic);
    } else if (topics && topics.length > 0) {
      setTopic(topics[0].topic);
    }
  }, [selectedTopic, topics]);

  // Fetch success prediction dynamically from ASSISTments GBDT model
  useEffect(() => {
    if (!topic || !studentId) return;
    
    const fetchPrediction = async () => {
      setPredicting(true);
      try {
        const res = await fetch(`${API_BASE}/api/performance/predict`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            student_id: studentId,
            topic: topic,
            hints_used: hintsUsed,
            attempts_count: correct ? 1 : 2
          })
        });
        if (res.ok) {
          const data = await res.json();
          setPrediction(data);
        }
      } catch (err) {
        console.error("Error predicting performance:", err);
      } finally {
        setPredicting(false);
      }
    };

    fetchPrediction();
  }, [studentId, topic, hintsUsed, correct]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const payload = {
      student_id: studentId,
      topic: topic,
      correct: correct ? 1 : 0,
      attempts_count: correct ? 1 : Math.max(2, Math.floor(Math.random() * 3) + 2), // failure implies multiple attempts
      time_taken: parseInt(timeTaken),
      hints_used: parseInt(hintsUsed),
      days_elapsed: parseFloat(daysElapsed)
    };

    try {
      const response = await fetch(`${API_BASE}/api/practice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error("Failed to submit practice interaction");
      }

      // Success
      setDaysElapsed(0.0); // Reset time elapsed slider
      if (onPracticeCompleted) {
        await onPracticeCompleted();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const getTopicStatus = () => {
    if (!topics || !topic) return null;
    return topics.find(t => t.topic === topic);
  };

  const currentStatus = getTopicStatus();

  return (
    <div className="w-full flex flex-col glass-panel p-5 bg-zinc-900/60 border border-zinc-800 text-zinc-100">
      <h2 className="text-xl font-semibold text-white mb-2">Practice Simulator Sandbox</h2>
      <p className="text-zinc-400 text-xs mb-4">
        Simulate a student solving problems. Submitting will update the student log and retrain the ML model instantly!
      </p>

      <form onSubmit={handleSubmit} className="space-y-4 flex-1 flex flex-col justify-between">
        <div className="space-y-3">
          {/* Topic Selector */}
          <div>
            <label className="block text-xs text-zinc-500 font-medium mb-1">Select CS Topic</label>
            <select
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-lg py-2 px-3 text-sm text-zinc-200 focus:outline-none focus:border-blue-500"
            >
              {topics && topics.map(t => (
                <option key={t.topic} value={t.topic}>
                  {t.topic} {t.mastery > 0 ? `(${Math.round(t.mastery * 100)}% Mastered)` : ""}
                </option>
              ))}
            </select>
            {currentStatus && (
              <div className="mt-1 text-[10px] flex items-center justify-between text-zinc-500 px-1">
                <span>Prerequisites: {currentStatus.prerequisites.join(", ") || "None"}</span>
                <span className={
                  currentStatus.status === "Mastered" ? "text-green-400" :
                  currentStatus.status === "Locked" ? "text-red-400" :
                  "text-cyan-400"
                }>
                  Status: {currentStatus.status}
                </span>
              </div>
            )}
          </div>

          {/* Outcome Toggle */}
          <div>
            <label className="block text-xs text-zinc-500 font-medium mb-1.5">Problem Solving Outcome</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setCorrect(true)}
                className={`py-2 px-3 text-sm font-medium rounded-lg border transition-all ${
                  correct
                    ? "bg-green-500/20 border-green-500 text-green-400"
                    : "bg-zinc-950 border-zinc-800 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Correct / Recalled
              </button>
              <button
                type="button"
                onClick={() => setCorrect(false)}
                className={`py-2 px-3 text-sm font-medium rounded-lg border transition-all ${
                  !correct
                    ? "bg-red-500/20 border-red-500 text-red-400"
                    : "bg-zinc-950 border-zinc-800 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Incorrect / Forgotten
              </button>
            </div>
          </div>

          {/* Time Taken Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs text-zinc-500 font-medium">Time Taken (Seconds)</label>
              <span className="text-xs font-semibold text-zinc-300">{timeTaken}s</span>
            </div>
            <input
              type="range"
              min="15"
              max="600"
              step="15"
              value={timeTaken}
              onChange={(e) => setTimeTaken(e.target.value)}
              className="w-full h-1 bg-zinc-850 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>

          {/* Hints Used */}
          <div>
            <label className="block text-xs text-zinc-500 font-medium mb-1">Hints Requested</label>
            <div className="grid grid-cols-4 gap-2">
              {[0, 1, 2, 3].map(h => (
                <button
                  key={`hint-${h}`}
                  type="button"
                  onClick={() => setHintsUsed(h)}
                  className={`py-1.5 text-xs font-medium rounded-lg border transition-all ${
                    hintsUsed === h
                      ? "bg-blue-500/20 border-blue-500 text-blue-400"
                      : "bg-zinc-950 border-zinc-800 text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {h} {h === 1 ? "Hint" : "Hints"}
                </button>
              ))}
            </div>
          </div>

          {/* Time Lapse Simulator (Days Elapsed) */}
          <div className="bg-zinc-950/40 p-2.5 rounded-lg border border-zinc-850">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-yellow-500 font-medium flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Time Travel: Days Elapsed
              </span>
              <span className="text-xs font-bold text-yellow-500">{daysElapsed.toFixed(1)} Days</span>
            </div>
            <p className="text-[10px] text-zinc-500 mb-2 leading-snug">
              Simulate memory decay by pretending a period of time has passed since their *last* activity.
            </p>
            <input
              type="range"
              min="0"
              max="15"
              step="0.5"
              value={daysElapsed}
              onChange={(e) => setDaysElapsed(parseFloat(e.target.value))}
              className="w-full h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-yellow-600"
            />
          </div>
        </div>

        {/* Live Predictor Box */}
        {prediction && (
          <div className="p-3 rounded-lg border border-blue-900/40 bg-blue-950/20 flex items-center justify-between text-xs mt-2">
            <div className="flex flex-col">
              <span className="text-zinc-400 font-medium">AI Probability of Success:</span>
              <span className="text-[9px] text-zinc-500">Based on historical learning paths</span>
            </div>
            <div className="text-right">
              <span className={`text-base font-extrabold block ${
                prediction.probability_correct >= 0.85 ? "text-emerald-400" :
                prediction.probability_correct >= 0.60 ? "text-yellow-500" :
                "text-red-400"
              }`}>
                {Math.round(prediction.probability_correct * 100)}%
              </span>
              <span className="text-[9px] text-zinc-500 block">Chance of Recall</span>
            </div>
          </div>
        )}

        <div className="pt-4 mt-auto">
          {error && <div className="text-xs text-red-400 bg-red-950/20 border border-red-900/40 p-2 rounded-lg mb-3">{error}</div>}
          <button
            type="submit"
            disabled={submitting || (currentStatus && currentStatus.status === "Locked")}
            className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm transition-all flex justify-center items-center gap-2 ${
              currentStatus && currentStatus.status === "Locked"
                ? "bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700"
                : "bg-blue-600 hover:bg-blue-500 text-white cursor-pointer active:scale-98"
            }`}
          >
            {submitting ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Retraining ML Model...
              </>
            ) : currentStatus && currentStatus.status === "Locked" ? (
              "Topic Locked (Resolve Prereqs First)"
            ) : (
              "Submit Learning Attempt"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
