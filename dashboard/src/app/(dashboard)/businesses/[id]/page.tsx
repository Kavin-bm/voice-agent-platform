"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { Field, inputClass } from "@/components/Field";
import { StatusPill, documentStatusTone } from "@/components/StatusPill";
import { IconPlus, IconUpload } from "@/components/icons";
import type { Business, DocumentRecord, KnowledgeSource } from "@/lib/types";

export default function BusinessDetailPage() {
  const { id } = useParams<{ id: string }>();
  const business = useAsync<Business>(() => api.getBusiness(id), [id]);
  const allSources = useAsync<KnowledgeSource[]>(() => api.listKnowledgeSources(), []);
  const [showSourceForm, setShowSourceForm] = useState(false);

  const sources = allSources.data?.filter((s) => s.business_id === id) ?? [];

  if (business.isLoading) return <p className="text-sm text-ink-soft">Loading…</p>;
  if (business.error || !business.data) return <p className="text-sm text-bad">{business.error ?? "Business not found."}</p>;

  const config = business.data.structured_config as { hours?: string; languages?: string[] };

  return (
    <div>
      <PageHeader
        kicker="Business"
        title={business.data.name}
        description="Structured facts the agent treats as ground truth, plus the knowledge base it searches during a call."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-10">
        <FactCard label="Hours" value={config.hours || "Not set"} />
        <FactCard label="Languages" value={config.languages?.join(", ") || "Not set"} />
        <FactCard label="Transfer number" value={business.data.default_transfer_number || "Not set"} />
      </div>

      <div className="flex items-center justify-between mb-3">
        <h2 className="font-mono text-xs uppercase tracking-widest text-ink-soft">Knowledge sources</h2>
        <Button variant="secondary" onClick={() => setShowSourceForm((v) => !v)}>
          <IconPlus className="h-4 w-4" />
          New source
        </Button>
      </div>

      {showSourceForm && (
        <NewSourceForm
          businessId={id}
          onCreated={() => {
            setShowSourceForm(false);
            allSources.reload();
          }}
          onCancel={() => setShowSourceForm(false)}
        />
      )}

      {sources.length === 0 && !showSourceForm && (
        <p className="text-sm text-ink-soft rounded-lg border border-dashed border-rule-strong px-6 py-8 text-center">
          No knowledge sources yet — create one, then upload the documents this agent should be able to look things up in.
        </p>
      )}

      <div className="flex flex-col gap-4">
        {sources.map((source) => (
          <KnowledgeSourceCard key={source.id} source={source} />
        ))}
      </div>
    </div>
  );
}

function FactCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-rule bg-surface px-4 py-3.5">
      <p className="font-mono text-[11px] uppercase tracking-widest text-ink-soft">{label}</p>
      <p className="text-sm mt-1 font-medium">{value}</p>
    </div>
  );
}

function NewSourceForm({ businessId, onCreated, onCancel }: { businessId: string; onCreated: () => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await api.createKnowledgeSource({ business_id: businessId, name });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the knowledge source.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-5 rounded-lg border border-rule bg-surface p-5 flex items-end gap-3">
      <div className="flex-1">
        <Field label="Name" required>
          <input required value={name} onChange={(e) => setName(e.target.value)} className={inputClass} placeholder="Clinic FAQs" />
        </Field>
      </div>
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating…" : "Create"}
      </Button>
      <Button type="button" variant="ghost" onClick={onCancel}>
        Cancel
      </Button>
      {error && <p className="text-sm text-bad">{error}</p>}
    </form>
  );
}

function KnowledgeSourceCard({ source }: { source: KnowledgeSource }) {
  const docs = useAsync<DocumentRecord[]>(() => api.listDocuments(source.id), [source.id]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const pending = docs.data?.some((d) => d.status === "pending" || d.status === "processing");
    if (!pending) return;
    const interval = setInterval(() => docs.reload(), 2500);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs.data]);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocument(source.id, file);
      docs.reload();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="rounded-lg border border-rule bg-surface p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="font-semibold text-sm">{source.name}</p>
        <label className="inline-flex items-center gap-2 rounded-md border border-rule px-3 py-1.5 text-xs font-semibold text-ink-soft hover:text-ink hover:bg-surface-raised cursor-pointer transition-colors">
          <IconUpload className="h-3.5 w-3.5" />
          {isUploading ? "Uploading…" : "Upload document"}
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.xlsx,.txt" className="hidden" onChange={handleFileChange} disabled={isUploading} />
        </label>
      </div>

      {uploadError && <p className="text-sm text-bad mb-2">{uploadError}</p>}
      {docs.error && <p className="text-sm text-bad mb-2">{docs.error}</p>}

      {!docs.data || docs.data.length === 0 ? (
        <p className="text-xs text-ink-soft">{docs.isLoading ? "Loading…" : "No documents uploaded yet."}</p>
      ) : (
        <div className="flex flex-col divide-y divide-rule">
          {docs.data.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between py-2 text-sm">
              <span className="font-mono text-xs text-ink-soft">{doc.source_type.toUpperCase()}</span>
              <div className="flex items-center gap-3">
                {doc.status === "failed" && doc.error && <span className="text-xs text-bad max-w-xs truncate">{doc.error}</span>}
                <StatusPill tone={documentStatusTone(doc.status)}>{doc.status}</StatusPill>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
