"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { IconBuilding, IconGrid, IconHeadset, IconKey, IconLogout } from "./icons";

const NAV = [
  { href: "/", label: "Overview", icon: IconGrid },
  { href: "/businesses", label: "Businesses", icon: IconBuilding },
  { href: "/agents", label: "Agents", icon: IconHeadset },
  { href: "/credentials", label: "Credentials", icon: IconKey },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-none flex-col border-r border-rule px-4 py-6">
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
      </aside>

      <main className="flex-1 min-w-0 px-10 py-8">{children}</main>
    </div>
  );
}
