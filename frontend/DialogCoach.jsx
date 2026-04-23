import { useState, useRef, useEffect } from "react";

// ─── Tiny design tokens ───────────────────────────────────────────────────────
const SCENARIOS = [
  { id: "coffee_chat",          label: "☕  Coffee Chat" },
  { id: "research_pitch",       label: "🔬  Research Pitch" },
  { id: "elevator_pitch",       label: "🛗  Elevator Pitch" },
  { id: "team_intro",           label: "👋  Team Intro" },
  { id: "interview_behavioral", label: "🎯  Behavioral Interview" },
  { id: "career_fair",          label: "🏢  Career Fair" },
];

const SCENARIO_DESC = {
  coffee_chat:          "Casual chat with an alum or mentor — build rapport, ask thoughtful questions, and leave a memorable impression.",
  research_pitch:       "~2-minute intro of your research to a professor — problem, approach, one result, and why it fits their group.",
  elevator_pitch:       "30–60 s pitch to a recruiter or investor — hook, credibility, concrete outcome, and a clear ask.",
  team_intro:           "First-day intro on an internship or project — relevant background, learning goals, and collaboration style.",
  interview_behavioral: "STAR-structure behavioral answer — clear situation, action, result, honest reflection, no clichés.",
  career_fair:          "Quick booth conversation — who you are, what you want, one concrete question, polite close.",
};

// ─── Score ring ───────────────────────────────────────────────────────────────
function ScoreRing({ score, label, color }) {
  const r = 30, c = 2 * Math.PI * r;
  const pct = (score / 5) * c;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <svg width={80} height={80} viewBox="0 0 80 80">
        <circle cx={40} cy={40} r={r} fill="none" stroke="#1e1e2e" strokeWidth={7} />
        <circle
          cx={40} cy={40} r={r} fill="none"
          stroke={color} strokeWidth={7}
          strokeDasharray={`${pct} ${c}`}
          strokeLinecap="round"
          transform="rotate(-90 40 40)"
          style={{ transition: "stroke-dasharray 0.8s cubic-bezier(.4,0,.2,1)" }}
        />
        <text x={40} y={46} textAnchor="middle"
          style={{ fill: "#e0def4", fontSize: 18, fontFamily: "'DM Mono', monospace", fontWeight: 700 }}>
          {score}
        </text>
      </svg>
      <span style={{ color: "#908caa", fontSize: 11, fontFamily: "'DM Mono', monospace", letterSpacing: "0.08em", textTransform: "uppercase" }}>{label}</span>
    </div>
  );
}

// ─── Badge ────────────────────────────────────────────────────────────────────
function Chip({ text, color }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 999,
      background: color + "22", color, fontSize: 12,
      fontFamily: "'DM Mono', monospace", border: `1px solid ${color}44`,
    }}>{text}</span>
  );
}

// ─── Collapsible section ──────────────────────────────────────────────────────
function Section({ title, icon, color, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{
      background: "#1e1e2e", borderRadius: 14,
      border: `1px solid ${open ? color + "55" : "#2a2a3e"}`,
      overflow: "hidden", transition: "border-color 0.2s",
    }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: "100%", display: "flex", alignItems: "center", gap: 10,
        padding: "14px 20px", background: "none", border: "none",
        cursor: "pointer", color: "#e0def4",
      }}>
        <span style={{ fontSize: 18 }}>{icon}</span>
        <span style={{ flex: 1, textAlign: "left", fontFamily: "'DM Mono', monospace", fontSize: 13, letterSpacing: "0.05em", color }}>{title}</span>
        <span style={{ color: "#908caa", fontSize: 14, transition: "transform 0.2s", display: "inline-block", transform: open ? "rotate(90deg)" : "rotate(0deg)" }}>›</span>
      </button>
      {open && (
        <div style={{ padding: "0 20px 18px", color: "#c4c2d4", fontSize: 14, lineHeight: 1.75 }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Stat pill row ────────────────────────────────────────────────────────────
function StatRow({ label, value, unit, warn }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #2a2a3e" }}>
      <span style={{ color: "#908caa", fontSize: 13 }}>{label}</span>
      <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 13, color: warn ? "#f6c177" : "#e0def4" }}>
        {value}<span style={{ color: "#908caa", fontSize: 11, marginLeft: 3 }}>{unit}</span>
      </span>
    </div>
  );
}

// ─── Parse feedback from Claude (very simple markdown-aware splitter) ─────────
function parseFeedback(text) {
  if (!text) return { raw: "" };
  // Extract rubric scores
  const scoreRx = /- (Delivery|Linguistic quality|Communication effectiveness):\s*(\d)/gi;
  const scores = {};
  let m;
  while ((m = scoreRx.exec(text)) !== null) {
    const k = m[1].toLowerCase().replace(/\s+/g, "_");
    scores[k] = parseInt(m[2]);
  }
  // Split into judge and improvement sections by the "---" separator
  const parts = text.split(/\n---\n/);
  return {
    judge: parts[0] || "",
    improvement: parts[1] || "",
    scores,
    raw: text,
  };
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function DialogCoach() {
  const [scenario, setScenario] = useState("coffee_chat");
  const [transcript, setTranscript] = useState("");
  const [wpm, setWpm] = useState("");
  const [fillers, setFillers] = useState("");
  const [pauses, setPauses] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [turn, setTurn] = useState(1);
  const [history, setHistory] = useState([]);
  const [tab, setTab] = useState("coach"); // "coach" | "history"
  const [jsonMode, setJsonMode] = useState(false);
  const resultRef = useRef(null);

  const scenarioText = SCENARIO_DESC[scenario];

  async function runCoach() {
    if (!transcript.trim()) return;
    setLoading(true);
    setResult(null);

    const analysis = {
      speech_rate: { words_per_min_speaking_only: wpm ? parseFloat(wpm) : null },
      pause_stats:  { pause_count: pauses ? parseInt(pauses) : null },
      filler_stats: { filler_total: fillers ? parseInt(fillers) : null },
    };

    const userContent = `## Scenario\n${scenarioText}\n\n## Transcript (turn ${turn})\n${transcript}\n\n## Delivery features\n\`\`\`json\n${JSON.stringify(analysis, null, 2)}\n\`\`\``;

    try {
      // Stage 1 – Judge
      const judgeRes = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: JUDGE_SYSTEM,
          messages: [{ role: "user", content: userContent }],
        }),
      });
      const judgeData = await judgeRes.json();
      const judgeText = judgeData.content?.find(b => b.type === "text")?.text || "";

      // Stage 2 – Improve
      const improveRes = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          system: IMPROVE_SYSTEM,
          messages: [{ role: "user", content: `${userContent}\n\n## Judge evaluation\n${judgeText}` }],
        }),
      });
      const improveData = await improveRes.json();
      const improveText = improveData.content?.find(b => b.type === "text")?.text || "";

      const combined = parseFeedback(`${judgeText}\n---\n${improveText}`);
      setResult(combined);
      const entry = { turn, scenario, transcript, analysis, judgeText, improveText, scores: combined.scores };
      setHistory(h => [...h, entry]);
      setTurn(t => t + 1);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e) {
      setResult({ raw: `❌ Error: ${e.message}` });
    } finally {
      setLoading(false);
    }
  }

  const scores = result?.scores || {};

  return (
    <div style={{
      minHeight: "100vh", background: "#13111e",
      fontFamily: "'IBM Plex Sans', 'Helvetica Neue', sans-serif",
      color: "#e0def4",
    }}>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        textarea { resize: vertical; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        ::-webkit-scrollbar { width: 5px; } ::-webkit-scrollbar-track { background: #1e1e2e; } ::-webkit-scrollbar-thumb { background: #403d52; border-radius: 3px; }
        .fadeIn { animation: fadeIn 0.4s ease; }
        @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
        .pulse { animation: pulse 1.4s ease-in-out infinite; }
        @keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.4} }
      `}</style>

      {/* Header */}
      <header style={{
        borderBottom: "1px solid #2a2a3e", padding: "18px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "#13111e", position: "sticky", top: 0, zIndex: 10,
      }}>
        <div>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 20, fontWeight: 500, color: "#c4a7e7" }}>dialog</span>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 20, fontWeight: 500, color: "#e0def4" }}>Coach</span>
          <span style={{ marginLeft: 10, background: "#c4a7e722", color: "#c4a7e7", fontSize: 10, padding: "2px 8px", borderRadius: 999, border: "1px solid #c4a7e744", fontFamily: "'DM Mono', monospace", letterSpacing: "0.1em" }}>BETA</span>
        </div>
        <nav style={{ display: "flex", gap: 4 }}>
          {["coach", "history"].map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "6px 16px", borderRadius: 8, border: "none", cursor: "pointer",
              fontFamily: "'DM Mono', monospace", fontSize: 12, letterSpacing: "0.06em",
              background: tab === t ? "#c4a7e722" : "transparent",
              color: tab === t ? "#c4a7e7" : "#908caa",
              transition: "all 0.15s",
            }}>{t.toUpperCase()}</button>
          ))}
        </nav>
      </header>

      <main style={{ maxWidth: 780, margin: "0 auto", padding: "32px 20px 80px" }}>

        {/* ── COACH TAB ── */}
        {tab === "coach" && (
          <div className="fadeIn">
            {/* Scenario picker */}
            <div style={{ marginBottom: 28 }}>
              <label style={{ display: "block", fontSize: 11, color: "#908caa", fontFamily: "'DM Mono', monospace", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Scenario</label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {SCENARIOS.map(s => (
                  <button key={s.id} onClick={() => setScenario(s.id)} style={{
                    padding: "8px 14px", borderRadius: 10, border: `1px solid ${scenario === s.id ? "#c4a7e7" : "#2a2a3e"}`,
                    background: scenario === s.id ? "#c4a7e722" : "#1e1e2e",
                    color: scenario === s.id ? "#c4a7e7" : "#908caa",
                    cursor: "pointer", fontSize: 13, transition: "all 0.15s",
                  }}>{s.label}</button>
                ))}
              </div>
              <p style={{ marginTop: 10, fontSize: 13, color: "#6e6a86", lineHeight: 1.6, fontStyle: "italic" }}>{scenarioText}</p>
            </div>

            {/* Transcript */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: 11, color: "#908caa", fontFamily: "'DM Mono', monospace", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
                Transcript — Turn {turn}
              </label>
              <textarea
                value={transcript} onChange={e => setTranscript(e.target.value)}
                placeholder="Paste or type your spoken dialogue here..."
                rows={6}
                style={{
                  width: "100%", background: "#1e1e2e", border: "1px solid #2a2a3e",
                  borderRadius: 12, padding: "14px 16px", color: "#e0def4",
                  fontSize: 14, lineHeight: 1.7, outline: "none",
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  transition: "border-color 0.15s",
                }}
                onFocus={e => e.target.style.borderColor = "#c4a7e755"}
                onBlur={e => e.target.style.borderColor = "#2a2a3e"}
              />
            </div>

            {/* Delivery metrics */}
            <div style={{ marginBottom: 28 }}>
              <label style={{ display: "block", fontSize: 11, color: "#908caa", fontFamily: "'DM Mono', monospace", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
                Delivery Metrics <span style={{ color: "#504d67" }}>(optional – from transcribe.py)</span>
              </label>
              <div style={{ display: "flex", gap: 10 }}>
                {[
                  { label: "WPM", val: wpm, set: setWpm, ph: "e.g. 145" },
                  { label: "Fillers", val: fillers, set: setFillers, ph: "e.g. 7" },
                  { label: "Pauses", val: pauses, set: setPauses, ph: "e.g. 3" },
                ].map(({ label, val, set, ph }) => (
                  <div key={label} style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: "#6e6a86", fontFamily: "'DM Mono', monospace", marginBottom: 4 }}>{label}</div>
                    <input value={val} onChange={e => set(e.target.value)} placeholder={ph}
                      style={{
                        width: "100%", background: "#1e1e2e", border: "1px solid #2a2a3e",
                        borderRadius: 8, padding: "8px 12px", color: "#e0def4", fontSize: 13,
                        outline: "none", fontFamily: "'DM Mono', monospace",
                      }} />
                  </div>
                ))}
              </div>
            </div>

            {/* Run button */}
            <button onClick={runCoach} disabled={loading || !transcript.trim()} style={{
              width: "100%", padding: "14px", borderRadius: 12,
              background: loading ? "#2a2a3e" : "linear-gradient(135deg,#c4a7e7,#9ccfd8)",
              border: "none", color: loading ? "#908caa" : "#13111e",
              fontSize: 14, fontWeight: 600, cursor: "pointer",
              fontFamily: "'DM Mono', monospace", letterSpacing: "0.08em",
              transition: "all 0.2s",
            }}>
              {loading ? <span className="pulse">⚙ Analyzing…</span> : `▶  GET FEEDBACK  (TURN ${turn})`}
            </button>

            {/* Results */}
            {result && (
              <div ref={resultRef} className="fadeIn" style={{ marginTop: 32 }}>
                {/* Score rings */}
                {Object.keys(scores).length > 0 && (
                  <div style={{ display: "flex", justifyContent: "center", gap: 32, marginBottom: 28, padding: 24, background: "#1e1e2e", borderRadius: 16, border: "1px solid #2a2a3e" }}>
                    <ScoreRing score={scores.delivery || "–"} label="Delivery" color="#9ccfd8" />
                    <ScoreRing score={scores.linguistic_quality || "–"} label="Linguistic" color="#c4a7e7" />
                    <ScoreRing score={scores.communication_effectiveness || "–"} label="Effectiveness" color="#f6c177" />
                  </div>
                )}

                {/* Judge evaluation */}
                {result.judge && (
                  <Section title="JUDGE EVALUATION" icon="⚖️" color="#9ccfd8" defaultOpen>
                    <pre style={{ whiteSpace: "pre-wrap", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 13.5, lineHeight: 1.8, color: "#c4c2d4" }}>
                      {result.judge}
                    </pre>
                  </Section>
                )}

                <div style={{ height: 12 }} />

                {/* Improvement coaching */}
                {result.improvement && (
                  <Section title="COACHING PLAN" icon="🚀" color="#c4a7e7" defaultOpen>
                    <pre style={{ whiteSpace: "pre-wrap", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 13.5, lineHeight: 1.8, color: "#c4c2d4" }}>
                      {result.improvement}
                    </pre>
                  </Section>
                )}

                {/* Raw JSON toggle */}
                <div style={{ marginTop: 12, textAlign: "right" }}>
                  <button onClick={() => setJsonMode(j => !j)} style={{ background: "none", border: "1px solid #2a2a3e", color: "#6e6a86", padding: "4px 12px", borderRadius: 6, cursor: "pointer", fontSize: 11, fontFamily: "'DM Mono', monospace" }}>
                    {jsonMode ? "Hide" : "Show"} raw
                  </button>
                </div>
                {jsonMode && (
                  <pre style={{ marginTop: 8, background: "#1e1e2e", padding: 16, borderRadius: 10, fontSize: 11, color: "#6e6a86", overflowX: "auto", border: "1px solid #2a2a3e" }}>
                    {result.raw}
                  </pre>
                )}

                {/* Next turn nudge */}
                <div style={{ marginTop: 20, padding: 16, background: "#1e1e2e", borderRadius: 12, border: "1px solid #2a2a3e", textAlign: "center" }}>
                  <p style={{ color: "#908caa", fontSize: 13 }}>Ready to try again? Update your transcript above and hit <strong style={{ color: "#c4a7e7" }}>Get Feedback</strong> for Turn {turn}.</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── HISTORY TAB ── */}
        {tab === "history" && (
          <div className="fadeIn">
            <h2 style={{ fontFamily: "'DM Mono', monospace", fontSize: 14, color: "#908caa", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 20 }}>
              Session History — {history.length} turn{history.length !== 1 ? "s" : ""}
            </h2>
            {history.length === 0 && (
              <p style={{ color: "#6e6a86", textAlign: "center", marginTop: 60 }}>No turns completed yet. Head to the Coach tab to get started.</p>
            )}
            {history.map((h, i) => (
              <div key={i} style={{ marginBottom: 16, background: "#1e1e2e", borderRadius: 14, border: "1px solid #2a2a3e", padding: "18px 22px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                  <div>
                    <span style={{ fontFamily: "'DM Mono', monospace", color: "#c4a7e7", fontSize: 13 }}>TURN {h.turn}</span>
                    <span style={{ marginLeft: 10 }}><Chip text={h.scenario.replace("_", " ")} color="#9ccfd8" /></span>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {h.scores?.delivery && <Chip text={`D:${h.scores.delivery}`} color="#9ccfd8" />}
                    {h.scores?.linguistic_quality && <Chip text={`L:${h.scores.linguistic_quality}`} color="#c4a7e7" />}
                    {h.scores?.communication_effectiveness && <Chip text={`E:${h.scores.communication_effectiveness}`} color="#f6c177" />}
                  </div>
                </div>
                <p style={{ fontSize: 13, color: "#6e6a86", lineHeight: 1.6, borderTop: "1px solid #2a2a3e", paddingTop: 10, fontStyle: "italic" }}>
                  "{h.transcript.slice(0, 180)}{h.transcript.length > 180 ? "…" : ""}"
                </p>
                {h.analysis?.speech_rate?.words_per_min_speaking_only && (
                  <div style={{ marginTop: 10, display: "flex", gap: 16 }}>
                    <StatRow label="WPM" value={h.analysis.speech_rate.words_per_min_speaking_only} unit="wpm" warn={h.analysis.speech_rate.words_per_min_speaking_only > 160} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

// ─── Embedded prompts (mirror your .md files) ─────────────────────────────────
const JUDGE_SYSTEM = `You are an expert dialogue coach evaluator for DialogCoach. Judge only: give a rigorous, evidence-based assessment of the user's spoken performance using the transcript and the Delivery features JSON.

Scoring standards (1–5):
## 1. Delivery (fluency & pacing)
Ground scores in provided metadata: wpm, filler_count, long_pauses, repeated_words. Do NOT claim specific pronunciation, pitch, or volume.
5=Natural flow, 4=Generally fluent minor issues, 3=Understandable but uneven, 2=Flow often interrupted, 1=Fragmented.

## 2. Linguistic quality (structure & clarity)
Use transcript: grammar, vocabulary, precision, vague placeholders.
5=Accurate varied precise, 4=Mostly accurate, 3=Acceptable limited, 2=Frequent errors, 1=Weak control.

## 3. Communication effectiveness (scenario fit)
Use the Scenario and stated goals.
5=Persuasive well tailored, 4=Main ideas land, 3=Message thin or generic, 2=Only partly meets scenario, 1=Off-topic or fails.

Output structure (follow exactly):
## Rubric scores
- Delivery: <1-5> — <one line; cite metadata and/or transcript>
- Linguistic quality: <1-5> — <one line; cite transcript phrases>
- Communication effectiveness: <1-5> — <one line; tie to scenario goals>
## Top strengths
- <Specific; include evidence>
- <Specific; include evidence>
## Top gaps
- <Specific weakness; actionable>
- <Specific weakness; actionable>`;

const IMPROVE_SYSTEM = `You are "DialogCoach," a supportive and expert communication mentor. Transform the judge evaluation into a personalized, actionable coaching plan.

Coaching Principles:
1. Supportive yet Rigorous — acknowledge effort but be specific about what to change.
2. Action-Oriented — explain HOW to fix issues, not just what is wrong.
3. Evidence-Based — link coaching to rubric scores and specific transcript snippets.

Feedback Structure (4 Levels):
### Level 1 – Delivery (Fluency Coaching)
- Give a specific pacing goal tied to the wpm / filler data.
- Suggest a breathing or pausing strategy for specific problem spots.

### Level 2 – Linguistic Quality (Vocabulary & Structure)
- Identify 1–2 vague phrases or repetitive words and explain why they weaken the message.
- Provide 2–3 higher-impact alternatives.

### Level 3 – Communication Effectiveness (Strategy & Intent)
- Explain how to better align the response with the Scenario goals.
- Suggest a structural change (STAR, hook, etc.) if applicable.

### Level 4 – Improvement Suggestions (The Rewritten Script)
- Provide a realistic "Model Answer" that sounds like the user but upgraded.
- Concrete Practice Steps: one Drill + one Context Challenge.

Tone: use encouraging language like "Next time, try…" Keep it concise and immediately actionable.`;
