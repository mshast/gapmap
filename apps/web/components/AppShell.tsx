"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, FlaskConical } from "lucide-react";
import { isMockMode } from "@/lib/api";
import { useAppState } from "@/components/AppStateProvider";
import { initialState } from "@/lib/types";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { state, setState } = useAppState();
  const projectHref = state.analysis?.recommended_project_id
    ? `/project/${state.analysis.recommended_project_id}`
    : "/readiness#assessment-title";
  const links = [
    { href: "/", label: "Input" },
    { href: "/readiness", label: "Readiness" },
    { href: projectHref, label: "Projects" },
    { href: "/results", label: "Results" },
  ];
  return (
    <div className="app-frame">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="GapMap home">
          <span className="brand-mark"><Compass size={19} strokeWidth={2.2} /></span>
          <span>gapmap<span className="brand-period">.</span></span>
        </Link>
        <nav className="main-nav" aria-label="Main navigation">
          {links.map((link, index) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href.split("/").slice(0, 2).join("/"));
            return (
              <Link key={link.href} className={`nav-link${active ? " active" : ""}`} href={link.href}>
                <span className="nav-index">0{index + 1}</span>{link.label}
              </Link>
            );
          })}
        </nav>
        <div className={`mode-chip${isMockMode ? " mock" : " live"}`}>
          {isMockMode ? <FlaskConical size={14} /> : <span className="live-dot" />}
          {isMockMode ? "Demo fixtures" : state.analysis?.analysis_mode === "demo" ? "Demo analysis · real SQL" : "API mode"}
        </div>
        <Link className="text-button session-reset" href="/" onClick={() => setState(initialState)}>Reset session</Link>
      </header>
      <main>{children}</main>
      <footer className="footer-note">
        <span>GapMap · Evidence, not odds.</span>
        <span>Resume claims are not test results.</span>
      </footer>
    </div>
  );
}
