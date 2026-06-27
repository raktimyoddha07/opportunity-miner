"use client";

/**
 * shadcn-style chart wrapper around recharts. Provides ChartContainer,
 * ChartTooltip, and ChartTooltipContent plus a shared chartConfig type so every
 * chart page uses the same theming tokens (chart-1..5 from globals.css).
 */

import * as React from "react";
import * as RechartsPrimitive from "recharts";

import { cn } from "@/lib/utils";

export type ChartConfig = {
  [k in string]: {
    label?: React.ReactNode;
    icon?: React.ComponentType;
    color?: string;
  };
};

const ChartContext = React.createContext<{ config: ChartConfig } | null>(null);

function useChart() {
  const ctx = React.useContext(ChartContext);
  if (!ctx) throw new Error("useChart must be used within a <ChartContainer />");
  return ctx;
}

const ChartContainer = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<"div"> & {
    config: ChartConfig;
    children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
  }
>(({ id, className, children, config, ...props }, ref) => {
  const uniqueId = React.useId();
  const chartId = `chart-${id ?? uniqueId.replace(/:/g, "")}`;
  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-chart={chartId}
        ref={ref}
        className={cn(
          "flex aspect-video justify-center text-xs",
          "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line]:stroke-border/50",
          className,
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>{children}</RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
});
ChartContainer.displayName = "ChartContainer";

const ChartStyle = ({ id, config }: { id: string; config: ChartConfig }) => {
  const colorConfig = Object.entries(config).filter(([_, c]) => c.color);
  if (!colorConfig.length) return null;
  return (
    <style
      dangerouslySetInnerHTML={{
        __html: Object.entries(config)
          .filter(([_, c]) => c.color)
          .map(
            ([key, c]) =>
              `[data-chart="${id}"]{--color-${key}:${c.color}}`,
          )
          .join("\n"),
      }}
    />
  );
};

const ChartTooltip = RechartsPrimitive.Tooltip;

const ChartTooltipContent = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof RechartsPrimitive.Tooltip> &
    React.ComponentProps<"div"> & {
      hideLabel?: boolean;
      nameKey?: string;
      active?: boolean;
      payload?: any[];
    }
>(({ active, payload, className, hideLabel = false, nameKey, ...props }, ref) => {
  const { config } = useChart();
  if (!active || !payload?.length) return null;
  const label = hideLabel ? null : (
    <div className="grid gap-1.5 pb-2 text-sm font-medium">{payload[0]?.payload?.name ?? ""}</div>
  );
  return (
    <div
      ref={ref}
      className={cn(
        "grid min-w-[8rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl",
        className,
      )}
      {...props}
    >
      {label}
      <div className="grid gap-1.5">
        {payload.map((item: any, idx: number) => {
          const key = (nameKey ?? item.name ?? item.dataKey) as string;
          const itemConfig = config[key as string];
          return (
            <div key={idx} className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span
                  className="h-2 w-2 rounded-sm"
                  style={{ backgroundColor: item.color ?? itemConfig?.color }}
                />
                {itemConfig?.label ?? key}
              </span>
              <span className="font-mono font-medium text-foreground">
                {item.value as React.ReactNode}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
});
ChartTooltipContent.displayName = "ChartTooltipContent";

export { ChartContainer, ChartTooltip, ChartTooltipContent, ChartStyle, useChart };
