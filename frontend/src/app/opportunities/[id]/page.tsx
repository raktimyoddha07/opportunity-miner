import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  ExternalLink,
  Layers,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { PageHeader } from "@/components/page-header";
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
import { Separator } from "@/components/ui/separator";
import { CATEGORY_LABELS, EMOTION_LABELS, IDEA_TYPE_LABELS } from "@/lib/constants";
import { getOpportunity, getIdeas } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default async function OpportunityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const opportunity = await getOpportunity(id);
  if (!opportunity) notFound();

  // Fetch ideas linked to this opportunity (and any globally).
  const allIdeas = await getIdeas();
  const ideas = allIdeas.filter((i) => i.opportunity_id === opportunity.id);
  const cluster = opportunity.cluster;
  const painPoints = cluster?.pain_points ?? [];

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2 w-fit">
        <Link href="/opportunities">
          <ArrowLeft className="h-4 w-4" />
          Back to opportunities
        </Link>
      </Button>

      <PageHeader
        title={opportunity.title}
        description={opportunity.summary}
        actions={
          <div className="flex items-center gap-3">
            <ScoreBadge score={opportunity.score} />
            {opportunity.is_valid ? (
              <Badge variant="success">
                <ShieldCheck className="mr-1 h-3 w-3" />
                Validated
              </Badge>
            ) : (
              <Badge variant="outline">Pending review</Badge>
            )}
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="secondary">{CATEGORY_LABELS[opportunity.category]}</Badge>
        {(() => {
          const mainEmotion = painPoints.find((p) => p.emotion)?.emotion;
          return mainEmotion && EMOTION_LABELS[mainEmotion] ? (
            <Badge variant="outline" className="bg-muted/50">
              {EMOTION_LABELS[mainEmotion]}
            </Badge>
          ) : null;
        })()}
        <span>Confidence {opportunity.confidence}/100</span>
        <span>·</span>
        <span>Identified {formatDateTime(opportunity.created_at)}</span>
      </div>

      {/* Validation reasoning */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4" />
            Validation reasoning
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">{opportunity.reasoning}</p>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Cluster context */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Layers className="h-4 w-4" />
              Cluster
            </CardTitle>
            <CardDescription>The validated complaint group behind this opportunity.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {cluster ? (
              <>
                <div>
                  <p className="font-medium">{cluster.name}</p>
                  <p className="mt-1 text-muted-foreground">{cluster.summary}</p>
                </div>
                <Separator />
                <dl className="grid grid-cols-2 gap-y-2">
                  <dt className="text-muted-foreground">Frequency</dt>
                  <dd className="text-right font-mono">{Math.round(cluster.frequency * 100)}%</dd>
                  <dt className="text-muted-foreground">Avg intensity</dt>
                  <dd className="text-right font-mono">{cluster.intensity.toFixed(1)}/5</dd>
                  <dt className="text-muted-foreground">Diversity</dt>
                  <dd className="text-right font-mono">{cluster.diversity} subs</dd>
                  <dt className="text-muted-foreground">Persistence</dt>
                  <dd className="text-right font-mono">{Math.round(cluster.persistence * 100)}%</dd>
                  <dt className="text-muted-foreground">Duplicates</dt>
                  <dd className="text-right font-mono">{cluster.duplicate_count}</dd>
                </dl>
              </>
            ) : (
              <p className="text-muted-foreground">Cluster data unavailable.</p>
            )}
          </CardContent>
        </Card>

        {/* Evidence — the trust layer */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquareQuote className="h-4 w-4" />
              Evidence
            </CardTitle>
            <CardDescription>
              Each quote traces back to its original Reddit post and URL. (Opportunity → Cluster →
              Pain point → Source)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {painPoints.length === 0 ? (
              <p className="text-sm text-muted-foreground">No evidence linked yet.</p>
            ) : (
              painPoints.map((pp) => {
                const src = pp.source_document;
                return (
                  <div key={pp.id} className="rounded-md border p-3">
                    <blockquote className="border-l-2 border-primary/40 pl-3 text-sm italic">
                      “{pp.quoted_evidence}”
                    </blockquote>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">{src?.author}</span>
                      {src?.metadata.subreddit ? (
                        <span>r/{src.metadata.subreddit}</span>
                      ) : null}
                      {pp.intensity ? <span>Intensity {pp.intensity}/5</span> : null}
                      {pp.confidence ? <span>Confidence {pp.confidence}/100</span> : null}
                      {src?.url ? (
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-auto inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          View source <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : null}
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Ideas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4" />
            Generated ideas
          </CardTitle>
          <CardDescription>
            Business concepts derived only from this validated opportunity (never from raw posts).
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {ideas.length === 0 ? (
            <p className="text-sm text-muted-foreground">No ideas generated yet.</p>
          ) : (
            ideas.map((idea) => (
              <div key={idea.id} className="rounded-md border p-4">
                <Badge variant="secondary" className="mb-2">
                  {IDEA_TYPE_LABELS[idea.type]}
                </Badge>
                <p className="font-medium">{idea.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{idea.description}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
