import { getRuns, getTrendSnapshots } from "@/lib/api";
import { RunsClientPage } from "@/components/runs-client-page";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const [runs, trends] = await Promise.all([getRuns(), getTrendSnapshots()]);

  return (
    <div className="space-y-6">
      <RunsClientPage initialRuns={runs} initialTrends={trends} />
    </div>
  );
}
