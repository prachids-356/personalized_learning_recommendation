import React, { useState, useEffect } from "react";

export default function StudentProfile({
  studentDetails,
  studentsList,
  selectedStudentId,
  onStudentChange,
  retentionInfo,
  onSelectTopic
}) {
  const [modelInfo, setModelInfo] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/performance/model-info")
      .then(res => res.json())
      .then(data => setModelInfo(data))
      .catch(err => console.error("Error loading model info:", err));
  }, []);

  if (!studentDetails) return null;

  const { stats, ability, forgetting_rate } = studentDetails;
  
  // Find topics that need revision
  const revisionQueue = retentionInfo
    ? retentionInfo.filter(item => item.should_revise)
    : [];

  return (
    <div className="w-full flex flex-col glass-panel p-5 bg-zinc-900/60 border border-zinc-800 text-zinc-100">
      <div className="profile-header">
        <div>
          <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Active Profile</span>
          <div className="flex items-center gap-2 mt-0.5">
            <h2 className="text-xl font-bold text-white">Student #{selectedStudentId}</h2>
          </div>
        </div>
        
        {/* Student Selector */}
        <div>
          <label className="block text-[10px] text-zinc-500 font-medium mb-1">Switch Student Profile</label>
          <select
            value={selectedStudentId}
            onChange={(e) => onStudentChange(parseInt(e.target.value))}
            className="bg-zinc-950 border border-zinc-800 rounded-lg py-1.5 px-3 text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
          >
            {studentsList && studentsList.map(s => (
              <option key={s.student_id} value={s.student_id}>
                Student #{s.student_id} (Ability: {s.ability.toFixed(2)})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Model Latent Variables Card */}
      <div className="latent-stats">
        <div>
          <div className="text-zinc-500 font-medium">True Learning Ability</div>
          <div className="text-lg font-bold text-emerald-400 mt-0.5">
            {ability.toFixed(2)}x
          </div>
          <p className="text-[9px] text-zinc-500 mt-0.5">Influences base mastery acquisition rate.</p>
        </div>
        <div>
          <div className="text-zinc-500 font-medium">Forgetting Decay Rate</div>
          <div className="text-lg font-bold text-yellow-500 mt-0.5">
            {forgetting_rate.toFixed(3)}/day
          </div>
          <p className="text-[9px] text-zinc-500 mt-0.5">Influences memory half-life decay speed.</p>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="text-[10px] text-zinc-500 font-medium block">Concept Completion</span>
          <span className="text-xl font-bold text-white block mt-0.5">
            {studentDetails.topics ? studentDetails.topics.filter(t => t.mastery >= 0.8).length : 0} / 8
          </span>
          <div className="progress-bg h-1 mt-2">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all duration-500"
              style={{
                width: `${
                  studentDetails.topics
                    ? (studentDetails.topics.filter(t => t.mastery >= 0.8).length / 8) * 100
                    : 0
                }%`
              }}
            ></div>
          </div>
        </div>

        <div className="metric-card">
          <span className="text-[10px] text-zinc-500 font-medium block">Solving Accuracy</span>
          <span className="text-xl font-bold text-white block mt-0.5">
            {Math.round(stats.avg_accuracy * 100)}%
          </span>
          <span className="text-[9px] text-zinc-500 block mt-0.5">Across {stats.total_attempts} total logs</span>
        </div>
      </div>

      {/* Spaced Repetition Revision Queue */}
      <div className="flex-1 flex flex-col min-h-[140px] mb-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Spaced Repetition Queue ({revisionQueue.length})
          </h3>
          {revisionQueue.length > 0 && (
            <span className="text-[9px] bg-red-950 text-red-400 border border-red-900/60 px-1.5 py-0.5 rounded-full font-bold animate-pulse">
              Revise Needed
            </span>
          )}
        </div>

        <div className="queue-list">
          {revisionQueue.length > 0 ? (
            revisionQueue.map((item) => (
              <div
                key={`queue-${item.topic}`}
                onClick={() => onSelectTopic(item.topic)}
                className="flex justify-between items-center p-2 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-red-500/40 hover:bg-zinc-850 transition-all cursor-pointer group"
              >
                <div>
                  <span className="text-xs font-semibold text-zinc-200 group-hover:text-white">
                    {item.topic}
                  </span>
                  <span className="text-[10px] text-zinc-500 block">
                    Practiced {item.days_since_last_practice.toFixed(1)} days ago
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-red-400 block">
                    {Math.round(item.retention_probability * 100)}%
                  </span>
                  <span className="text-[9px] text-zinc-500 block">Retention</span>
                </div>
              </div>
            ))
          ) : (
            <div className="h-full flex flex-col justify-center items-center text-center p-4">
              <svg className="w-8 h-8 text-zinc-700 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-zinc-500 text-xs">All memory levels stable!</span>
              <span className="text-[9px] text-zinc-600">No revisions recommended today.</span>
            </div>
          )}
        </div>
      </div>

      {/* AI Performance Predictor Diagnostics */}
      {modelInfo && (
        <div className="p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/10 text-xs flex flex-col gap-2 mt-auto">
          <div className="flex justify-between items-center">
            <span className="font-semibold text-cyan-400 uppercase tracking-wider text-[10px]">AI Performance Predictor</span>
            <span className="text-[9px] bg-cyan-950 text-cyan-400 border border-cyan-500/50 px-2 py-0.5 rounded-full font-bold">
              {modelInfo.model_loaded ? "GBDT Loaded" : "Offline fallback"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-1">
            <div>
              <span className="text-zinc-500 block">Dataset Reference:</span>
              <span className="text-zinc-300 font-semibold">{modelInfo.dataset}</span>
            </div>
            <div>
              <span className="text-zinc-500 block">Model Type:</span>
              <span className="text-zinc-300 font-semibold">{modelInfo.model_name}</span>
            </div>
            <div>
              <span className="text-zinc-500 block">Eval Accuracy:</span>
              <span className="text-emerald-400 font-bold">{(modelInfo.accuracy * 100).toFixed(2)}%</span>
            </div>
            <div>
              <span className="text-zinc-500 block">ROC-AUC Score:</span>
              <span className="text-emerald-400 font-bold">{modelInfo.auc_score.toFixed(4)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
