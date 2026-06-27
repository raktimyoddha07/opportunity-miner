import { PageHeader } from "@/components/page-header";
import { OpportunitiesTable } from "@/components/opportunities-table";
import { getOpportunities } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OpportunitiesPage() {
  const opportunities = await getOpportunities();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ranked Opportunities"
        description="Validated problems ranked by score. Sort, filter, and dig into the evidence behind each."
      />
      <OpportunitiesTable opportunities={opportunities} />
    </div>
  );
}
