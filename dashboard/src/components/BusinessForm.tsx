"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "./Button";
import { Field, inputClass } from "./Field";
import type { Business } from "@/lib/types";

export function BusinessForm({ onCreated, onCancel }: { onCreated: (business: Business) => void; onCancel?: () => void }) {
  const [name, setName] = useState("");
  const [hours, setHours] = useState("");
  const [languages, setLanguages] = useState("hi, en");
  const [transferNumber, setTransferNumber] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const business = await api.createBusiness({
        name,
        structured_config: {
          hours: hours || undefined,
          languages: languages
            .split(",")
            .map((l) => l.trim())
            .filter(Boolean),
        },
        default_transfer_number: transferNumber || null,
      });
      onCreated(business);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the business.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-rule bg-surface p-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Business name" required>
          <input required value={name} onChange={(e) => setName(e.target.value)} className={inputClass} placeholder="Smile Dental" />
        </Field>
        <Field label="Transfer number">
          <input value={transferNumber} onChange={(e) => setTransferNumber(e.target.value)} className={inputClass} placeholder="+91 98765 43210" />
        </Field>
        <Field label="Hours">
          <input value={hours} onChange={(e) => setHours(e.target.value)} className={inputClass} placeholder="9am–6pm, Mon–Sat" />
        </Field>
        <Field label="Languages">
          <input value={languages} onChange={(e) => setLanguages(e.target.value)} className={inputClass} placeholder="hi, en" />
        </Field>
      </div>

      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      <div className="mt-5 flex items-center gap-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Save business"}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
