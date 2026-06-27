"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Boxes,
  FileText,
  Lightbulb,
  ListChecks,
  PlayCircle,
  Settings,
  ShieldCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";

/** Primary navigation. Routes mirror AGENTS.md Frontend Pages table. */
const nav = [
  { href: "/", label: "Dashboard", icon: BarChart3 },
  { href: "/opportunities", label: "Opportunities", icon: ListChecks },
  { href: "/clusters", label: "Clusters", icon: Boxes },
  { href: "/evidence", label: "Evidence", icon: ShieldCheck },
  { href: "/ideas", label: "Ideas", icon: Lightbulb },
  { href: "/runs", label: "Runs", icon: PlayCircle },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 border-r bg-card md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <FileText className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold">Opportunity Miner</p>
          <p className="text-xs text-muted-foreground">Reddit research</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {nav.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-4 text-xs text-muted-foreground">
        <p>Validated problems are the moat.</p>
      </div>
    </aside>
  );
}
