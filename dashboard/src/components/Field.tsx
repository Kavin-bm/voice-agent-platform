// Tailwind's cascade is stylesheet-emission-order, not class-attribute-order
// — appending "w-32" after a className that already contains "w-full" does
// NOT reliably override it. Anything that needs a non-default width must
// start from baseInputClass (no width baked in) rather than fight inputClass.
export const baseInputClass =
  "rounded-md border border-rule bg-ground px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire";

export const inputClass = `${baseInputClass} w-full`;

export function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-mono uppercase tracking-wide text-ink-soft">
        {label}
        {required && <span className="text-copper"> *</span>}
      </span>
      {children}
      {hint && <span className="text-xs text-ink-soft">{hint}</span>}
    </label>
  );
}
