"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { baseInputClass } from "@/components/Field";
import { StatusPill, versionStatusTone } from "@/components/StatusPill";
import { IconPlus } from "@/components/icons";
import type { Agent, AgentVersion, Business, CompiledSpec, Policy } from "@/lib/types";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const agent = useAsync<Agent>(() => api.getAgent(id), [id]);
  const versions = useAsync<AgentVersion[]>(() => api.listAgentVersions(id), [id]);
  const business = useAsync<Business | null>(
    () => (agent.data ? api.getBusiness(agent.data.business_id) : Promise.resolve(null)),
    [agent.data?.business_id]
  );

  if (agent.isLoading) return <p className="text-sm text-ink-soft">Loading…</p>;
  if (agent.error || !agent.data) return <p className="text-sm text-bad">{agent.error ?? "Agent not found."}</p>;

  return (
    <div>
      <PageHeader
        kicker={business.data?.name ?? "Agent"}
        title={agent.data.name}
        description="Every version is a draft snapshot until published — publishing never disturbs whichever version is already live."
        actions={
          <Button
            variant="secondary"
            onClick={async () => {
              await api.createAgentVersion(id);
              versions.reload();
            }}
          >
            <IconPlus className="h-4 w-4" />
            New draft version
          </Button>
        }
      />

      {versions.isLoading && <p className="text-sm text-ink-soft">Loading versions…</p>}
      {versions.error && <p className="text-sm text-bad">{versions.error}</p>}

      <div className="flex flex-col gap-4">
        {versions.data
          ?.slice()
          .reverse()
          .map((version) => (
            <VersionCard key={version.id} agentId={id} version={version} onChange={versions.reload} />
          ))}
      </div>
    </div>
  );
}

function VersionCard({ agentId, version, onChange }: { agentId: string; version: AgentVersion; onChange: () => void }) {
  const [expanded, setExpanded] = useState(version.status === "draft");
  const [busy, setBusy] = useState<"compile" | "publish" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const policies = useAsync<Policy[]>(() => api.listPolicies(agentId, version.id), [agentId, version.id]);

  const hasCompiledSpec = Object.keys(version.compiled_spec ?? {}).length > 0;
  const spec = version.compiled_spec as unknown as CompiledSpec;

  async function handleCompile() {
    setBusy("compile");
    setError(null);
    try {
      await api.compileAgentVersion(agentId, version.id);
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Compile failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handlePublish() {
    setBusy("publish");
    setError(null);
    try {
      await api.publishAgentVersion(agentId, version.id);
      onChange();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Publish failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-lg border border-rule bg-surface overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-surface-raised transition-colors"
      >
        <span className="text-sm font-semibold font-mono">v{version.version_number}</span>
        <StatusPill tone={versionStatusTone(version.status)}>{version.status}</StatusPill>
      </button>

      {expanded && (
        <div className="border-t border-rule px-5 py-5">
          <div className="mb-5">
            <p className="text-xs font-mono uppercase tracking-wide text-ink-soft mb-2">Policies</p>
            {policies.data && policies.data.length === 0 && <p className="text-xs text-ink-soft">No extra policies on this version.</p>}
            <div className="flex flex-col gap-2 mb-2">
              {policies.data?.map((p) => (
                <div key={p.id} className="rounded-md border border-rule px-3 py-2 text-sm">
                  <span className="font-mono text-xs text-copper uppercase mr-2">{p.category}</span>
                  {p.rule_text}
                </div>
              ))}
            </div>
            {version.status === "draft" && (
              <AddPolicyInline
                agentId={agentId}
                versionId={version.id}
                onAdded={() => {
                  policies.reload();
                }}
              />
            )}
          </div>

          {hasCompiledSpec && (
            <div className="mb-5">
              <p className="text-xs font-mono uppercase tracking-wide text-ink-soft mb-2">Compiled spec</p>
              <div className="rounded-md border border-rule bg-ground p-4 flex flex-col gap-3">
                <SpecRow label="Tools" value={spec.tools?.map((t) => t.name).join(", ") || "none"} />
                <SpecRow label="Policies compiled" value={String(spec.policies?.length ?? 0)} />
                <SpecRow label="Provider stack" value={JSON.stringify(spec.provider_stack ?? {})} mono />
                {version.dograh_workflow_id && <SpecRow label="Dograh workflow" value={version.dograh_workflow_id} mono />}
              </div>
            </div>
          )}

          {error && <p className="text-sm text-bad mb-3">{error}</p>}

          {version.status === "draft" && (
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={handleCompile} disabled={busy !== null}>
                {busy === "compile" ? "Compiling…" : hasCompiledSpec ? "Recompile" : "Compile"}
              </Button>
              <Button onClick={handlePublish} disabled={busy !== null || !hasCompiledSpec}>
                {busy === "publish" ? "Publishing…" : "Publish"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SpecRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="text-ink-soft flex-none">{label}</span>
      <span className={`text-right break-all ${mono ? "font-mono text-xs" : ""}`}>{value}</span>
    </div>
  );
}

function AddPolicyInline({ agentId, versionId, onAdded }: { agentId: string; versionId: string; onAdded: () => void }) {
  const [category, setCategory] = useState("");
  const [ruleText, setRuleText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleAdd() {
    if (!category.trim() || !ruleText.trim()) return;
    setIsSubmitting(true);
    try {
      await api.createPolicy(agentId, versionId, { category: category.trim(), rule_text: ruleText.trim() });
      setCategory("");
      setRuleText("");
      onAdded();
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex items-start gap-2 mt-2">
      <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="category" className={`${baseInputClass} w-28 flex-none`} />
      <input
        value={ruleText}
        onChange={(e) => setRuleText(e.target.value)}
        placeholder="Add a rule…"
        className={`${baseInputClass} flex-1 min-w-0`}
      />
      <Button type="button" variant="secondary" onClick={handleAdd} disabled={isSubmitting} className="flex-none">
        <IconPlus className="h-4 w-4" />
      </Button>
    </div>
  );
}
