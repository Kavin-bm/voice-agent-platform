"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Field, baseInputClass, inputClass } from "@/components/Field";
import { WizardSteps } from "@/components/WizardSteps";
import { BusinessForm } from "@/components/BusinessForm";
import { IconCheck, IconPlus } from "@/components/icons";
import type { AgentTemplate, Business, CompiledSpec, VerticalPack } from "@/lib/types";

const STEPS = [{ label: "Business" }, { label: "Template" }, { label: "Details" }, { label: "Deploy" }];

interface DraftPolicy {
  category: string;
  rule_text: string;
}

export default function NewAgentWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  const [businessId, setBusinessId] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [verticalPackId, setVerticalPackId] = useState<string | null>(null);
  const [agentName, setAgentName] = useState("");
  const [policies, setPolicies] = useState<DraftPolicy[]>([]);

  const businesses = useAsync<Business[]>(() => api.listBusinesses(), []);
  const templates = useAsync<AgentTemplate[]>(() => api.listTemplates(), []);
  const verticalPacks = useAsync<VerticalPack[]>(
    () => (templateId ? api.listVerticalPacks(templateId) : Promise.resolve([])),
    [templateId]
  );

  const selectedBusiness = businesses.data?.find((b) => b.id === businessId);
  const selectedTemplate = templates.data?.find((t) => t.id === templateId);
  const selectedPack = verticalPacks.data?.find((v) => v.id === verticalPackId);
  const defaultAgentName = selectedBusiness ? `${selectedTemplate?.name ?? "Agent"} — ${selectedBusiness.name}` : "";

  const canAdvance = [
    Boolean(businessId),
    Boolean(templateId),
    (agentName || defaultAgentName).trim().length > 0,
    true,
  ][step];

  return (
    <div className="max-w-3xl">
      <PageHeader kicker="New deployment" title="Deploy an agent" description="Template + business + knowledge + policies + tools — the whole composition, in one guided flow." />

      <WizardSteps steps={STEPS} current={step} />

      <div className="rounded-lg border border-rule bg-surface p-7">
        {step === 0 && businesses.isLoading && <p className="text-sm text-ink-soft">Loading businesses…</p>}
        {step === 0 && !businesses.isLoading && (
          <StepBusiness
            businesses={businesses.data ?? []}
            selectedId={businessId}
            onSelect={setBusinessId}
            onCreated={(b) => {
              businesses.reload();
              setBusinessId(b.id);
            }}
          />
        )}

        {step === 1 && (
          <StepTemplate
            templates={templates.data ?? []}
            verticalPacks={verticalPacks.data ?? []}
            templateId={templateId}
            verticalPackId={verticalPackId}
            onSelectTemplate={(id) => {
              setTemplateId(id);
              setVerticalPackId(null);
            }}
            onSelectPack={setVerticalPackId}
          />
        )}

        {step === 2 && (
          <StepDetails
            agentName={agentName}
            onNameChange={setAgentName}
            defaultName={defaultAgentName}
            policies={policies}
            onPoliciesChange={setPolicies}
          />
        )}

        {step === 3 && selectedBusiness && selectedTemplate && businessId && templateId && (
          <StepDeploy
            business={selectedBusiness}
            template={selectedTemplate}
            verticalPack={selectedPack}
            agentName={agentName}
            policies={policies}
            businessId={businessId}
            templateId={templateId}
            verticalPackId={verticalPackId}
            onDone={(agentId) => router.push(`/agents/${agentId}`)}
          />
        )}
      </div>

      {step < 3 && (
        <div className="mt-6 flex items-center justify-between">
          <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
            Back
          </Button>
          <Button onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))} disabled={!canAdvance}>
            Continue
          </Button>
        </div>
      )}
      {step === 3 && (
        <div className="mt-6">
          <Button variant="ghost" onClick={() => setStep(2)}>
            Back
          </Button>
        </div>
      )}
    </div>
  );
}

function StepBusiness({
  businesses,
  selectedId,
  onSelect,
  onCreated,
}: {
  businesses: Business[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreated: (b: Business) => void;
}) {
  const [creating, setCreating] = useState(businesses.length === 0);

  if (creating) {
    return (
      <div>
        <p className="text-sm text-ink-soft mb-4">Add the client&apos;s business first.</p>
        <BusinessForm
          onCreated={(b) => {
            onCreated(b);
            setCreating(false);
          }}
          onCancel={businesses.length > 0 ? () => setCreating(false) : undefined}
        />
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-ink-soft mb-4">Which business is this agent for?</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 mb-4">
        {businesses.map((b) => (
          <button
            key={b.id}
            type="button"
            onClick={() => onSelect(b.id)}
            className={`text-left rounded-md border px-4 py-3 transition-colors ${
              selectedId === b.id ? "border-wire bg-wire/5" : "border-rule hover:border-rule-strong"
            }`}
          >
            <p className="text-sm font-semibold">{b.name}</p>
            <p className="text-xs text-ink-soft mt-0.5">{b.default_transfer_number || "No transfer number set"}</p>
          </button>
        ))}
      </div>
      <Button variant="ghost" onClick={() => setCreating(true)}>
        <IconPlus className="h-4 w-4" />
        New business
      </Button>
    </div>
  );
}

function StepTemplate({
  templates,
  verticalPacks,
  templateId,
  verticalPackId,
  onSelectTemplate,
  onSelectPack,
}: {
  templates: AgentTemplate[];
  verticalPacks: VerticalPack[];
  templateId: string | null;
  verticalPackId: string | null;
  onSelectTemplate: (id: string) => void;
  onSelectPack: (id: string | null) => void;
}) {
  return (
    <div>
      <p className="text-sm text-ink-soft mb-4">What role does this agent play?</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 mb-6">
        {templates.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelectTemplate(t.id)}
            className={`text-left rounded-md border px-4 py-3 transition-colors ${
              templateId === t.id ? "border-wire bg-wire/5" : "border-rule hover:border-rule-strong"
            }`}
          >
            <p className="text-sm font-semibold">{t.name}</p>
          </button>
        ))}
      </div>

      {templateId && (
        <div>
          <p className="text-sm text-ink-soft mb-3">
            {verticalPacks.length > 0 ? "Any industry specifics for this business?" : "No vertical pack for this template yet — the generic version will be used."}
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => onSelectPack(null)}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                verticalPackId === null ? "border-wire bg-wire/5 text-wire" : "border-rule text-ink-soft hover:border-rule-strong"
              }`}
            >
              Generic
            </button>
            {verticalPacks.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => onSelectPack(v.id)}
                className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                  verticalPackId === v.id ? "border-wire bg-wire/5 text-wire" : "border-rule text-ink-soft hover:border-rule-strong"
                }`}
              >
                {v.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StepDetails({
  agentName,
  defaultName,
  onNameChange,
  policies,
  onPoliciesChange,
}: {
  agentName: string;
  defaultName: string;
  onNameChange: (v: string) => void;
  policies: DraftPolicy[];
  onPoliciesChange: (p: DraftPolicy[]) => void;
}) {
  return (
    <div className="flex flex-col gap-6">
      <Field label="Agent name" required hint="Shown in the agent list — the caller never hears this.">
        <input
          value={agentName || defaultName}
          onChange={(e) => onNameChange(e.target.value)}
          className={inputClass}
        />
      </Field>

      <div>
        <p className="text-xs font-mono uppercase tracking-wide text-ink-soft mb-2">
          Extra policies <span className="normal-case font-body text-ink-soft">— beyond the template defaults, optional</span>
        </p>
        <div className="flex flex-col gap-2 mb-3">
          {policies.map((p, i) => (
            <div key={i} className="flex items-start gap-2 rounded-md border border-rule px-3 py-2">
              <div className="flex-1 text-sm">
                <span className="font-mono text-xs text-copper uppercase mr-2">{p.category}</span>
                {p.rule_text}
              </div>
              <button
                type="button"
                onClick={() => onPoliciesChange(policies.filter((_, idx) => idx !== i))}
                className="text-xs text-ink-soft hover:text-bad flex-none"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
        <PolicyAdder onAdd={(p) => onPoliciesChange([...policies, p])} />
      </div>
    </div>
  );
}

function PolicyAdder({ onAdd }: { onAdd: (p: DraftPolicy) => void }) {
  const [category, setCategory] = useState("");
  const [ruleText, setRuleText] = useState("");

  function handleAdd() {
    if (!category.trim() || !ruleText.trim()) return;
    onAdd({ category: category.trim(), rule_text: ruleText.trim() });
    setCategory("");
    setRuleText("");
  }

  return (
    <div className="flex items-start gap-2">
      <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="category" className={`${baseInputClass} w-32 flex-none`} />
      <input
        value={ruleText}
        onChange={(e) => setRuleText(e.target.value)}
        placeholder="e.g. We do not accept international cards."
        className={`${baseInputClass} flex-1 min-w-0`}
      />
      <Button type="button" variant="secondary" onClick={handleAdd} className="flex-none">
        <IconPlus className="h-4 w-4" />
      </Button>
    </div>
  );
}

function StepDeploy({
  business,
  template,
  verticalPack,
  agentName,
  policies,
  businessId,
  templateId,
  verticalPackId,
  onDone,
}: {
  business: Business;
  template: AgentTemplate;
  verticalPack?: VerticalPack;
  agentName: string;
  policies: DraftPolicy[];
  businessId: string;
  templateId: string;
  verticalPackId: string | null;
  onDone: (agentId: string) => void;
}) {
  const [phase, setPhase] = useState<"review" | "compiling" | "compiled" | "publishing" | "published" | "error">("review");
  const [error, setError] = useState<string | null>(null);
  const [compiledSpec, setCompiledSpec] = useState<CompiledSpec | null>(null);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);

  async function handleCreateAndCompile() {
    setPhase("compiling");
    setError(null);
    try {
      const agent = await api.createAgent({
        business_id: businessId,
        template_id: templateId,
        vertical_pack_id: verticalPackId,
        name: agentName || `${template.name} — ${business.name}`,
      });
      const version = await api.createAgentVersion(agent.id);
      for (const p of policies) {
        await api.createPolicy(agent.id, version.id, p);
      }
      const compiled = await api.compileAgentVersion(agent.id, version.id);
      setAgentId(agent.id);
      setVersionId(version.id);
      setCompiledSpec(compiled.compiled_spec as unknown as CompiledSpec);
      setPhase("compiled");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong while compiling.");
      setPhase("error");
    }
  }

  async function handlePublish() {
    if (!agentId || !versionId) return;
    setPhase("publishing");
    setError(null);
    try {
      await api.publishAgentVersion(agentId, versionId);
      setPhase("published");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't publish to the runtime.");
      setPhase("error");
    }
  }

  return (
    <div>
      <p className="text-sm text-ink-soft mb-4">Review, then deploy.</p>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm mb-6">
        <SummaryRow label="Business" value={business.name} />
        <SummaryRow label="Template" value={template.name} />
        <SummaryRow label="Vertical pack" value={verticalPack?.name ?? "Generic"} />
        <SummaryRow label="Extra policies" value={String(policies.length)} />
      </dl>

      {phase === "review" && <Button onClick={handleCreateAndCompile}>Create &amp; compile</Button>}
      {phase === "compiling" && <p className="text-sm text-ink-soft">Compiling the agent spec…</p>}

      {(phase === "compiled" || phase === "publishing" || phase === "published") && compiledSpec && (
        <div className="mb-5">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-soft mb-2 flex items-center gap-1.5">
            <IconCheck className="h-3.5 w-3.5 text-good" /> Compiled
          </p>
          <div className="rounded-md border border-rule bg-ground p-4 mb-4">
            <p className="text-xs font-mono uppercase tracking-wide text-ink-soft mb-1.5">Tools attached</p>
            <div className="flex flex-wrap gap-1.5">
              {compiledSpec.tools.map((t) => (
                <span key={t.name} className="rounded-full border border-rule px-2.5 py-0.5 text-xs font-mono">
                  {t.name}
                </span>
              ))}
            </div>
          </div>

          {phase === "compiled" && <Button onClick={handlePublish}>Publish to runtime</Button>}
          {phase === "publishing" && <p className="text-sm text-ink-soft">Provisioning the runtime and publishing…</p>}
          {phase === "published" && agentId && (
            <div>
              <p className="text-sm text-good mb-3 flex items-center gap-1.5">
                <IconCheck className="h-4 w-4" /> Published — this agent is live in the runtime.
              </p>
              <Button onClick={() => onDone(agentId)}>Go to agent</Button>
            </div>
          )}
        </div>
      )}

      {phase === "error" && (
        <div>
          <p className="text-sm text-bad mb-3">{error}</p>
          {agentId && versionId ? (
            <Button onClick={handlePublish}>Retry publish</Button>
          ) : (
            <Button onClick={handleCreateAndCompile}>Retry</Button>
          )}
          {agentId && (
            <Button variant="ghost" className="ml-2" onClick={() => onDone(agentId)}>
              View agent anyway
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-mono uppercase tracking-wide text-ink-soft">{label}</dt>
      <dd className="font-medium mt-0.5">{value}</dd>
    </div>
  );
}
