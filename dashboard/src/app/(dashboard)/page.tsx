"use client";

import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { LinkButton } from "@/components/Button";
import { StatusPill, versionStatusTone } from "@/components/StatusPill";
import { IconPlus } from "@/components/icons";
import Link from "next/link";
import { useMemo } from "react";
import type { Agent, AgentVersion, Business } from "@/lib/types";

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-rule bg-surface px-5 py-4">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">{label}</p>
      <p className="font-display text-4xl font-extrabold mt-1">{value}</p>
    </div>
  );
}

export default function OverviewPage() {
  const businesses = useAsync<Business[]>(() => api.listBusinesses(), []);
  const agents = useAsync<Agent[]>(() => api.listAgents(), []);

  const businessById = useMemo(() => {
    const map = new Map<string, Business>();
    businesses.data?.forEach((b) => map.set(b.id, b));
    return map;
  }, [businesses.data]);

  return (
    <div>
      <PageHeader
        kicker="Operator console"
        title="Overview"
        description="Everything running on this control plane, at a glance."
        actions={
          <LinkButton href="/agents/new">
            <IconPlus className="h-4 w-4" />
            Deploy new agent
          </LinkButton>
        }
      />

      <div className="grid grid-cols-2 gap-4 mb-10 sm:grid-cols-3">
        <StatCard label="Businesses" value={businesses.data?.length ?? "—"} />
        <StatCard label="Agents" value={agents.data?.length ?? "—"} />
      </div>

      <h2 className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-3">Recent agents</h2>

      {agents.isLoading && <p className="text-sm text-ink-soft">Loading…</p>}
      {agents.error && <p className="text-sm text-bad">{agents.error}</p>}

      {agents.data && agents.data.length === 0 && (
        <div className="rounded-lg border border-dashed border-rule-strong px-6 py-10 text-center">
          <p className="text-sm text-ink-soft mb-4">No agents yet. Deploy your first one from a template.</p>
          <LinkButton href="/agents/new" variant="secondary">
            <IconPlus className="h-4 w-4" />
            Deploy new agent
          </LinkButton>
        </div>
      )}

      {agents.data && agents.data.length > 0 && (
        <div className="flex flex-col rounded-lg border border-rule bg-surface divide-y divide-rule overflow-hidden">
          {agents.data.slice(0, 8).map((agent) => (
            <AgentRow key={agent.id} agent={agent} business={businessById.get(agent.business_id)} />
          ))}
        </div>
      )}
    </div>
  );
}

function AgentRow({ agent, business }: { agent: Agent; business?: Business }) {
  const versions = useAsync<AgentVersion[]>(() => api.listAgentVersions(agent.id), [agent.id]);
  const latest = versions.data?.[versions.data.length - 1];

  return (
    <Link href={`/agents/${agent.id}`} className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-surface-raised transition-colors">
      <div className="min-w-0">
        <p className="text-sm font-semibold truncate">{agent.name}</p>
        <p className="text-xs text-ink-soft truncate">{business?.name ?? "—"}</p>
      </div>
      {latest && <StatusPill tone={versionStatusTone(latest.status)}>{latest.status}</StatusPill>}
    </Link>
  );
}
