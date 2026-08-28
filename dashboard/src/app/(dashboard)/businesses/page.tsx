"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { BusinessForm } from "@/components/BusinessForm";
import { IconChevronRight, IconPlus } from "@/components/icons";
import type { Business } from "@/lib/types";

export default function BusinessesPage() {
  const businesses = useAsync<Business[]>(() => api.listBusinesses(), []);
  const [showForm, setShowForm] = useState(false);

  return (
    <div>
      <PageHeader
        kicker="Clients"
        title="Businesses"
        description="Each business holds structured facts and knowledge one or more agents draw on."
        actions={
          <Button onClick={() => setShowForm((v) => !v)}>
            <IconPlus className="h-4 w-4" />
            Add business
          </Button>
        }
      />

      {showForm && (
        <div className="mb-8">
          <BusinessForm
            onCreated={() => {
              setShowForm(false);
              businesses.reload();
            }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {businesses.isLoading && <p className="text-sm text-ink-soft">Loading…</p>}
      {businesses.error && <p className="text-sm text-bad">{businesses.error}</p>}

      {businesses.data && businesses.data.length === 0 && !showForm && (
        <EmptyState
          title="No businesses yet"
          description="Add the client's business — name, hours, languages, and a transfer number — before creating an agent for them."
          action={
            <Button variant="secondary" onClick={() => setShowForm(true)}>
              <IconPlus className="h-4 w-4" />
              Add business
            </Button>
          }
        />
      )}

      {businesses.data && businesses.data.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {businesses.data.map((b) => (
            <Link
              key={b.id}
              href={`/businesses/${b.id}`}
              className="group flex items-center justify-between gap-3 rounded-lg border border-rule bg-surface px-5 py-4 hover:border-wire transition-colors"
            >
              <div className="min-w-0">
                <p className="font-semibold text-sm truncate">{b.name}</p>
                <p className="text-xs text-ink-soft truncate mt-0.5">
                  {(b.structured_config?.languages as string[] | undefined)?.join(", ") || "No languages set"}
                </p>
              </div>
              <IconChevronRight className="h-4 w-4 flex-none text-ink-soft group-hover:text-wire" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
