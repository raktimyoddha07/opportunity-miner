"use client";

import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

interface CategoryData {
  category: string;
  count: number;
}

interface DashboardChartsProps {
  categoryData: CategoryData[];
  trendData: Record<string, string | number>[];
  clusterNames: string[];
}

export function DashboardCharts({
  categoryData,
  trendData,
  clusterNames,
}: DashboardChartsProps) {
  const categoryConfig: ChartConfig = {
    count: { label: "Opportunities", color: "hsl(var(--chart-1))" },
  };

  const trendConfig: ChartConfig = {
    [clusterNames[0] ?? "cluster"]: {
      label: clusterNames[0] ?? "Cluster",
      color: "hsl(var(--chart-1))",
    },
    [clusterNames[1] ?? ""]: {
      label: clusterNames[1] ?? "",
      color: "hsl(var(--chart-2))",
    },
    [clusterNames[2] ?? ""]: {
      label: clusterNames[2] ?? "",
      color: "hsl(var(--chart-3))",
    },
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Opportunities by category</CardTitle>
          <CardDescription>Where recurring pain points concentrate.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={categoryConfig} className="h-[260px] w-full">
            <BarChart data={categoryData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="category" tickLine={false} axisLine={false} fontSize={11} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="count" fill="var(--color-count)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Frequency trend</CardTitle>
          <CardDescription>Cluster frequency across recent runs.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={trendConfig} className="h-[260px] w-full">
            <LineChart data={trendData} margin={{ left: -10, right: 10 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} width={28} />
              <ChartTooltip content={<ChartTooltipContent />} />
              {clusterNames.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={`hsl(var(--chart-${(i % 5) + 1}))`}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ChartContainer>
        </CardContent>
      </Card>
    </div>
  );
}
