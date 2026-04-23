import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Mic, Send, Briefcase, Presentation, MessageSquareQuote, CheckCircle2, Circle, Sparkles, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

const scenarioOptions = [
  {
    id: "job_interview",
    label: "Job Interview",
    subtitle: "Behavioral and technical prep",
    icon: Briefcase,
  },
  {
    id: "presentation",
    label: "Presentation Preparation",
    subtitle: "Practice structure and delivery",
    icon: Presentation,
  },
  {
    id: "elevator_pitch",
    label: "Elevator Pitch",
    subtitle: "Short, confident self-introduction",
    icon: MessageSquareQuote,
  },
];

const starterPrompts = {
  job_interview: {
    title: "Interview Coach",
    helper: "Paste the question, your goal, or any context before you record.",
    placeholder:
      "Example: I am a CS junior preparing for a software engineering internship interview. Question: Tell me about yourself.",
  },
  presentation: {
    title: "Presentation Coach",
    helper: "Describe the audience, topic, and what kind of feedback you want.",
    placeholder:
      "Example: I am giving a 5-minute class presentation on my RAG project. I want feedback on clarity and confidence.",
  },
  elevator_pitch: {
    title: "Elevator Pitch Coach",
    helper: "Tell the system who you are speaking to and what you want to achieve.",
    placeholder:
      "Example: I am talking to a recruiter at a career fair. I want my pitch to sound more specific and professional.",
  },
};

const mockFeedback = {
  summary:
    "Your pace sounds natural overall. The biggest opportunity is making your message more specific and giving one concrete example.",
  strengths: [
    "You sound friendly and approachable.",
    "Your response is concise enough for a first attempt.",
  ],
  issues: [
    "Your goal is slightly vague.",
    "You do not include one memorable example or project.",
    "A short pause between ideas would improve clarity.",
  ],
  nextGoal: "Try again and add one concrete example from a project or experience.",
};

export default function DialogueCoachUI() {
  const [selectedScenario, setSelectedScenario] = useState("job_interview");
  const [userContext, setUserContext] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recorded, setRecorded] = useState(false);
  const [transcript, setTranscript] = useState(
    "Hi, I am Supia, a computer science student interested in machine learning and human-centered AI. I am looking for opportunities where I can apply both research and development skills."
  );
  const [showFeedback, setShowFeedback] = useState(false);

  const scenarioMeta = useMemo(() => starterPrompts[selectedScenario], [selectedScenario]);

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      setRecorded(true);
    } else {
      setIsRecording(true);
      setRecorded(false);
      setShowFeedback(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[radial-gradient(circle_at_top_left,#eef2ff,transparent_25%),radial-gradient(circle_at_top_right,#f8fafc,transparent_30%),linear-gradient(135deg,#eef2ff_0%,#ffffff_40%,#f5f3ff_100%)] p-6 text-slate-900">
      <div className="mx-auto grid min-h-[92vh] max-w-7xl grid-cols-1 gap-6 rounded-[2rem] border border-white/70 bg-white/70 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur xl:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="rounded-[1.75rem] border border-slate-200/70 bg-white/80 p-4 shadow-sm">
          <div className="mb-6 flex items-center gap-3 px-2 pt-1">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-slate-500">AI Dialogue Coach</p>
              <h1 className="text-lg font-semibold">Practice Studio</h1>
            </div>
          </div>

          <div className="space-y-3">
            <p className="px-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
              Choose a setting
            </p>
            {scenarioOptions.map((option) => {
              const Icon = option.icon;
              const active = selectedScenario === option.id;
              return (
                <button
                  key={option.id}
                  onClick={() => {
                    setSelectedScenario(option.id);
                    setShowFeedback(false);
                  }}
                  className={`w-full rounded-2xl border p-4 text-left transition-all ${
                    active
                      ? "border-slate-900 bg-slate-900 text-white shadow-lg"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
                  }`}
                >
                  <div className="mb-2 flex items-center gap-3">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                        active ? "bg-white/15" : "bg-slate-100"
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="font-semibold">{option.label}</span>
                  </div>
                  <p className={`text-sm ${active ? "text-slate-200" : "text-slate-500"}`}>
                    {option.subtitle}
                  </p>
                </button>
              );
            })}
          </div>

          <Card className="mt-6 rounded-2xl border-slate-200/80 bg-slate-50/90 shadow-none">
            <CardContent className="p-4">
              <p className="mb-2 text-sm font-semibold">Session flow</p>
              <div className="space-y-3 text-sm text-slate-600">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-slate-900" /> Add context
                </div>
                <div className="flex items-center gap-2">
                  <Circle className="h-4 w-4" /> Record speech
                </div>
                <div className="flex items-center gap-2">
                  <Circle className="h-4 w-4" /> Review transcript
                </div>
                <div className="flex items-center gap-2">
                  <Circle className="h-4 w-4" /> Get coaching feedback
                </div>
              </div>
            </CardContent>
          </Card>
        </aside>

        <main className="grid min-h-0 grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.2fr)_420px]">
          <section className="flex min-h-0 flex-col gap-6">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-[2rem] border border-slate-200/70 bg-[linear-gradient(180deg,rgba(248,250,252,0.9),rgba(255,255,255,0.95))] p-8 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <Badge className="rounded-full bg-slate-900 px-3 py-1 text-white hover:bg-slate-900">
                    {scenarioMeta.title}
                  </Badge>
                  <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight tracking-tight">
                    Practice your dialogue with step-by-step AI feedback.
                  </h2>
                  <p className="mt-3 max-w-2xl text-base text-slate-600">
                    Start by choosing a scenario, add your context, then record your response.
                    The coach will analyze both your delivery and your content.
                  </p>
                </div>
                <div className="rounded-3xl border border-white/80 bg-white/70 px-4 py-3 shadow-sm">
                  <p className="text-sm font-medium text-slate-500">Current mode</p>
                  <p className="text-lg font-semibold">{scenarioOptions.find(s => s.id === selectedScenario)?.label}</p>
                </div>
              </div>
            </motion.div>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_220px]">
              <Card className="rounded-[2rem] border-slate-200/70 bg-white/85 shadow-sm">
                <CardContent className="p-6">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold">Context chat box</p>
                      <p className="text-sm text-slate-500">{scenarioMeta.helper}</p>
                    </div>
                    <Button
                      variant="outline"
                      className="rounded-full border-slate-200 bg-white text-slate-700"
                      onClick={() => {
                        setUserContext("");
                        setTranscript("");
                        setRecorded(false);
                        setShowFeedback(false);
                      }}
                    >
                      <RotateCcw className="mr-2 h-4 w-4" /> Reset
                    </Button>
                  </div>

                  <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-3">
                    <Textarea
                      value={userContext}
                      onChange={(e) => setUserContext(e.target.value)}
                      placeholder={scenarioMeta.placeholder}
                      className="min-h-[140px] resize-none border-0 bg-transparent p-3 text-base shadow-none focus-visible:ring-0"
                    />

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-3 pt-3">
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="rounded-full bg-white px-3 py-1 shadow-sm">Type your background, goal, and audience</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          className={`h-11 w-11 rounded-full border ${isRecording ? "border-red-300 bg-red-50 text-red-600" : "border-slate-200 bg-white"}`}
                          onClick={toggleRecording}
                        >
                          <Mic className={`h-5 w-5 ${isRecording ? "animate-pulse" : ""}`} />
                        </Button>
                        <Button
                          className="rounded-full bg-slate-900 px-5 text-white hover:bg-slate-800"
                          onClick={() => setShowFeedback(true)}
                        >
                          Analyze <Send className="ml-2 h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-[2rem] border-slate-200/70 bg-white/85 shadow-sm">
                <CardContent className="p-6">
                  <p className="text-lg font-semibold">Recording status</p>
                  <div className="mt-6 flex flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <motion.div
                      animate={isRecording ? { scale: [1, 1.08, 1] } : { scale: 1 }}
                      transition={{ duration: 1.4, repeat: isRecording ? Infinity : 0 }}
                      className={`flex h-20 w-20 items-center justify-center rounded-full ${isRecording ? "bg-red-100 text-red-600" : "bg-slate-900 text-white"}`}
                    >
                      <Mic className="h-8 w-8" />
                    </motion.div>
                    <p className="mt-4 text-lg font-semibold">
                      {isRecording ? "Recording..." : recorded ? "Recording saved" : "Ready to record"}
                    </p>
                    <p className="mt-2 text-sm text-slate-500">
                      {isRecording
                        ? "Speak naturally. Your transcript and delivery features will appear after analysis."
                        : "Press the mic button to record your response."}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="min-h-[260px] rounded-[2rem] border-slate-200/70 bg-white/85 shadow-sm">
              <CardContent className="p-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold">Transcript preview</p>
                    <p className="text-sm text-slate-500">You can show low-confidence words with highlighted tags later.</p>
                  </div>
                  <Badge variant="secondary" className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                    Editable transcript area
                  </Badge>
                </div>
                <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-5 text-[15px] leading-7 text-slate-700">
                  {transcript || "Your transcript will appear here after recording and transcription."}
                </div>
              </CardContent>
            </Card>
          </section>

          <section className="flex min-h-0 flex-col gap-6">
            <Card className="rounded-[2rem] border-slate-200/70 bg-white/85 shadow-sm">
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold">AI coaching panel</p>
                    <p className="text-sm text-slate-500">Delivery and content feedback in one place</p>
                  </div>
                  <Badge className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700 hover:bg-emerald-50">
                    {showFeedback ? "Ready" : "Waiting"}
                  </Badge>
                </div>

                {!showFeedback ? (
                  <div className="mt-6 rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-sm leading-6 text-slate-500">
                    Add your context and record a response, then click Analyze to generate coaching feedback.
                  </div>
                ) : (
                  <div className="mt-6 space-y-4">
                    <div className="rounded-[1.5rem] bg-slate-900 p-5 text-white">
                      <p className="text-sm text-slate-300">Overall summary</p>
                      <p className="mt-2 text-sm leading-6">{mockFeedback.summary}</p>
                    </div>

                    <div className="rounded-[1.5rem] border border-slate-200 p-5">
                      <p className="font-semibold">What you did well</p>
                      <ul className="mt-3 space-y-2 text-sm text-slate-600">
                        {mockFeedback.strengths.map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-[1.5rem] border border-slate-200 p-5">
                      <p className="font-semibold">Main issues</p>
                      <ol className="mt-3 space-y-2 text-sm text-slate-600">
                        {mockFeedback.issues.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ol>
                    </div>

                    <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5">
                      <p className="font-semibold">Next practice goal</p>
                      <p className="mt-2 text-sm text-slate-600">{mockFeedback.nextGoal}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="grid gap-6 md:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
              <Card className="rounded-[1.75rem] border-slate-200/70 bg-white/85 shadow-sm">
                <CardContent className="p-5">
                  <p className="text-sm text-slate-500">Speech rate</p>
                  <p className="mt-2 text-3xl font-semibold">129</p>
                  <p className="mt-1 text-sm text-slate-500">WPM · natural pace</p>
                </CardContent>
              </Card>

              <Card className="rounded-[1.75rem] border-slate-200/70 bg-white/85 shadow-sm">
                <CardContent className="p-5">
                  <p className="text-sm text-slate-500">Pause count</p>
                  <p className="mt-2 text-3xl font-semibold">0</p>
                  <p className="mt-1 text-sm text-slate-500">Continuous speech</p>
                </CardContent>
              </Card>

              <Card className="rounded-[1.75rem] border-slate-200/70 bg-white/85 shadow-sm">
                <CardContent className="p-5">
                  <p className="text-sm text-slate-500">Clarity</p>
                  <p className="mt-2 text-3xl font-semibold">Mostly clear</p>
                  <p className="mt-1 text-sm text-slate-500">1 low-confidence word</p>
                </CardContent>
              </Card>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
