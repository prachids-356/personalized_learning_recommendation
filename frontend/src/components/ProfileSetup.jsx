import { useState } from "react";

const EMPTY_PROFILE = {
  goal: "",
  experience: "beginner",
  github: "",
  leetcode: "",
  hackerrank: "",
  geeksforgeeks: ""
};

const PLATFORMS = [
  { key: "github", label: "GitHub", hint: "github.com/you" },
  { key: "leetcode", label: "LeetCode", hint: "leetcode.com/u/you" },
  { key: "hackerrank", label: "HackerRank", hint: "hackerrank.com/you" },
  { key: "geeksforgeeks", label: "GeeksforGeeks", hint: "geeksforgeeks.org/user/you" }
];

export default function ProfileSetup({ apiBase, initialProfile, onComplete, onSkip }) {
  const [profile, setProfile] = useState(initialProfile || EMPTY_PROFILE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const updateField = (field, value) => {
    setProfile(current => ({ ...current, [field]: value }));
  };

  const submit = async event => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/api/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(profile)
      });
      if (!response.ok) throw new Error("Could not save your learning profile");
      onComplete(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen text-zinc-100 p-6 flex items-center justify-center">
      <section className="glass-panel p-6 md:p-10 w-full max-w-3xl border border-zinc-800">
        <div className="max-w-xl mb-8">
          <span className="text-xs uppercase tracking-widest text-cyan-400">Personal setup</span>
          <h1 className="text-3xl md:text-4xl font-bold text-white mt-2">Build your learning profile</h1>
          <p className="text-zinc-400 mt-3 leading-relaxed">
            Add the places where you practice. Public GitHub profile links can be analyzed immediately; OAuth sign-in is available when the app is configured for it.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-6">
          <div className="grid md:grid-cols-2 gap-4">
            <label className="block">
              <span className="block text-xs text-zinc-400 mb-2">What are you working toward?</span>
              <input value={profile.goal} onChange={event => updateField("goal", event.target.value)} placeholder="e.g. prepare for backend interviews" className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-500" maxLength={160} />
            </label>
            <label className="block">
              <span className="block text-xs text-zinc-400 mb-2">Current experience</span>
              <select value={profile.experience} onChange={event => updateField("experience", event.target.value)} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-500">
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
          </div>

          <div>
            <div className="flex items-end justify-between mb-3">
              <div>
                <h2 className="text-sm font-semibold text-white">Practice profiles</h2>
                <p className="text-xs text-zinc-500 mt-1">Add as many as you use. Every field is optional.</p>
              </div>
              <span className="text-xs text-zinc-600">Private by default</span>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {PLATFORMS.map(platform => (
                <label key={platform.key} className="block">
                  <span className="block text-xs text-zinc-400 mb-2">{platform.label}</span>
                  <input value={profile[platform.key]} onChange={event => updateField(platform.key, event.target.value)} placeholder={platform.hint} className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-500" maxLength={300} />
                </label>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3 pt-2">
            <button type="button" onClick={onSkip} className="px-4 py-2.5 text-sm text-zinc-400 hover:text-white transition-colors">Use demo profile for now</button>
            <button type="submit" disabled={saving} className="px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-zinc-950 text-sm font-semibold transition-colors">{saving ? "Saving profile..." : "Continue to dashboard"}</button>
          </div>
        </form>
      </section>
    </main>
  );
}