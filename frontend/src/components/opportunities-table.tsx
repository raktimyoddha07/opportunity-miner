"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpDown, ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScoreBadge } from "@/components/score-badge";
import { CATEGORY_LABELS, CATEGORY_OPTIONS, EMOTION_LABELS, EMOTION_OPTIONS } from "@/lib/constants";
import { cn, truncate } from "@/lib/utils";
import type { Opportunity } from "@/lib/types";

type SortKey = "score" | "confidence" | "title";

interface OpportunitiesTableProps {
  opportunities: Opportunity[];
}

/** Client-side sortable + filterable opportunities table. */
export function OpportunitiesTable({ opportunities }: OpportunitiesTableProps) {
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState<string>("all");
  const [emotion, setEmotion] = React.useState<string>("all");
  const [validity, setValidity] = React.useState<string>("all");
  const [sortKey, setSortKey] = React.useState<SortKey>("score");
  const [asc, setAsc] = React.useState(false);

  const filtered = React.useMemo(() => {
    let rows = opportunities;
    if (category !== "all") rows = rows.filter((o) => o.category === category);
    if (emotion !== "all") {
      rows = rows.filter((o) => {
        const pps = o.cluster?.pain_points || [];
        return pps.some((p) => p.emotion === emotion);
      });
    }
    if (validity === "valid") rows = rows.filter((o) => o.is_valid);
    if (validity === "pending") rows = rows.filter((o) => !o.is_valid);
    if (query.trim()) {
      const q = query.toLowerCase();
      rows = rows.filter(
        (o) => o.title.toLowerCase().includes(q) || o.summary.toLowerCase().includes(q),
      );
    }
    rows = [...rows].sort((a, b) => {
      let cmp: number;
      if (sortKey === "title") cmp = a.title.localeCompare(b.title);
      else cmp = a[sortKey] - b[sortKey];
      return asc ? cmp : -cmp;
    });
    return rows;
  }, [opportunities, query, category, emotion, validity, sortKey, asc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(false);
    }
  }

  const sortBtn = (key: SortKey, label: string) => (
    <button
      onClick={() => toggleSort(key)}
      className={cn(
        "inline-flex items-center gap-1",
        sortKey === key ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {label}
      <ArrowUpDown className="h-3 w-3" />
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Input
          placeholder="Search opportunities…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="sm:w-[180px]">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORY_OPTIONS.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={emotion} onValueChange={setEmotion}>
          <SelectTrigger className="sm:w-[180px]">
            <SelectValue placeholder="Emotion Signal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All signals</SelectItem>
            {EMOTION_OPTIONS.map((e) => (
              <SelectItem key={e.value} value={e.value}>
                {e.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={validity} onValueChange={setValidity}>
          <SelectTrigger className="sm:w-[140px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All status</SelectItem>
            <SelectItem value="valid">Validated</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">{filtered.length} result(s)</span>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{sortBtn("title", "Opportunity")}</TableHead>
              <TableHead>Category & Signals</TableHead>
              <TableHead className="text-right">{sortBtn("score", "Score")}</TableHead>
              <TableHead className="text-right">{sortBtn("confidence", "Confidence")}</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((o) => {
              const mainEmotion = o.cluster?.pain_points?.find((p) => p.emotion)?.emotion;
              return (
                <TableRow key={o.id}>
                  <TableCell className="max-w-md">
                    <Link href={`/opportunities/${o.id}`} className="block">
                      <p className="font-medium hover:underline">{o.title}</p>
                      <p className="text-xs text-muted-foreground line-clamp-1">
                        {truncate(o.summary, 90)}
                      </p>
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant="secondary">{CATEGORY_LABELS[o.category]}</Badge>
                      {mainEmotion && EMOTION_LABELS[mainEmotion] && (
                        <Badge variant="outline" className="text-[10px] bg-muted/50">
                          {EMOTION_LABELS[mainEmotion]}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <ScoreBadge score={o.score} />
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">{o.confidence}</TableCell>
                  <TableCell>
                    {o.is_valid ? (
                      <Badge variant="success">Validated</Badge>
                    ) : (
                      <Badge variant="outline">Pending</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button asChild variant="ghost" size="icon">
                      <Link href={`/opportunities/${o.id}`}>
                        <ExternalLink className="h-4 w-4" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-sm text-muted-foreground">
                  No opportunities match the current filters.
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
