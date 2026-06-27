import { cn } from "@/lib/utils";
import { scoreColor, scoreLabel } from "@/lib/constants";

/** Renders a 0-100 score with a qualitative label and color. */
export function ScoreBadge({ score, className }: { score: number; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm font-semibold", scoreColor(score), className)}>
      <span className="font-mono">{Math.round(score)}</span>
      <span className="text-xs font-medium opacity-80">{scoreLabel(score)}</span>
    </span>
  );
}
