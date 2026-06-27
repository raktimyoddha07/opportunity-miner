import { ExternalLink, ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { CATEGORY_LABELS } from "@/lib/constants";
import { getSourceDocuments, getEvidence } from "@/lib/api";
import { formatDateTime, truncate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function EvidencePage() {
  const [documents, painPoints] = await Promise.all([getSourceDocuments(), getEvidence()]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence"
        description="The trust layer. Every signal is traceable to its original source, author, and URL — never discarded."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4" />
            Extracted pain points
          </CardTitle>
          <CardDescription>
            LLM-extracted complaints with their quoted evidence and original source link.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {painPoints.filter((p) => p.has_pain_point).map((pp) => {
            const src = pp.source_document;
            return (
              <div key={pp.id} className="rounded-md border p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium">{pp.summary}</p>
                  {pp.category ? (
                    <Badge variant="secondary" className="shrink-0">
                      {CATEGORY_LABELS[pp.category]}
                    </Badge>
                  ) : null}
                </div>
                <blockquote className="mt-2 border-l-2 border-primary/40 pl-3 text-sm italic text-muted-foreground">
                  “{pp.quoted_evidence}”
                </blockquote>
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
                  {pp.intensity ? <span>Intensity {pp.intensity}/5</span> : null}
                  {pp.confidence ? <span>Confidence {pp.confidence}/100</span> : null}
                  {src ? (
                    <>
                      <span className="font-medium text-foreground">{src.author}</span>
                      {src.metadata.subreddit ? <span>r/{src.metadata.subreddit}</span> : null}
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-auto inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Source <ExternalLink className="h-3 w-3" />
                      </a>
                    </>
                  ) : null}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Raw source documents</CardTitle>
          <CardDescription>
            Original posts and comments, stored before any processing — the immutable provenance chain.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-start gap-3 rounded-md border p-4">
              <Avatar>
                <AvatarFallback>{doc.author.replace(/^u\//, "").slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                  <span className="font-medium">{doc.author}</span>
                  {doc.metadata.subreddit ? (
                    <Badge variant="outline" className="text-xs">r/{doc.metadata.subreddit}</Badge>
                  ) : null}
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(doc.created_at)}
                  </span>
                </div>
                {doc.title ? <p className="text-sm font-medium">{doc.title}</p> : null}
                <p className="text-sm text-muted-foreground">{truncate(doc.content, 200)}</p>
                <div className="flex items-center gap-4 pt-1 text-xs text-muted-foreground">
                  {typeof doc.metadata.score === "number" ? <span>▲ {doc.metadata.score}</span> : null}
                  {typeof doc.metadata.comment_count === "number" ? (
                    <span>💬 {doc.metadata.comment_count}</span>
                  ) : null}
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
