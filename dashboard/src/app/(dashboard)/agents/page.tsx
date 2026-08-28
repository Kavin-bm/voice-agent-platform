"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { LinkButton } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill, versionStatusTone } from "@/components/StatusPill";
import { IconChevronRight, IconPlus } from "@/components/icons";
import type { Agent, AgentVersion, Business } from "@/lib/types";
import { useMemo } from "react";

export default function AgentsPage() {
  const agents = useAsync<Agent[]>(() => api.listAgents(), []);
  const businesses = useAsync<Business[]>(() => api.listBusinesses(), []);

  const businessById = useMemo(() => {
    const map = new Map<string, Business>();
    businesses.data?.forEach((b) => map.set(b.id, b));
    return map;
  }, [businesses.data]);

  return (
    <div>
      <PageHeader
        kicker="Deployments"
        title="Agents"
        description="One agent is a template plus a business — a Receptionist for Smile Dental, a Sales agent for a real-estate client."
        actions={
          <LinkButton href="/agents/new">
            <IconPlus className="h-4 w-4" />
            Deploy new agent
          </LinkButton>
        }
      />

      {agents.isLoading && <p className="text-sm text-ink-soft">Loading…</p>}
      {agents.error && <p className="text-sm text-bad">{agents.error}</p>}

      {agents.data && agents.data.length === 0 && (
        <EmptyState
          title="No agents deployed"
          description="Pick a template, attach it to a business, and publish it — that's the whole flow."
          action={
            <LinkButton href="/agents/new" variant="secondary">
              <IconPlus className="h-4 w-4" />
              Deploy new agent
            </LinkButton>
          }
        />
      )}

      {agents.data && agents.data.length > 0 && (
        <div className="flex flex-col rounded-lg border border-rule bg-surface divide-y divide-rule overflow-hidden">
          {agents.data.map((agent) => (
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
    <Link href={`/agents/${agent.id}`} className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-surface-raised transition-colors">
      <div className="min-w-0">
        <p className="text-sm font-semibold truncate">{agent.name}</p>
        <p className="text-xs text-ink-soft truncate mt-0.5">{business?.name ?? "—"}</p>
      </div>
      <div className="flex items-center gap-3 flex-none">
        {latest && <StatusPill tone={versionStatusTone(latest.status)}>{latest.status}</StatusPill>}
        <IconChevronRight className="h-4 w-4 text-ink-soft" />
      </div>
    </Link>
  );
}
