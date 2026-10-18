"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { DURATION, EASE, prefersReducedMotion } from "@/lib/motion";
import { useLocalStorageBoolean } from "@/lib/useLocalStorageBoolean";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: HomeIcon },
  { href: "/leads", label: "Leads", icon: LeadsIcon },
];

const STORAGE_KEY = "pitchpilot:sidebar-collapsed";

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useLocalStorageBoolean(STORAGE_KEY, false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  function toggleCollapsed() {
    setCollapsed(!collapsed);
  }

  // Animate the mobile overlay sidebar sliding in/out.
  useGSAP(
    () => {
      if (!overlayRef.current) return;
      if (prefersReducedMotion()) {
        gsap.set(overlayRef.current, { x: mobileOpen ? 0 : "-100%" });
        return;
      }
      gsap.to(overlayRef.current, {
        x: mobileOpen ? 0 : "-100%",
        duration: DURATION,
        ease: EASE,
      });
    },
    { dependencies: [mobileOpen], scope: overlayRef }
  );

  // Inline style, not competing `md:w-*` Tailwind utility classes: two
  // same-specificity width utilities (an arbitrary value vs. a scale
  // value) were found to lose a CSS cascade-order tie in practice --
  // confirmed via getComputedStyle, not assumed -- so the collapsed
  // width never actually applied. The aside is hidden entirely below
  // `md`, so an unconditional inline width is safe there too.
  const sidebarWidth = collapsed ? 72 : 224;

  const content = (onNavigate?: () => void) => (
    <>
      <div className={`flex items-center gap-2 px-4 py-5 ${collapsed ? "md:justify-center md:px-0" : ""}`}>
        <div className="accent-gradient flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white">
          P
        </div>
        <span className={`text-sm font-semibold tracking-tight text-text ${collapsed ? "md:hidden" : ""}`}>
          PitchPilot AI
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              title={collapsed ? item.label : undefined}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                collapsed ? "md:justify-center" : ""
              } ${
                active
                  ? "bg-surface-2 text-text"
                  : "text-text-muted hover:bg-surface-2 hover:text-text"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] shrink-0 ${active ? "text-accent-hover" : "text-text-faint group-hover:text-text-muted"}`}
              />
              <span className={collapsed ? "md:hidden" : ""}>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-3 py-3">
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="hidden w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-text-faint transition-colors hover:bg-surface-2 hover:text-text-muted md:flex"
        >
          <ChevronIcon className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`} />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <div className="accent-gradient flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold text-white">
            P
          </div>
          <span className="text-sm font-semibold text-text">PitchPilot AI</span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="rounded-md p-2 text-text-muted hover:bg-surface-2"
        >
          <MenuIcon className="h-5 w-5" />
        </button>
      </div>

      {/* Mobile overlay sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={overlayRef}
            className="relative flex h-full w-64 -translate-x-full flex-col border-r border-border bg-surface"
          >
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
              className="absolute right-3 top-4 rounded-md p-1.5 text-text-faint hover:bg-surface-2"
            >
              <CloseIcon className="h-4 w-4" />
            </button>
            {content(() => setMobileOpen(false))}
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside
        ref={navRef}
        style={{ width: sidebarWidth }}
        className="hidden shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-300 ease-out md:flex"
      >
        {content()}
      </aside>
    </>
  );
}

function HomeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M4 11.5 12 4l8 7.5M6 10v9a1 1 0 0 0 1 1h3v-5a2 2 0 1 1 4 0v5h3a1 1 0 0 0 1-1v-9"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LeadsIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <rect x="4" y="5" width="16" height="4" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="4" y="11" width="16" height="4" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="4" y="17" width="10" height="2.4" rx="1" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path d="M15 6l-6 6 6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
