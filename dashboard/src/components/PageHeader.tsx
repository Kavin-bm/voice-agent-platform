export function PageHeader({
  kicker,
  title,
  description,
  actions,
}: {
  kicker?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 sm:gap-6 mb-8">
      <div className="min-w-0">
        {kicker && (
          <p className="font-mono text-xs uppercase tracking-widest text-copper mb-1.5">{kicker}</p>
        )}
        <h1 className="font-display text-3xl font-extrabold uppercase tracking-wide leading-none text-balance">{title}</h1>
        {description && <p className="mt-2.5 text-sm text-ink-soft max-w-lg">{description}</p>}
      </div>
      {actions && <div className="flex-none flex items-center gap-2">{actions}</div>}
    </div>
  );
}
