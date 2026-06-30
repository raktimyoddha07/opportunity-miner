"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Loader2, XCircle, Square, Trash2, Play } from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import type { Run, RunStatus, TrendSnapshot } from "@/lib/types";
import { stopRun, deleteRun, getRuns, getSettings, startRun } from "@/lib/api";

// Shared AudioContext for overcoming browser autoplay block
let sharedCtx: AudioContext | null = null;

function getAudioContext() {
  if (typeof window === "undefined") return null;
  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
  if (!AudioContextClass) return null;
  if (!sharedCtx) {
    sharedCtx = new AudioContextClass();
  }
  if (sharedCtx.state === "suspended") {
    sharedCtx.resume().catch(() => {});
  }
  return sharedCtx;
}

function playNotificationSound(type: "success" | "error") {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    
    if (type === "success") {
      // Pleasant double-chime (ascending)
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
      
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(659.25, ctx.currentTime + 0.15); // E5
      gain2.gain.setValueAtTime(0.1, ctx.currentTime + 0.15);
      gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.45);
      osc2.start(ctx.currentTime + 0.15);
      osc2.stop(ctx.currentTime + 0.45);
    } else {
      // Alert chime (descending/flat warning)
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.type = "triangle";
      osc.frequency.setValueAtTime(329.63, ctx.currentTime); // E4
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
      
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.type = "triangle";
      osc2.frequency.setValueAtTime(261.63, ctx.currentTime + 0.15); // C4
      gain2.gain.setValueAtTime(0.15, ctx.currentTime + 0.15);
      gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.65);
      osc2.start(ctx.currentTime + 0.15);
      osc2.stop(ctx.currentTime + 0.65);
    }
  } catch (err) {
    console.warn("Failed to play notification sound:", err);
  }
}

const statusMeta: Record<
  RunStatus,
  { label: string; icon: React.ComponentType<{ className?: string }>; className: string; badge: "success" | "warning" | "destructive" }
> = {
  completed: { label: "Completed", icon: CheckCircle2, className: "text-emerald-600", badge: "success" },
  running: { label: "Running", icon: Loader2, className: "text-amber-600", badge: "warning" },
  failed: { label: "Failed", icon: XCircle, className: "text-rose-600", badge: "destructive" },
};

interface RunsClientPageProps {
  initialRuns: Run[];
  initialTrends: TrendSnapshot[];
}

export function RunsClientPage({ initialRuns, initialTrends }: RunsClientPageProps) {
  const router = useRouter();
  const [runs, setRuns] = React.useState<Run[]>(initialRuns);
  const [trends, setTrends] = React.useState<TrendSnapshot[]>(initialTrends);
  const [stoppingId, setStoppingId] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [starting, setStarting] = React.useState(false);
  const [message, setMessage] = React.useState<{ kind: "ok" | "err"; text: string } | null>(null);

  // Sync state with server component props when they re-fetch (router.refresh())
  React.useEffect(() => {
    setRuns(initialRuns);
  }, [initialRuns]);

  React.useEffect(() => {
    setTrends(initialTrends);
  }, [initialTrends]);

  // Unlock AudioContext on first user interaction
  React.useEffect(() => {
    function unlock() {
      const ctx = getAudioContext();
      if (ctx && ctx.state === "suspended") {
        ctx.resume().catch(() => {});
      }
      window.removeEventListener("click", unlock);
      window.removeEventListener("keydown", unlock);
    }
    window.addEventListener("click", unlock);
    window.addEventListener("keydown", unlock);
    return () => {
      window.removeEventListener("click", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  // Compare cluster frequency across the two most recent runs.
  const dates = [...new Set(trends.map((t) => formatDate(t.snapshot_date)))].sort();
  const lastTwo = dates.slice(-2);
  const comparison = [...new Set(trends.map((t) => t.cluster_name))]
    .map((name) => {
      const earlier =
        trends.find((t) => t.cluster_name === name && formatDate(t.snapshot_date) === lastTwo[0])
          ?.frequency ?? 0;
      const later =
        trends.find((t) => t.cluster_name === name && formatDate(t.snapshot_date) === lastTwo[1])
          ?.frequency ?? 0;
      return { name, [lastTwo[0] ?? "prev"]: earlier, [lastTwo[1] ?? "curr"]: later };
    })
    .sort(
      (a, b) =>
        (b[lastTwo[1] ?? "curr"] as number) - (a[lastTwo[1] ?? "curr"] as number),
    );

  const chartConfig: ChartConfig = {
    [lastTwo[0] ?? "prev"]: { label: lastTwo[0] ?? "Previous", color: "hsl(var(--chart-4))" },
    [lastTwo[1] ?? "curr"]: { label: lastTwo[1] ?? "Latest", color: "hsl(var(--chart-1))" },
  };

  // Poll for run status every 10 s while a run is active.
  // Backs off to 30 s after 3 consecutive failures so a busy Ollama backend
  // doesn't get hammered with rapid retries.
  React.useEffect(() => {
    const hasRunning = runs.some((r) => r.status === "running");
    if (!hasRunning) return;

    let consecutiveFails = 0;

    const poll = async () => {
      try {
        const latestRuns = await getRuns();
        consecutiveFails = 0; // reset on success
        let changed = false;

        latestRuns.forEach((r) => {
          const prevRun = runs.find((p) => p.id === r.id);
          if (prevRun && prevRun.status === "running" && r.status !== "running") {
            changed = true;
            if (r.status === "completed") {
              playNotificationSound("success");
            } else if (r.status === "failed") {
              playNotificationSound("error");
            }
          }
        });

        if (changed) {
          // Trigger server refresh to load updated trends and data
          router.refresh();
        } else {
          setRuns(latestRuns);
        }
      } catch (err) {
        consecutiveFails++;
        if (consecutiveFails <= 3) {
          console.error("Polling runs failed", err);
        } else if (consecutiveFails === 4) {
          console.warn("[runs] Backend appears busy — backing off poll to 30 s");
        }
      }
    };

    // Adaptive interval: 10 s normally, 30 s if the backend is failing repeatedly.
    const NORMAL_INTERVAL = 10_000;
    const BACKOFF_INTERVAL = 30_000;
    const BACKOFF_THRESHOLD = 3;

    let timeoutId: ReturnType<typeof setTimeout>;
    const schedule = () => {
      const delay = consecutiveFails > BACKOFF_THRESHOLD ? BACKOFF_INTERVAL : NORMAL_INTERVAL;
      timeoutId = setTimeout(async () => {
        await poll();
        schedule(); // re-schedule after each poll completes
      }, delay);
    };
    schedule();

    return () => clearTimeout(timeoutId);
  }, [runs, router]);

  async function handleStartRun() {
    setStarting(true);
    setMessage(null);
    try {
      // Direct call warms up/resumes AudioContext inside click interaction
      getAudioContext();

      const currentSettings = await getSettings();
      if (!currentSettings.subreddits || currentSettings.subreddits.length === 0) {
        throw new Error("No subreddits configured. Go to Settings to add subreddits.");
      }
      const newRun = await startRun({
        subreddits: currentSettings.subreddits,
        llm_config: currentSettings.llm_config as unknown as Record<string, unknown>,
      });
      if (newRun) {
        setRuns((prev) => [newRun, ...prev]);
        setMessage({ kind: "ok", text: "Run started successfully!" });
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start run.");
      playNotificationSound("error");
    } finally {
      setStarting(false);
    }
  }

  // Fallback setter just in case
  function setErrorMsg(text: string) {
    setMessage({ kind: "err", text });
  }

  async function handleStop(runId: string) {
    setStoppingId(runId);
    try {
      const updated = await stopRun(runId);
      if (updated) {
        setRuns((prev) => prev.map((r) => (r.id === runId ? updated : r)));
      }
    } catch (err) {
      console.error("Failed to stop run", err);
    } finally {
      setStoppingId(null);
    }
  }

  async function handleDelete(runId: string) {
    if (!confirm("Are you sure you want to delete this run and all associated data?")) return;
    setDeletingId(runId);
    try {
      await deleteRun(runId);
      setRuns((prev) => prev.filter((r) => r.id !== runId));
      setTrends((prev) => prev.filter((t) => t.run_id !== runId));
    } catch (err) {
      console.error("Failed to delete run", err);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Runs"
        description="Pipeline execution history and frequency comparisons across runs."
        actions={
          <Button onClick={handleStartRun} disabled={starting}>
            <Play className="mr-2 h-4 w-4 fill-current" />
            {starting ? "Starting..." : "Start run"}
          </Button>
        }
      />

      {message ? (
        <div
          className={
            message.kind === "ok"
              ? "rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
          }
        >
          {message.text}
        </div>
      ) : null}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Status</TableHead>
              <TableHead>Subreddits</TableHead>
              <TableHead>LLM</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => {
              const meta = statusMeta[run.status];
              const Icon = meta.icon;
              return (
                <TableRow key={run.id}>
                  <TableCell>
                    <Badge variant={meta.badge} className="gap-1">
                      <Icon className={cn("h-3 w-3", run.status === "running" && "animate-spin")} />
                      {meta.label}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {run.subreddits.map((s) => (
                        <Badge key={s} variant="outline" className="text-xs">
                          r/{s}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {String(run.llm_config.provider ?? "—")} / {String(run.llm_config.model ?? "—")}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTime(run.created_at)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTime(run.updated_at)}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    {run.status === "running" && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleStop(run.id)}
                        disabled={stoppingId === run.id}
                        className="h-7 px-2 text-xs"
                      >
                        <Square className="mr-1 h-3 w-3 fill-current" />
                        {stoppingId === run.id ? "Stopping..." : "Stop"}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(run.id)}
                      disabled={deletingId === run.id}
                      className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
            {runs.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                  No runs found. Start one in Settings.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {runs.some((r) => r.status === "failed" && r.error) ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-rose-600">
              <AlertTriangle className="h-4 w-4" />
              Failed run errors
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {runs
              .filter((r) => r.status === "failed" && r.error)
              .map((r) => (
                <div key={r.id} className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm dark:border-rose-900 dark:bg-rose-950/40">
                  <p className="font-mono text-xs text-rose-700 dark:text-rose-300">{r.id}</p>
                  <p className="mt-1 text-muted-foreground">{r.error}</p>
                </div>
              ))}
          </CardContent>
        </Card>
      ) : null}

      {lastTwo.length === 2 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Frequency comparison</CardTitle>
            <CardDescription>
              Cluster frequency in the two most recent runs ({lastTwo[0]} → {lastTwo[1]}).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={chartConfig} className="h-[280px] w-full">
              <BarChart data={comparison} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                <XAxis type="number" tickLine={false} axisLine={false} domain={[0, "dataMax"]} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  width={160}
                  fontSize={11}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey={lastTwo[0]} fill="var(--color-chart-4)" radius={[0, 4, 4, 0]} />
                <Bar dataKey={lastTwo[1]} fill="var(--color-chart-1)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
