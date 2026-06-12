import React from "react";

// Fixed positions for CS topics in our graph space (800x400)
const NODE_POSITIONS = {
  "Arrays": { x: 80, y: 200 },
  "Strings": { x: 220, y: 100 },
  "Hashing": { x: 220, y: 300 },
  "Sliding Window": { x: 420, y: 100 },
  "Two Pointers": { x: 420, y: 200 },
  "Trees": { x: 420, y: 300 },
  "Graphs": { x: 620, y: 300 },
  "Dynamic Programming": { x: 620, y: 150 }
};

// Edges defining relationships in the knowledge graph
const EDGES = [
  { from: "Arrays", to: "Strings" },
  { from: "Arrays", to: "Hashing" },
  { from: "Arrays", to: "Trees" },
  { from: "Strings", to: "Sliding Window" },
  { from: "Strings", to: "Two Pointers" },
  { from: "Trees", to: "Graphs" },
  { from: "Trees", to: "Dynamic Programming" },
  { from: "Arrays", to: "Dynamic Programming" }
];

export default function KnowledgeGraph({ topics, selectedTopic, onSelectTopic, recommendations }) {
  // Build a fast lookup for student state per topic
  const topicMap = React.useMemo(() => {
    const map = {};
    if (topics) {
      topics.forEach(t => {
        map[t.topic] = t;
      });
    }
    return map;
  }, [topics]);

  // Check if topic is recommended
  const isRecommended = (topicName) => {
    return recommendations && recommendations.some(r => r.topic === topicName);
  };

  const getRecommendationRank = (topicName) => {
    if (!recommendations) return -1;
    return recommendations.findIndex(r => r.topic === topicName) + 1;
  };

  const getNodeColor = (topic) => {
    const state = topicMap[topic];
    if (!state) return { bg: "#27272a", text: "#a1a1aa", border: "#3f3f46" }; // default dark
    
    if (state.status === "Mastered") {
      return { bg: "rgba(22, 163, 74, 0.2)", text: "#4ade80", border: "#16a34a" }; // Green
    } else if (state.status === "Learning") {
      return { bg: "rgba(37, 99, 235, 0.2)", text: "#60a5fa", border: "#2563eb" }; // Blue
    } else if (state.status === "Ready") {
      return { bg: "rgba(6, 182, 212, 0.15)", text: "#22d3ee", border: "#06b6d4" }; // Cyan
    } else if (state.status === "Review Prereqs") {
      return { bg: "rgba(234, 179, 8, 0.1)", text: "#facc15", border: "#eab308" }; // Yellow
    } else {
      return { bg: "rgba(39, 39, 42, 0.4)", text: "#71717a", border: "#27272a" }; // Locked (Grey)
    }
  };

  return (
    <div className="w-full flex flex-col h-full">
      <div className="graph-header">
        <h2 className="text-xl font-semibold text-white">CS Prerequisite Knowledge Graph</h2>
        <div className="flex flex-wrap gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500"></span>
            <span className="text-zinc-400">Mastered (≥80%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-blue-500/20 border border-blue-500"></span>
            <span className="text-zinc-400">In Progress</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-cyan-500/20 border border-cyan-500"></span>
            <span className="text-zinc-400">Ready to Learn</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-yellow-500/10 border border-yellow-600"></span>
            <span className="text-zinc-400">Prereqs Needed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-zinc-800 border border-zinc-700"></span>
            <span className="text-zinc-400">Locked</span>
          </div>
        </div>
      </div>

      <div className="relative flex-1 bg-zinc-950/70 border border-zinc-800 rounded-xl overflow-hidden" style={{ minHeight: '350px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {/* SVG Canvas for drawing edges and nodes */}
        <svg className="w-full" style={{ display: 'block', height: 'auto', maxHeight: '400px' }} viewBox="0 0 760 400" preserveAspectRatio="xMidYMid meet">
          {/* Arrow markers for edges */}
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#3f3f46" />
            </marker>
            <marker id="arrow-active" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563eb" />
            </marker>
            {/* Glow effect filter */}
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Draw Connection Edges */}
          {EDGES.map((edge, idx) => {
            const start = NODE_POSITIONS[edge.from];
            const end = NODE_POSITIONS[edge.to];
            
            // Check if this connection pathway is actively studied (both nodes unlocked)
            const fromState = topicMap[edge.from];
            const toState = topicMap[edge.to];
            const isActivePath = fromState && toState && fromState.mastery > 0 && toState.status !== "Locked";
            
            return (
              <line
                key={`edge-${idx}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke={isActivePath ? "#3b82f6" : "#27272a"}
                strokeWidth={isActivePath ? 2.5 : 1.5}
                strokeDasharray={isActivePath ? "none" : "4 4"}
                markerEnd={`url(#${isActivePath ? "arrow-active" : "arrow"})`}
              />
            );
          })}

          {/* Draw Nodes */}
          {Object.entries(NODE_POSITIONS).map(([name, pos]) => {
            const colors = getNodeColor(name);
            const state = topicMap[name];
            const isSelected = selectedTopic === name;
            const recRank = getRecommendationRank(name);
            const isRec = recRank > 0;
            
            return (
              <g
                key={`node-${name}`}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => onSelectTopic(name)}
                className="cursor-pointer group"
              >
                {/* Glow ring if selected */}
                {isSelected && (
                  <circle
                    r="26"
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="3"
                    filter="url(#glow)"
                    opacity="0.8"
                    className="animate-pulse"
                  />
                )}

                {/* Outer Ring if Recommended */}
                {isRec && !isSelected && (
                  <circle
                    r="26"
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                    className="animate-spin"
                    style={{ animationDuration: "12s" }}
                  />
                )}

                {/* Main Node Circle */}
                <circle
                  r="20"
                  fill={colors.bg}
                  stroke={isSelected ? "#3b82f6" : colors.border}
                  strokeWidth={isSelected ? 3 : 2}
                  className="transition-all duration-300 group-hover:scale-110"
                />

                {/* Mastery Level Arc Indicator (Ring inside circle) */}
                {state && state.mastery > 0 && (
                  <circle
                    r="15"
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth="1.5"
                    strokeDasharray={`${state.mastery * 94} 94`}
                    transform="rotate(-90)"
                    opacity="0.5"
                  />
                )}

                {/* Recommendation Rank Label */}
                {isRec && (
                  <g transform="translate(14, -14)">
                    <circle r="7.5" fill="#22d3ee" />
                    <text
                      textAnchor="middle"
                      dy="2.5"
                      fill="#09090b"
                      fontSize="9"
                      fontWeight="bold"
                    >
                      {recRank}
                    </text>
                  </g>
                )}

                {/* Node Text Label (centered below node) */}
                <text
                  y="34"
                  textAnchor="middle"
                  fill={isSelected ? "#3b82f6" : colors.text}
                  fontSize="11"
                  fontWeight={isSelected || isRec ? "bold" : "medium"}
                  className="select-none transition-colors duration-200 group-hover:fill-zinc-100"
                >
                  {name}
                </text>

                {/* Subtext showing percentage */}
                {state && state.mastery > 0 && (
                  <text
                    y="46"
                    textAnchor="middle"
                    fill="#71717a"
                    fontSize="9"
                    className="select-none"
                  >
                    {Math.round(state.mastery * 100)}% mastery
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
