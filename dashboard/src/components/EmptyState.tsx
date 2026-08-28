export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-rule-strong bg-surface/50 px-6 py-16 text-center">
      <p className="font-display text-xl font-bold uppercase tracking-wide">{title}</p>
      <p className="text-sm text-ink-soft max-w-sm">{description}</p>
      {action}
    </div>
  );
}
