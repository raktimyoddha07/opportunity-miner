import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter } from "next/font/google";
import { Database } from "lucide-react";

import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { AppSidebar } from "@/components/app-sidebar";
import { MobileNav } from "@/components/mobile-nav";
import { usingMocks } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Reddit Opportunity Miner",
  description:
    "Collect Reddit discussions, extract recurring pain points, cluster them into validated opportunities, and generate business ideas from strong signals.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <div className="flex min-h-screen w-full flex-col md:flex-row">
            <AppSidebar />
            <div className="flex min-h-screen flex-1 flex-col">
              <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-2 border-b bg-background/95 px-4 backdrop-blur md:px-6">
                <div className="flex items-center gap-2">
                  <MobileNav />
                  <span className="text-sm font-medium md:hidden">Opportunity Miner</span>
                </div>
                <div className="flex items-center gap-3">
                  {usingMocks ? (
                    <Badge variant="warning" className="hidden sm:inline-flex">
                      <Database className="mr-1 h-3 w-3" />
                      Mock data
                    </Badge>
                  ) : null}
                  <ThemeToggle />
                </div>
              </header>
              <main className="flex-1 p-4 md:p-6 lg:p-8">{children}</main>
            </div>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
