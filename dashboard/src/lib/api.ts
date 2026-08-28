import type {
  Agent,
  AgentTemplate,
  AgentVersion,
  Business,
  Credential,
  DocumentRecord,
  KnowledgeSource,
  Policy,
  ProviderType,
  VerticalPack,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "vap_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; formData?: FormData } = {}
): Promise<T> {
  const { method = "GET", body, auth = true, formData } = options;
  const headers: Record<string, string> = {};

  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let payload: BodyInit | undefined;
  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}/api/v1${path}`, { method, headers, body: payload });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", { method: "POST", body: { email, password }, auth: false }),

  listBusinesses: () => request<Business[]>("/businesses"),
  getBusiness: (id: string) => request<Business>(`/businesses/${id}`),
  createBusiness: (body: { name: string; structured_config?: Record<string, unknown>; default_transfer_number?: string | null }) =>
    request<Business>("/businesses", { method: "POST", body }),

  listTemplates: () => request<AgentTemplate[]>("/templates"),
  listVerticalPacks: (templateId: string) => request<VerticalPack[]>(`/templates/${templateId}/vertical-packs`),

  listAgents: () => request<Agent[]>("/agents"),
  getAgent: (id: string) => request<Agent>(`/agents/${id}`),
  createAgent: (body: { business_id: string; template_id: string; vertical_pack_id?: string | null; name: string }) =>
    request<Agent>("/agents", { method: "POST", body }),

  listAgentVersions: (agentId: string) => request<AgentVersion[]>(`/agents/${agentId}/versions`),
  createAgentVersion: (agentId: string) => request<AgentVersion>(`/agents/${agentId}/versions`, { method: "POST" }),
  compileAgentVersion: (agentId: string, versionId: string) =>
    request<AgentVersion>(`/agents/${agentId}/versions/${versionId}/compile`, { method: "POST" }),
  publishAgentVersion: (agentId: string, versionId: string) =>
    request<AgentVersion>(`/agents/${agentId}/versions/${versionId}/publish`, { method: "POST" }),

  listPolicies: (agentId: string, versionId: string) =>
    request<Policy[]>(`/agents/${agentId}/versions/${versionId}/policies`),
  createPolicy: (agentId: string, versionId: string, body: { category: string; rule_text: string; escalation_target?: string | null }) =>
    request<Policy>(`/agents/${agentId}/versions/${versionId}/policies`, { method: "POST", body }),
  deletePolicy: (agentId: string, versionId: string, policyId: string) =>
    request<void>(`/agents/${agentId}/versions/${versionId}/policies/${policyId}`, { method: "DELETE" }),

  listKnowledgeSources: () => request<KnowledgeSource[]>("/knowledge-sources"),
  createKnowledgeSource: (body: { business_id: string; name: string }) =>
    request<KnowledgeSource>("/knowledge-sources", { method: "POST", body }),
  uploadDocument: (knowledgeSourceId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<DocumentRecord>(`/knowledge-sources/${knowledgeSourceId}/documents/upload`, {
      method: "POST",
      formData,
    });
  },
  addDocumentFromUrl: (knowledgeSourceId: string, url: string) =>
    request<DocumentRecord>(`/knowledge-sources/${knowledgeSourceId}/documents/url`, {
      method: "POST",
      body: { url },
    }),
  listDocuments: (knowledgeSourceId: string) =>
    request<DocumentRecord[]>(`/knowledge-sources/${knowledgeSourceId}/documents`),
  getDocument: (id: string) => request<DocumentRecord>(`/documents/${id}`),

  listCredentials: () => request<Credential[]>("/credentials"),
  createCredential: (body: { provider_type: ProviderType; provider_name: string; credentials: Record<string, unknown>; is_default?: boolean }) =>
    request<Credential>("/credentials", { method: "POST", body }),
  deleteCredential: (id: string) => request<void>(`/credentials/${id}`, { method: "DELETE" }),
};
