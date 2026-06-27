import { Boxes } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { ScoreBadge } from "@/components/score-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CATEGORY_LABELS } from "@/lib/constants";
import { getClusters } from "@/lib/api";
import { truncate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function ClustersPage() {
  const clusters = (await getClusters()).sort((a, b) => b.score - a.score);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Clusters"
        description="Grouped complaints with their frequency, intensity, and diversity signals."
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {clusters.map((c) => (
          <Card key={c.id}>
            <CardContent className="space-y-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-medium leading-tight">{c.name}</p>
                  <Badge variant="secondary">{CATEGORY_LABELS[c.category]}</Badge>
                </div>
                <ScoreBadge score={c.score} />
              </div>
              <p className="text-sm text-muted-foreground">{truncate(c.summary, 140)}</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 border-t pt-3 text-xs">
                <Metric label="Frequency" value={`${Math.round(c.frequency * 100)}%`} />
                <Metric label="Intensity" value={`${c.intensity.toFixed(1)}/5`} />
                <Metric label="Diversity" value={`${c.diversity} subs`} />
                <Metric label="Duplicates" value={c.duplicate_count} />
              </div>
            </CardContent>
          </Card>
        ))}
        {clusters.length === 0 ? (
          <div className="col-span-full flex flex-col items-center justify-center gap-2 rounded-md border border-dashed py-16 text-center text-sm text-muted-foreground">
            <Boxes className="h-8 w-8 opacity-50" />
            No clusters yet.
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}
