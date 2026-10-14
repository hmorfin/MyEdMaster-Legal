import { useState, useEffect } from "react";
import {
  ArrowLeft,
  BookOpen,
  Brain,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getStoredUserId } from "@/lib/auth";

type MasterySource = "chat" | "course";

type MasteryScore = {
  title: string;
  score: number;
  source: MasterySource;
  detail: string;
  trend: string;
};

const tabConfig = [
  { value: "all", label: "All" },
  { value: "chat", label: "Chat Scores" },
  { value: "course", label: "Course Scores" },
] as const;

function getVisibleScores(
  scores: MasteryScore[],
  tab: (typeof tabConfig)[number]["value"]
) {
  if (tab === "all") return scores;
  return scores.filter((item) => item.source === tab);
}

function getAverageScore(scores: MasteryScore[]) {
  if (!scores.length) return 0;
  const total = scores.reduce((sum, item) => sum + item.score, 0);
  return total / scores.length;
}

function getScoreTone(score: number) {
  if (score >= 4.2) {
    return {
      pill: "bg-emerald-500/12 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300",
      accent: "bg-emerald-500",
      label: "Excellent",
    };
  }
  if (score >= 3.2) {
    return {
      pill: "bg-amber-500/12 text-amber-700 ring-amber-500/20 dark:text-amber-300",
      accent: "bg-amber-500",
      label: "Building",
    };
  }
  return {
    pill: "bg-rose-500/12 text-rose-700 ring-rose-500/20 dark:text-rose-300",
    accent: "bg-rose-500",
    label: "Needs Focus",
  };
}

function ScoreDots({ score }: { score: number }) {
  const rounded = Math.round(score);
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex gap-1.5">
        {Array.from({ length: 5 }, (_, index) => {
          const filled = index < rounded;
          return (
            <span
              key={index}
              className={`h-2.5 w-7 rounded-full transition-colors sm:w-8 ${
                filled ? "bg-foreground" : "bg-muted"
              }`}
            />
          );
        })}
      </div>
      <span className="text-sm font-medium text-muted-foreground">
        {score.toFixed(1)} / 5
      </span>
    </div>
  );
}

function ScoreCard({ item }: { item: MasteryScore }) {
  const tone = getScoreTone(item.score);
  const sourceLabel =
    item.source === "chat"
      ? "Source: based on chat info"
      : "Source: based on course they are taking";

  return (
    <Card className="overflow-hidden border-border/70 bg-card/95 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <CardHeader className="gap-5 border-b border-border/60 px-6 py-6 sm:px-7 sm:py-7">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <CardDescription className="text-xs uppercase tracking-[0.22em] text-muted-foreground/80">
              Mastery Signal
            </CardDescription>
            <CardTitle className="text-xl leading-tight">{item.title}</CardTitle>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tone.pill}`}
          >
            {tone.label}
          </span>
        </div>
        <ScoreDots score={item.score} />
      </CardHeader>
      <CardContent className="space-y-5 px-6 py-6 sm:px-7 sm:py-7">
        <div className="rounded-2xl border border-border/50 bg-muted/50 p-5">
          <p className="text-sm font-medium text-foreground">{sourceLabel}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {item.detail}
          </p>
        </div>
        <div className="flex items-start gap-4 rounded-2xl border border-border/70 bg-background/80 p-5">
          <div className={`mt-0.5 h-10 w-1 shrink-0 rounded-full ${tone.accent}`} />
          <div>
            <p className="text-sm font-semibold text-foreground">What this means</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {item.trend}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string;
  value: string;
  description: string;
  icon: typeof Sparkles;
}) {
  return (
    <Card className="border-border/70 bg-card/95 shadow-sm">
      <CardContent className="flex items-start justify-between gap-5 px-6 py-6">
        <div className="space-y-2.5">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-3xl font-semibold tracking-tight">{value}</p>
          <p className="text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-muted text-foreground">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function StatisticsPage() {
  const navigate = useNavigate();
  const [masteryScores, setMasteryScores] = useState<MasteryScore[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const userId = getStoredUserId();
    if (!userId) return;
    fetch(`/api/v1/users/${userId}/stats/`)
      .then((res) => res.json())
      .then((payload) => {
        if (payload.status === "success") {
          setMasteryScores(payload.data);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const allAverage = getAverageScore(masteryScores);
  const chatScores = masteryScores.filter((s) => s.source === "chat");
  const courseScores = masteryScores.filter((s) => s.source === "course");
  const chatAverage = getAverageScore(chatScores);
  const courseAverage = getAverageScore(courseScores);
  const topStrength = [...masteryScores].sort((a, b) => b.score - a.score)[0];
  const bestNextFocus = [...masteryScores].sort((a, b) => a.score - b.score)[0];
  const mostActiveSource =
    chatScores.length >= courseScores.length
      ? "Chat-based signals"
      : "Course-based signals";

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-muted-foreground">
        Loading stats...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background px-4 py-10 sm:px-6 sm:py-12 lg:px-8 lg:py-14">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-10">
        <section className="overflow-hidden rounded-[2rem] border border-border/70 bg-card/90 shadow-sm backdrop-blur">
          <div className="grid gap-10 px-6 py-8 sm:px-8 sm:py-10 lg:grid-cols-[1.5fr_0.9fr] lg:px-10 lg:py-12">
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-full border-border/70 bg-background/80 px-4 shadow-none backdrop-blur"
                  onClick={() => {
                    if (window.history.length > 1) {
                      navigate(-1);
                      return;
                    }
                    navigate("/chat");
                  }}
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/80 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  <Brain className="h-3.5 w-3.5" />
                  User Statistics
                </div>
              </div>
              <div className="space-y-4">
                <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
                  Mastery scores to track your progress!
                </h1>
                <p className="max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
                  Track how confident a user is across legal topics, compare
                  signals from chats and courses, and surface where more guided
                  learning is needed next.
                </p>
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-3 lg:grid-cols-1">
              <SummaryCard
                title="Overall Average"
                value={`${allAverage.toFixed(1)}/5`}
                description="Blended score across all current mastery signals."
                icon={TrendingUp}
              />
              <SummaryCard
                title="Chat-Derived"
                value={`${chatAverage.toFixed(1)}/5`}
                description="Confidence inferred from live conversations."
                icon={MessageSquareText}
              />
              <SummaryCard
                title="Course-Derived"
                value={`${courseAverage.toFixed(1)}/5`}
                description="Progress measured from structured learning paths."
                icon={BookOpen}
              />
            </div>
          </div>
        </section>

        <section className="grid gap-5 md:grid-cols-3">
          <Card className="border-border/70 bg-card/95 shadow-sm">
            <CardContent className="flex items-center gap-4 px-6 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/12 text-emerald-600 dark:text-emerald-300">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Top Strength</p>
                <p className="text-lg font-semibold">{topStrength?.title ?? "N/A"}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border/70 bg-card/95 shadow-sm">
            <CardContent className="flex items-center gap-4 px-6 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/12 text-sky-600 dark:text-sky-300">
                <MessageSquareText className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Most Active Source</p>
                <p className="text-lg font-semibold">{mostActiveSource}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border/70 bg-card/95 shadow-sm">
            <CardContent className="flex items-center gap-4 px-6 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/12 text-amber-600 dark:text-amber-300">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Best Next Focus</p>
                <p className="text-lg font-semibold">{bestNextFocus?.title ?? "N/A"}</p>
              </div>
            </CardContent>
          </Card>
        </section>

        <Card className="border-border/70 bg-card/95 py-0 shadow-sm">
          <CardHeader className="gap-4 border-b border-border/60 px-6 py-7 sm:px-8 sm:py-8">
            <div className="space-y-2">
              <CardDescription className="text-xs uppercase tracking-[0.22em] text-muted-foreground/80">
                Detailed View
              </CardDescription>
              <CardTitle className="text-2xl">Mastery Breakdown</CardTitle>
            </div>
            <CardDescription className="max-w-2xl leading-7">
              Each score combines topic understanding with recent user activity.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-4 py-6 sm:px-6 sm:py-8">
            {masteryScores.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No mastery data yet. Start chatting or take a course to see your scores here.
              </p>
            ) : (
              <Tabs defaultValue="all" className="gap-8">
                <TabsList
                  variant="line"
                  className="w-full justify-start gap-3 overflow-x-auto rounded-none border-b border-border bg-transparent px-1 pb-1"
                >
                  {tabConfig.map((tab) => (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className="rounded-t-xl rounded-b-none px-4 py-3.5 text-sm font-semibold data-[state=active]:bg-muted/60"
                    >
                      {tab.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
                {tabConfig.map((tab) => {
                  const visibleScores = getVisibleScores(masteryScores, tab.value);
                  return (
                    <TabsContent key={tab.value} value={tab.value}>
                      {visibleScores.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-8 text-center">
                          No {tab.value === "all" ? "" : tab.label.toLowerCase()} data yet.
                        </p>
                      ) : (
                        <div className="grid gap-6 pt-1 md:grid-cols-2 2xl:grid-cols-3">
                          {visibleScores.map((item) => (
                            <ScoreCard key={`${tab.value}-${item.title}`} item={item} />
                          ))}
                        </div>
                      )}
                    </TabsContent>
                  );
                })}
              </Tabs>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}