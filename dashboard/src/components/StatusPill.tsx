const TONES = {
  good: "text-good border-good/40 bg-good/10",
  warn: "text-warn border-warn/40 bg-warn/10",
  bad: "text-bad border-bad/40 bg-bad/10",
  pending: "text-pending border-pending/40 bg-pending/10",
} as const;

export function StatusPill({ tone, children }: { tone: keyof typeof TONES; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wide whitespace-nowrap ${TONES[tone]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function documentStatusTone(status: string): keyof typeof TONES {
  if (status === "ready") return "good";
  if (status === "failed") return "bad";
  if (status === "processing") return "warn";
  return "pending";
}

export function versionStatusTone(status: string): keyof typeof TONES {
  if (status === "published") return "good";
  if (status === "archived") return "pending";
  return "warn";
}
