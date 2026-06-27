"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Boxes,
  Lightbulb,
  ListChecks,
  Menu,
  PlayCircle,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: BarChart3 },
  { href: "/opportunities", label: "Opportunities", icon: ListChecks },
  { href: "/clusters", label: "Clusters", icon: Boxes },
  { href: "/evidence", label: "Evidence", icon: ShieldCheck },
  { href: "/ideas", label: "Ideas", icon: Lightbulb },
  { href: "/runs", label: "Runs", icon: PlayCircle },
  { href: "/settings", label: "Settings", icon: Settings },
];

/** Top-bar navigation shown on screens below the `md` breakpoint. */
export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);

  return (
    <div className="md:hidden">
      <Button variant="ghost" size="icon" aria-label="Open menu" onClick={() => setOpen(true)}>
        <Menu className="h-5 w-5" />
      </Button>
      {open ? (
        <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setOpen(false)}>
          <div
            className="absolute left-0 top-0 h-full w-64 bg-card p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <span className="font-semibold">Menu</span>
              <Button variant="ghost" size="icon" aria-label="Close" onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <nav className="space-y-1">
              {nav.map((item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium",
                      active
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      ) : null}
    </div>
  );
}
