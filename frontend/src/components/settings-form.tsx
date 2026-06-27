"use client";

import * as React from "react";
import { Play, Save, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PROVIDER_OPTIONS } from "@/lib/constants";
import { saveSettings, startRun, usingMocks } from "@/lib/api";
import type { Provider, Settings } from "@/lib/types";

const FEED_OPTIONS = ["hot", "top", "rising", "new"] as const;

export function SettingsForm({ initial }: { initial: Settings }) {
  const [settings, setSettings] = React.useState<Settings>(initial);
  const [subredditInput, setSubredditInput] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [starting, setStarting] = React.useState(false);
  const [message, setMessage] = React.useState<{ kind: "ok" | "err"; text: string } | null>(null);

  function updateLLM(patch: Partial<{ provider: Provider; model: string; api_key: string; base_url: string; temperature: number }>) {
    setSettings((s) => ({
      ...s,
      llm_config: {
        ...s.llm_config,
        provider: patch.provider ?? s.llm_config.provider,
        model: patch.model ?? s.llm_config.model,
        config: {
          ...s.llm_config.config,
          ...(patch.api_key !== undefined ? { api_key: patch.api_key } : {}),
          ...(patch.base_url !== undefined ? { base_url: patch.base_url } : {}),
          ...(patch.temperature !== undefined ? { temperature: patch.temperature } : {}),
        },
      },
    }));
  }

  function addSubreddit() {
    const v = subredditInput.trim().replace(/^r\//, "").toLowerCase();
    if (!v) return;
    if (!settings.subreddits.includes(v)) {
      setSettings((s) => ({ ...s, subreddits: [...s.subreddits, v] }));
    }
    setSubredditInput("");
  }

  function removeSubreddit(name: string) {
    setSettings((s) => ({ ...s, subreddits: s.subreddits.filter((n) => n !== name) }));
  }

  function toggleFeed(feed: (typeof FEED_OPTIONS)[number]) {
    setSettings((s) => {
      const has = s.pipeline.feeds.includes(feed);
      return {
        ...s,
        pipeline: {
          ...s.pipeline,
          feeds: has
            ? s.pipeline.feeds.filter((f) => f !== feed)
            : [...s.pipeline.feeds, feed],
        },
      };
    });
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      await saveSettings(settings);
      setMessage({ kind: "ok", text: "Settings saved." });
    } catch {
      setMessage({ kind: "err", text: "Failed to save settings." });
    } finally {
      setSaving(false);
    }
  }

  async function handleStartRun() {
    setStarting(true);
    setMessage(null);
    try {
      await startRun({
        subreddits: settings.subreddits,
        llm_config: settings.llm_config as unknown as Record<string, unknown>,
      });
      setMessage({
        kind: "ok",
        text: usingMocks
          ? "Run queued (mock mode — no backend connected)."
          : "Run started.",
      });
    } catch {
      setMessage({ kind: "err", text: "Failed to start run." });
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="space-y-6">
      {usingMocks ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
          No <code className="font-mono">NEXT_PUBLIC_API_URL</code> set — changes are local only.
          Set it to connect the FastAPI backend.
        </div>
      ) : null}

      {message ? (
        <div
          className={
            message.kind === "ok"
              ? "rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
          }
        >
          {message.text}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button variant="outline" onClick={handleSave} disabled={saving}>
          <Save className="h-4 w-4" />
          {saving ? "Saving…" : "Save settings"}
        </Button>
        <Button onClick={handleStartRun} disabled={starting || settings.subreddits.length === 0}>
          <Play className="h-4 w-4" />
          {starting ? "Starting…" : "Start run"}
        </Button>
      </div>

      {/* LLM config */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">LLM configuration</CardTitle>
          <CardDescription>
            Provider-agnostic. All LLM access goes through <code>factory.py</code> — no node
            instantiates a model directly.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={settings.llm_config.provider}
              onValueChange={(v) => updateLLM({ provider: v as Provider })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDER_OPTIONS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <Input
              id="model"
              value={settings.llm_config.model}
              onChange={(e) => updateLLM({ model: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="api_key">API key</Label>
            <Input
              id="api_key"
              type="password"
              placeholder="sk-…"
              value={String(settings.llm_config.config.api_key ?? "")}
              onChange={(e) => updateLLM({ api_key: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="base_url">Base URL (optional)</Label>
            <Input
              id="base_url"
              placeholder="http://localhost:11434"
              value={String(settings.llm_config.config.base_url ?? "")}
              onChange={(e) => updateLLM({ base_url: e.target.value })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Subreddits */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subreddits</CardTitle>
          <CardDescription>Targets for the next collection run.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Add subreddit (e.g. SaaS)"
              value={subredditInput}
              onChange={(e) => setSubredditInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSubreddit();
                }
              }}
            />
            <Button type="button" variant="secondary" onClick={addSubreddit}>
              Add
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {settings.subreddits.map((s) => (
              <Badge key={s} variant="secondary" className="gap-1">
                r/{s}
                <button onClick={() => removeSubreddit(s)} aria-label={`Remove ${s}`}>
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
            {settings.subreddits.length === 0 ? (
              <p className="text-sm text-muted-foreground">No subreddits added.</p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {/* Pipeline controls */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pipeline controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Feeds to collect</Label>
            <div className="flex flex-wrap gap-2">
              {FEED_OPTIONS.map((feed) => {
                const active = settings.pipeline.feeds.includes(feed);
                return (
                  <button
                    key={feed}
                    type="button"
                    onClick={() => toggleFeed(feed)}
                    className={
                      active
                        ? "rounded-md border border-primary bg-primary px-3 py-1 text-xs font-medium text-primary-foreground"
                        : "rounded-md border px-3 py-1 text-xs font-medium text-muted-foreground hover:bg-accent"
                    }
                  >
                    {feed}
                  </button>
                );
              })}
            </div>
          </div>
          <Separator />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <NumberField
              label="Feed limit"
              value={settings.pipeline.feed_limit}
              onChange={(v) =>
                setSettings((s) => ({ ...s, pipeline: { ...s.pipeline, feed_limit: v } }))
              }
            />
            <NumberField
              label="Comment depth"
              value={settings.pipeline.comment_depth}
              onChange={(v) =>
                setSettings((s) => ({ ...s, pipeline: { ...s.pipeline, comment_depth: v } }))
              }
            />
            <NumberField
              label="Dedup threshold (×100)"
              value={Math.round(settings.pipeline.dedup_threshold * 100)}
              step={1}
              onChange={(v) =>
                setSettings((s) => ({
                  ...s,
                  pipeline: { ...s.pipeline, dedup_threshold: v / 100 },
                }))
              }
            />
            <NumberField
              label="Min content length"
              value={settings.pipeline.min_length}
              onChange={(v) =>
                setSettings((s) => ({ ...s, pipeline: { ...s.pipeline, min_length: v } }))
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Validation thresholds — read-only per AGENTS.md rule #7 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Validation thresholds</CardTitle>
          <CardDescription>
            Minimum signals for a valid opportunity. When in doubt, the system rejects rather than
            lowering a threshold.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Threshold label="Unique mentions" value={settings.pipeline.validation.min_unique_mentions} />
          <Threshold label="Unique users" value={settings.pipeline.validation.min_unique_users} />
          <Threshold label="Unique threads" value={settings.pipeline.validation.min_unique_threads} />
          <Threshold label="Avg confidence" value={settings.pipeline.validation.min_avg_confidence} />
        </CardContent>
      </Card>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  step,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function Threshold({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-muted/40 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">≥ {value}</p>
    </div>
  );
}
