import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { IDEA_TYPE_LABELS } from "@/lib/constants";
import { getIdeas } from "@/lib/api";
import type { IdeaType } from "@/lib/types";

export const dynamic = "force-dynamic";

const TYPE_ORDER: IdeaType[] = [
  "micro_saas",
  "ai_agent",
  "chrome_extension",
  "api_product",
  "marketplace",
  "service_business",
  "internal_tool",
  "workflow_automation",
];

export default async function IdeasPage() {
  const ideas = await getIdeas();
  const grouped = TYPE_ORDER.map((type) => ({
    type,
    items: ideas.filter((i) => i.type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ideas"
        description="Business concepts generated only from validated opportunities, across every idea format."
      />

      <div className="space-y-8">
        {grouped.map(({ type, items }) => (
          <section key={type} className="space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {IDEA_TYPE_LABELS[type]}
              </h2>
              <Badge variant="outline">{items.length}</Badge>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((idea) => (
                <Card key={idea.id}>
                  <CardContent className="space-y-3 p-5">
                    <p className="font-medium leading-tight">{idea.title}</p>
                    <p className="text-sm text-muted-foreground">{idea.description}</p>
                    {idea.opportunity ? (
                      <Link
                        href={`/opportunities/${idea.opportunity.id}`}
                        className="inline-block text-xs text-primary hover:underline"
                      >
                        ← {idea.opportunity.title}
                      </Link>
                    ) : null}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        ))}
        {grouped.length === 0 ? (
          <p className="rounded-md border border-dashed py-16 text-center text-sm text-muted-foreground">
            No ideas generated yet.
          </p>
        ) : null}
      </div>
    </div>
  );
}
