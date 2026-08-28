import { IconCheck } from "./icons";

export interface WizardStep {
  label: string;
}

export function WizardSteps({ steps, current }: { steps: WizardStep[]; current: number }) {
  return (
    <div className="flex items-center mb-10">
      {steps.map((step, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <div key={step.label} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-2 flex-none">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 font-mono text-xs font-semibold transition-colors ${
                  done
                    ? "border-copper bg-copper text-white"
                    : active
                      ? "border-wire text-wire"
                      : "border-rule-strong text-ink-soft"
                }`}
              >
                {done ? <IconCheck className="h-3.5 w-3.5" /> : index + 1}
              </div>
              <span className={`text-xs font-mono uppercase tracking-wide whitespace-nowrap ${active ? "text-ink" : "text-ink-soft"}`}>
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className={`h-0.5 flex-1 mx-2 mb-5 rounded-full ${done ? "bg-copper" : "bg-rule-strong"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
