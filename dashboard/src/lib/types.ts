export type AgentVersionStatus = "draft" | "published" | "archived";
export type DocumentStatus = "pending" | "processing" | "ready" | "failed";
export type ProviderType = "telephony" | "stt" | "llm" | "tts";

export interface Business {
  id: string;
  name: string;
  structured_config: Record<string, unknown>;
  default_transfer_number: string | null;
}

export interface AgentTemplate {
  id: string;
  slug: string;
  name: string;
}

export interface VerticalPack {
  id: string;
  template_id: string;
  slug: string;
  name: string;
}

export interface Agent {
  id: string;
  business_id: string;
  template_id: string;
  vertical_pack_id: string | null;
  name: string;
}

export interface AgentVersion {
  id: string;
  agent_id: string;
  version_number: number;
  status: AgentVersionStatus;
  compiled_spec: Record<string, unknown>;
  voice_config: Record<string, unknown>;
  dograh_workflow_id: string | null;
}

export interface Policy {
  id: string;
  agent_version_id: string;
  category: string;
  rule_text: string;
  escalation_target: string | null;
}

export interface KnowledgeSource {
  id: string;
  business_id: string;
  name: string;
}

export interface DocumentRecord {
  id: string;
  knowledge_source_id: string;
  source_type: string;
  status: DocumentStatus;
  error: string | null;
}

export interface Credential {
  id: string;
  provider_type: ProviderType;
  provider_name: string;
  is_default: boolean;
}

export interface CompiledSpec {
  prompt: string;
  business: {
    name: string;
    structured_config: Record<string, unknown>;
    default_transfer_number: string | null;
  };
  policies: { category: string; rule_text: string; escalation_target?: string | null }[];
  tools: { name: string; type: string; config: Record<string, unknown> }[];
  knowledge_source_ids: string[];
  voice_config: Record<string, unknown>;
  provider_stack: Record<string, unknown>;
}
