/**
 * TenderSense AI — Backend API Client
 * Replaces all mockData imports with real API calls.
 */
import { supabase } from "@/lib/supabase";

// FORCE Production URL for deployment stability
const API_BASE = "https://tendersense.onrender.com";

// ── Auth helpers ─────────────────────────────────────────────────────────────

async function getToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function authHeaders(): Promise<HeadersInit> {
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const headers = await authHeaders();
  const apiPath = path.startsWith("/api") ? path : `/api${path}`;
  
  const res = await fetch(`${API_BASE}${apiPath}`, {
    ...options,
    headers: {
      "Accept": "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...headers,
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: any) => apiFetch<T>(path, { 
    method: "POST", 
    body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined)
  }),
  put: <T>(path: string, body?: any) => apiFetch<T>(path, { 
    method: "PUT", 
    body: body instanceof FormData ? body : (body ? JSON.stringify(body) : undefined)
  }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

// ── Types ────────────────────────────────────────────────────────────────────

export interface Tender {
  id: string;
  tender_number: string;
  title: string;
  department: string;
  tender_type: string;
  estimated_value: number | null;
  submission_deadline: string;
  status: string;
  criteria: Record<string, unknown>;
  created_at: string;
}

export interface BidderEval {
  id: string;
  bidder_id: string;
  bidder_name: string;
  bidder_gstin: string;
  bid_amount: number | null;
  final_verdict: "eligible" | "not_eligible" | "needs_review";
  confidence_score: number;
  needs_human_review: boolean;
  review_reason: string;
  finance_verdict: AgentVerdict | null;
  tech_verdict: AgentVerdict | null;
  compliance_verdict: AgentVerdict | null;
  validation_verdict: AgentVerdict | null;
  fraud_verdict: AgentVerdict | null;
  explanation_chain: ExplanationChain | null;
  evaluated_at: string;
}

export interface AgentVerdict {
  status: string;
  confidence: number;
  criteria_results: CriterionResult[];
  agent_reasoning: string;
  execution_time_ms: number;
  red_flags?: string[];
  risk_score?: number;
  fraud_indicators?: FraudIndicator[];
}

export interface CriterionResult {
  criterion_id: string;
  result: string;
  extracted_value: string;
  required_value: string;
  evidence: string[];
  explanation: string;
}

export interface ExplanationChain {
  summary: string;
  criterion_analysis: CriterionResult[];
  risk_factors: string[];
  recommendation: string;
}

export interface FraudIndicator {
  type: string;
  severity: string;
  description: string;
  evidence: string[];
  score_contribution: number;
}

export interface AuditLog {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  user_email?: string;
  user_role?: string;
  old_value?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  llm_model?: string;
  llm_tokens_used?: number;
  created_at: string;
}

export interface DashboardAnalytics {
  tenders_processed: number;
  bidders_evaluated: number;
  eligible: number;
  not_eligible: number;
  needs_review: number;
  avg_confidence: number;
  active_tenders: number;
  recent_evaluations: BidderEval[];
}

export interface SSEUpdate {
  type: string;
  agent?: string;
  message?: string;
  status?: string;
  confidence?: number;
  verdict?: string;
  evaluation_id?: string;
  needs_review?: boolean;
  total_bidders?: number;
  current?: number;
  bidder_name?: string;
  bidder_id?: string;
}

// ── Tender APIs ──────────────────────────────────────────────────────────────

export async function uploadTender(formData: FormData): Promise<{ tender_id: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE}/api/tenders/upload`, {
    method: "POST",
    headers: { ...headers },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
}

export async function listTenders(params?: {
  status?: string;
  department?: string;
  skip?: number;
  limit?: number;
}): Promise<{ tenders: Tender[]; total: number }> {
  const qs = new URLSearchParams(
    Object.entries(params ?? {}).filter(([, v]) => v !== undefined) as [string, string][]
  ).toString();
  return apiFetch(`/api/tenders${qs ? `?${qs}` : ""}`);
}

export async function getTender(tenderId: string): Promise<Tender> {
  return apiFetch(`/api/tenders/${tenderId}`);
}

export async function uploadBidder(tenderId: string, formData: FormData): Promise<{ bidder_id: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE}/api/tenders/${tenderId}/bidders/upload`, {
    method: "POST",
    headers: { ...headers },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
}

// ── Evaluation APIs ──────────────────────────────────────────────────────────

export function streamEvaluation(
  tenderId: string,
  onUpdate: (update: SSEUpdate) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): () => void {
  const controller = new AbortController();

  const startStream = async () => {
    const token = await getToken();
    const url = `${API_BASE}/api/evaluations/${tenderId}/start`;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`Evaluation failed: ${res.statusText}`);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const update = JSON.parse(line.slice(6)) as SSEUpdate;
              onUpdate(update);
              if (update.type === "complete") onDone();
            } catch {
              // ignore malformed SSE line
            }
          }
        }
      }
      onDone();
    } catch (err: any) {
      if (err.name !== "AbortError") onError(err);
    }
  };

  startStream();

  return () => controller.abort();
}

export async function getEvaluationResults(
  tenderId: string,
  verdictFilter?: string,
): Promise<{
  tender_id: string;
  total_bidders: number;
  eligible: number;
  not_eligible: number;
  needs_review: number;
  results: BidderEval[];
}> {
  const qs = verdictFilter ? `?verdict_filter=${verdictFilter}` : "";
  return apiFetch(`/api/evaluations/${tenderId}/results${qs}`);
}

export async function getExplanationChain(evaluationId: string): Promise<Record<string, unknown>> {
  return apiFetch(`/api/evaluations/explanation/${evaluationId}`);
}

// ── Review APIs ──────────────────────────────────────────────────────────────

export async function getReviewQueue(): Promise<{
  queue: (BidderEval & { tender_title: string; department: string })[];
  total: number;
}> {
  return apiFetch("/api/review/queue");
}

export async function submitReview(
  evaluationId: string,
  verdict: "eligible" | "not_eligible",
  notes: string,
): Promise<{ success: boolean }> {
  return apiFetch(`/api/review/${evaluationId}/submit`, {
    method: "POST",
    body: JSON.stringify({ verdict, notes }),
  });
}

// ── Audit APIs ───────────────────────────────────────────────────────────────

export async function getAuditLogs(params?: {
  entity_type?: string;
  entity_id?: string;
  limit?: number;
  skip?: number;
}): Promise<{ logs: AuditLog[]; total: number }> {
  const qs = new URLSearchParams(
    Object.entries(params ?? {}).filter(([, v]) => v !== undefined) as [string, string][]
  ).toString();
  return apiFetch(`/api/audit${qs ? `?${qs}` : ""}`);
}

// ── Analytics APIs ───────────────────────────────────────────────────────────

export async function getDashboardAnalytics(): Promise<DashboardAnalytics> {
  return apiFetch("/api/analytics/dashboard");
}

// ── Reports ──────────────────────────────────────────────────────────────────

export async function downloadPdfReport(tenderId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE}/api/reports/${tenderId}/pdf`, {
    headers: { ...headers },
  });
  if (!res.ok) throw new Error("PDF generation failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `TenderSense_${tenderId}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Health ───────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<Record<string, unknown>> {
  return apiFetch("/health");
}
