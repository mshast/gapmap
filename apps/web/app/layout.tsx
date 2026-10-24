import type { Metadata } from "next";
import { AppStateProvider } from "@/components/AppStateProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "GapMap | Evidence for your next role",
  description: "Turn job requirements into a focused evidence-building roadmap.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <AppStateProvider>{children}</AppStateProvider>
      </body>
    </html>
  );
}
