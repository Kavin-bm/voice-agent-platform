"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { IconBuilding, IconGrid, IconHeadset, IconKey, IconLogout } from "./icons";

const NAV = [
  { href: "/", label: "Overview", icon: IconGrid },
  { href: "/businesses", label: "Businesses", icon: IconBuilding },
  { href: "/agents", label: "Agents", icon: IconHeadset },
  { href: "/credentials", label: "Credentials", icon: IconKey },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className="flex h-full flex-col px-4 py-6">
      <div className="mb-8 px-2">
        <p className="font-display text-xl font-extrabold tracking-wide uppercase leading-none">Voice&nbsp;Agent</p>
        <p className="font-mono text-[11px] uppercase tracking-widest text-ink-soft mt-1">Operator console</p>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5">
        {NAV.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors border-l-2 ${
                active
                  ? "border-wire bg-surface text-ink font-semibold"
                  : "border-transparent text-ink-soft hover:text-ink hover:bg-surface/60"
              }`}
            >
              <Icon className="h-4 w-4 flex-none" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-3 rounded-md px-2.5 py-2 text-sm text-ink-soft hover:text-bad hover:bg-surface/60 transition-colors"
      >
        <IconLogout className="h-4 w-4 flex-none" />
        Log out
      </button>
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-60 md:flex-none md:border-r md:border-rule">
        <SidebarContent />
      </aside>

      {/* Mobile top bar */}
      <div className="fixed inset-x-0 top-0 z-30 flex items-center justify-between border-b border-rule bg-ground px-4 py-3 md:hidden">
        <p className="font-display text-lg font-extrabold tracking-wide uppercase leading-none">Voice&nbsp;Agent</p>
        <button
          onClick={() => setDrawerOpen(true)}
          aria-label="Open menu"
          className="flex h-9 w-9 items-center justify-center rounded-md border border-rule text-ink"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4 stroke-current" strokeWidth="1.6">
            <line x1="3" y1="6" x2="17" y2="6" strokeLinecap="round" />
            <line x1="3" y1="10" x2="17" y2="10" strokeLinecap="round" />
            <line x1="3" y1="14" x2="17" y2="14" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-ground border-r border-rule">
            <SidebarContent onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}

      <main className="flex-1 min-w-0 px-4 py-6 pt-20 md:px-10 md:py-8 md:pt-8">{children}</main>
    </div>
  );
}
