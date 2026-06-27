"use client";

import * as React from "react";
import { Download, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { exportUrl } from "@/lib/api";

export function ExportDropdown() {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      <Button variant="outline" onClick={() => setOpen(!open)} className="gap-2">
        <Download className="h-4 w-4" />
        Export
        <ChevronDown className="h-3 w-3 opacity-50" />
      </Button>

      {open && (
        <div className="absolute right-0 mt-2 w-48 origin-top-right rounded-md border bg-popover text-popover-foreground shadow-md outline-none animate-in fade-in-50 zoom-in-95 z-50">
          <div className="py-1">
            <a
              href={exportUrl("json")}
              download
              className="flex items-center px-4 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => setOpen(false)}
            >
              JSON Dataset
            </a>
            <a
              href={exportUrl("markdown")}
              download
              className="flex items-center px-4 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => setOpen(false)}
            >
              Markdown Report
            </a>
            <a
              href={exportUrl("csv")}
              download
              className="flex items-center px-4 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => setOpen(false)}
            >
              CSV Sheet
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
