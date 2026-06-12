import React from "react";

export default function ForgettingCurve({ curves, selectedTopic, retentionStatus }) {
  if (!curves || Object.keys(curves).length === 0) {
    return (
      <div className="w-full h-full flex flex-col justify-center items-center text-center p-8 bg-zinc-950/40 border border-zinc-800 rounded-xl min-h-[300px]">
        <svg className="w-12 h-12 text-zinc-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <h3 className="text-zinc-400 font-medium mb-1">No Practice History Yet</h3>
        <p className="text-zinc-500 text-xs max-w-xs">
          Simulate solving a concept problem to see its memory retention forgetting curve.
        </p>
      </div>
    );
  }

  // Dimension configurations
  const width = 600;
  const height = 300;
  const paddingLeft = 50;
  const paddingRight = 30;
  const paddingTop = 20;
  const paddingBottom = 40;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  // Scale functions
  const scaleX = (day) => paddingLeft + (day / 14) * chartWidth;
  const scaleY = (prob) => paddingTop + (1.0 - prob) * chartHeight;

  // Colors for highlighted topic vs others
  const activeColor = "#06b6d4"; // cyan-500
  const inactiveColor = "rgba(63, 63, 70, 0.4)"; // zinc-700
  
  // Get active status details if available
  const activeStatus = retentionStatus && retentionStatus.find(s => s.topic === selectedTopic);

  // Generate SVG path string from points
  const generatePath = (points) => {
    return points
      .map((p, idx) => {
        const x = scaleX(p.day);
        const y = scaleY(p.probability);
        return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  };

  return (
    <div className="w-full flex flex-col h-full">
      <div className="graph-header">
        <div>
          <h2 className="text-xl font-semibold text-white">Memory Forgetting Curves</h2>
          <p className="text-zinc-400 text-xs mt-0.5">
            {"Ebbinghaus model projections: $P(\\text{recall}) = 2^{-\\Delta t / h}$"}
          </p>
        </div>
        {selectedTopic && curves[selectedTopic] && (
          <div className="text-right">
            <span className="text-xs text-zinc-500 block">Active Topic</span>
            <span className="text-sm font-semibold text-cyan-400">{selectedTopic}</span>
          </div>
        )}
      </div>

      <div className="curve-container">
        {/* SVG Drawing Area */}
        <div className="flex-1 relative" style={{ minHeight: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg className="w-full" style={{ display: 'block', height: 'auto', maxHeight: '300px' }} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
            {/* Grid Lines */}
            {/* Y Axis Grid lines (20%, 40%, 60%, 80%, 100%) */}
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((val) => {
              const y = scaleY(val);
              return (
                <g key={`y-grid-${val}`}>
                  <line
                    x1={paddingLeft}
                    y1={y}
                    x2={width - paddingRight}
                    y2={y}
                    stroke="#27272a"
                    strokeWidth="1"
                    strokeDasharray="2 4"
                  />
                  <text
                    x={paddingLeft - 8}
                    y={y + 4}
                    textAnchor="end"
                    fill="#71717a"
                    fontSize="10"
                  >
                    {Math.round(val * 100)}%
                  </text>
                </g>
              );
            })}

            {/* X Axis Grid lines (0, 2, 4, 6, 8, 10, 12, 14 days) */}
            {[0, 2, 4, 6, 8, 10, 12, 14].map((day) => {
              const x = scaleX(day);
              return (
                <g key={`x-grid-${day}`}>
                  <line
                    x1={x}
                    y1={paddingTop}
                    x2={x}
                    y2={height - paddingBottom}
                    stroke="#27272a"
                    strokeWidth="1"
                  />
                  <text
                    x={x}
                    y={height - paddingBottom + 16}
                    textAnchor="middle"
                    fill="#71717a"
                    fontSize="10"
                  >
                    d{day}
                  </text>
                </g>
              );
            })}

            {/* Revision Threshold Line (60% recall probability) */}
            <g>
              <line
                x1={paddingLeft}
                y1={scaleY(0.6)}
                x2={width - paddingRight}
                y2={scaleY(0.6)}
                stroke="rgba(239, 68, 68, 0.5)"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
              <text
                x={width - paddingRight - 8}
                y={scaleY(0.6) - 6}
                textAnchor="end"
                fill="#ef4444"
                fontSize="9"
                fontWeight="semibold"
                opacity="0.8"
              >
                Threshold (60%)
              </text>
            </g>

            {/* Curves for INACTIVE topics (drawn first, in background) */}
            {Object.entries(curves).map(([topic, points]) => {
              if (topic === selectedTopic) return null;
              return (
                <path
                  key={`curve-bg-${topic}`}
                  d={generatePath(points)}
                  fill="none"
                  stroke={inactiveColor}
                  strokeWidth="1.5"
                />
              );
            })}

            {/* Curve for ACTIVE topic (drawn on top, with glow) */}
            {selectedTopic && curves[selectedTopic] && (
              <g>
                {/* Underlay glow */}
                <path
                  d={generatePath(curves[selectedTopic])}
                  fill="none"
                  stroke={activeColor}
                  strokeWidth="5"
                  opacity="0.2"
                />
                {/* Solid path */}
                <path
                  d={generatePath(curves[selectedTopic])}
                  fill="none"
                  stroke={activeColor}
                  strokeWidth="3.5"
                />
                {/* Current elapsed time point */}
                {activeStatus && activeStatus.days_since_last_practice <= 14 && (
                  <circle
                    cx={scaleX(activeStatus.days_since_last_practice)}
                    cy={scaleY(activeStatus.retention_probability)}
                    r="5"
                    fill="#ef4444"
                    stroke="#ffffff"
                    strokeWidth="1.5"
                  />
                )}
              </g>
            )}
          </svg>
        </div>

        {/* Sidebar stats panel */}
        <div className="curve-sidebar">
          {selectedTopic && activeStatus ? (
            <div className="space-y-4">
              <div>
                <h4 className="text-zinc-400 font-medium">Memory Strength</h4>
                <div className="text-2xl font-bold text-white mt-0.5">
                  {Math.round(activeStatus.retention_probability * 100)}%
                </div>
                <span className="text-zinc-500 text-[10px]">Current Recall Chance</span>
              </div>
              <div>
                <h4 className="text-zinc-400 font-medium">Memory Half-Life</h4>
                <div className="text-lg font-bold text-cyan-400 mt-0.5">
                  {activeStatus.predicted_half_life_days.toFixed(1)} days
                </div>
                <span className="text-zinc-500 text-[10px]">Time to drop to 50%</span>
              </div>
              <div>
                <h4 className="text-zinc-400 font-medium">Last Revise</h4>
                <div className="text-zinc-300 font-medium mt-0.5">
                  {activeStatus.days_since_last_practice.toFixed(1)} days ago
                </div>
              </div>
              <div>
                <h4 className="text-zinc-400 font-medium">Revision Count</h4>
                <div className="text-zinc-300 font-medium mt-0.5">
                  {activeStatus.revision_count} practices
                </div>
              </div>
            </div>
          ) : (
            <div className="text-zinc-500 text-center py-4">
              Select a practiced topic in the graph or list to view retention diagnostics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
