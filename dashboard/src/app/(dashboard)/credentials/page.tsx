"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Field, inputClass } from "@/components/Field";
import { IconKey, IconPlus } from "@/components/icons";
import type { Credential, ProviderType } from "@/lib/types";

interface FieldSpec {
  key: string;
  label: string;
  type?: string;
}

interface ProviderPreset {
  label: string;
  providerType: ProviderType;
  fields: FieldSpec[];
}

const PRESETS: Record<string, ProviderPreset> = {
  sarvam_stt: { label: "Sarvam (STT)", providerType: "stt", fields: [{ key: "api_key", label: "API key", type: "password" }] },
  sarvam_tts: { label: "Sarvam (TTS)", providerType: "tts", fields: [{ key: "api_key", label: "API key", type: "password" }] },
  gemini: { label: "Gemini (LLM)", providerType: "llm", fields: [{ key: "api_key", label: "API key", type: "password" }] },
  openai: {
    label: "OpenAI (LLM + embeddings)",
    providerType: "llm",
    fields: [{ key: "api_key", label: "API key", type: "password" }],
  },
  exotel: {
    label: "Exotel (telephony)",
    providerType: "telephony",
    fields: [
      { key: "sid", label: "Account SID" },
      { key: "token", label: "API token", type: "password" },
      { key: "subdomain", label: "Subdomain" },
    ],
  },
  plivo: {
    label: "Plivo (telephony)",
    providerType: "telephony",
    fields: [
      { key: "auth_id", label: "Auth ID" },
      { key: "auth_token", label: "Auth token", type: "password" },
    ],
  },
};

const PROVIDER_NAME_BY_PRESET: Record<string, string> = {
  sarvam_stt: "sarvam",
  sarvam_tts: "sarvam",
  gemini: "gemini",
  openai: "openai",
  exotel: "exotel",
  plivo: "plivo",
};

export default function CredentialsPage() {
  const credentials = useAsync<Credential[]>(() => api.listCredentials(), []);
  const [showForm, setShowForm] = useState(false);

  return (
    <div>
      <PageHeader
        kicker="BYOC / BYOK"
        title="Credentials"
        description="This tenant's own provider accounts — encrypted at rest, used to run their agents. Never resold or shared across tenants."
        actions={
          <Button onClick={() => setShowForm((v) => !v)}>
            <IconPlus className="h-4 w-4" />
            Add credential
          </Button>
        }
      />

      {showForm && (
        <NewCredentialForm
          onCreated={() => {
            setShowForm(false);
            credentials.reload();
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {credentials.isLoading && <p className="text-sm text-ink-soft">Loading…</p>}
      {credentials.error && <p className="text-sm text-bad">{credentials.error}</p>}

      {credentials.data && credentials.data.length === 0 && !showForm && (
        <EmptyState
          title="No credentials yet"
          description="Add this client's Sarvam, Exotel, and Gemini keys — publishing an agent needs them to reach a real phone line."
          action={
            <Button variant="secondary" onClick={() => setShowForm(true)}>
              <IconPlus className="h-4 w-4" />
              Add credential
            </Button>
          }
        />
      )}

      {credentials.data && credentials.data.length > 0 && (
        <div className="flex flex-col rounded-lg border border-rule bg-surface divide-y divide-rule overflow-hidden">
          {credentials.data.map((c) => (
            <div key={c.id} className="flex items-center justify-between px-5 py-3.5">
              <div className="flex items-center gap-3">
                <IconKey className="h-4 w-4 text-ink-soft" />
                <div>
                  <p className="text-sm font-semibold capitalize">{c.provider_name}</p>
                  <p className="text-xs text-ink-soft font-mono uppercase tracking-wide">{c.provider_type}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {c.is_default && <span className="text-xs text-wire font-mono uppercase tracking-wide">Default</span>}
                <Button
                  variant="danger"
                  onClick={async () => {
                    await api.deleteCredential(c.id);
                    credentials.reload();
                  }}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewCredentialForm({ onCreated, onCancel }: { onCreated: () => void; onCancel: () => void }) {
  const [presetKey, setPresetKey] = useState<keyof typeof PRESETS>("sarvam_stt");
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const preset = PRESETS[presetKey];

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await api.createCredential({
        provider_type: preset.providerType,
        provider_name: PROVIDER_NAME_BY_PRESET[presetKey],
        credentials: values,
        is_default: true,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the credential.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-8 rounded-lg border border-rule bg-surface p-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Provider" required>
          <select
            value={presetKey}
            onChange={(e) => {
              setPresetKey(e.target.value as keyof typeof PRESETS);
              setValues({});
            }}
            className={inputClass}
          >
            {Object.entries(PRESETS).map(([key, p]) => (
              <option key={key} value={key}>
                {p.label}
              </option>
            ))}
          </select>
        </Field>

        {preset.fields.map((field) => (
          <Field key={field.key} label={field.label} required>
            <input
              required
              type={field.type ?? "text"}
              value={values[field.key] ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
              className={inputClass}
            />
          </Field>
        ))}
      </div>

      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      <div className="mt-5 flex items-center gap-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Save credential"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
