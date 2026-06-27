import Link from "next/link";
import { Boxes, ListChecks, TrendingUp, Trophy } from "lucide-react";

export const dynamic = "force-dynamic";

import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { ScoreBadge } from "@/components/score-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CATEGORY_LABELS } from "@/lib/constants";
import { getOpportunities, getClusters, getRuns, getTrendSnapshots } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { DashboardCharts } from "@/components/dashboard-charts";
import { ExportDropdown } from "@/components/export-dropdown";

export default async function DashboardPage() {
  const [opportunities, clusters, runs, trends] = await Promise.all([
    getOpportunities(),
    getClusters(),
    getRuns(),
    getTrendSnapshots(),
  ]);

  const valid = opportunities.filter((o) => o.is_valid);
  const avgScore = valid.length
    ? Math.round(valid.reduce((s, o) => s + o.score, 0) / valid.length)
    : 0;

  // Category distribution across opportunities.
  const byCategory = new Map<string, number>();
  for (const o of opportunities) {
    byCategory.set(o.category, (byCategory.get(o.category) ?? 0) + 1);
  }
  const categoryData = [...byCategory.entries()]
    .map(([category, count]) => ({
      category: CATEGORY_LABELS[category as keyof typeof CATEGORY_LABELS] ?? category,
      count,
    }))
    .sort((a, b) => b.count - a.count);

  // Trend lines: frequency per cluster_name over snapshot dates.
  const dates = [...new Set(trends.map((t) => formatDate(t.snapshot_date)))].sort();
  const clusterNames = [...new Set(trends.map((t) => t.cluster_name))];
  const trendData = dates.map((date) => {
    const row: Record<string, string | number> = { date };
    for (const name of clusterNames) {
      row[name] =
          trends.find((t) => formatDate(t.snapshot_date) === date && t.cluster_name === name)
              ?.frequency ?? 0;
    }
    return row;
  });

  const top = [...valid].sort((a, b) => b.score - a.score).slice(0, 5);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Top opportunities, category distribution, and trend signals across runs."
        actions={
          <div className="flex items-center gap-2">
            <ExportDropdown />
            <Button asChild>
              <Link href="/opportunities">View all</Link>
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Validated opportunities"
          value={valid.length}
          hint={`${opportunities.length - valid.length} pending review`}
          icon={ListChecks}
        />
        <StatCard label="Avg opportunity score" value={avgScore} icon={Trophy} />
        <StatCard label="Clusters" value={clusters.length} hint={`${runs.length} runs`} icon={Boxes} />
        <StatCard
          label="Completed runs"
          value={runs.filter((r) => r.status === "completed").length}
          hint={runs[0] ? `Latest ${formatDate(runs[0].created_at)}` : undefined}
          icon={TrendingUp}
        />
      </div>

      <DashboardCharts
        categoryData={categoryData}
        trendData={trendData}
        clusterNames={clusterNames}
      />

      <Card>
        <CardHeader>
          <CardTitle>Top opportunities</CardTitle>
          <CardDescription>Highest-scoring validated problems.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {top.map((o) => (
            <Link
              key={o.id}
              href={`/opportunities/${o.id}`}
              className="flex items-center justify-between gap-4 rounded-md border p-3 transition-colors hover:bg-accent"
            >
              <div className="min-w-0 space-y-1">
                <p className="truncate text-sm font-medium">{o.title}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{CATEGORY_LABELS[o.category]}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {o.cluster?.diversity ?? 0} subreddits
                  </span>
                </div>
              </div>
              <ScoreBadge score={o.score} />
            </Link>
          ))}
          {top.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No validated opportunities yet.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
