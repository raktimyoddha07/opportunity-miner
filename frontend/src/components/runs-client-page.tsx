"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Loader2, XCircle, Square, Trash2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { stopRun, deleteRun } from "@/lib/api";

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
  const [runs, setRuns] = React.useState<Run[]>(initialRuns);
  const [trends, setTrends] = React.useState<TrendSnapshot[]>(initialTrends);
  const [stoppingId, setStoppingId] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

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
                        size="xs"
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
                      size="xs"
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
