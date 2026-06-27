import { PageHeader } from "@/components/page-header";
import { getRuns, getTrendSnapshots } from "@/lib/api";
import { RunsClientPage } from "@/components/runs-client-page";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const [runs, trends] = await Promise.all([getRuns(), getTrendSnapshots()]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Runs"
        description="Pipeline execution history and frequency comparisons across runs."
      />

      <RunsClientPage initialRuns={runs} initialTrends={trends} />
    </div>
  );
}
