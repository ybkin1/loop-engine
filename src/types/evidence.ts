export type EvidenceStatus = "submitted" | "verified" | "tampered" | "expired";

export interface EvidenceRecord {
  evidence_id: string;
  type: string;
  content: string;
  content_hash: string;
  submitted_at: string;
  submitted_by: string;
  gate_id: string | null;
  role_id: string | null;
  ttl_seconds: number | null;
  depends_on: string[];
  metadata: Record<string, unknown>;
}

export interface EvidenceSubmitParams {
  evidence_id: string;
  type: string;
  content: string;
  gate_id?: string;
  role_id?: string;
  ttl_seconds?: number;
  depends_on?: string[];
  metadata?: Record<string, unknown>;
}

export interface EvidenceSubmitResult {
  success: boolean;
  evidence_id: string;
  content_hash: string;
  stored_at: string;
  submitted_at: string;
}

export interface EvidenceVerifyResult {
  evidence_id: string;
  status: EvidenceStatus;
  content_hash: string;
  stored_hash: string;
  match: boolean;
  submitted_at: string;
  freshness: "fresh" | "stale" | "no_ttl" | "unknown";
}

export interface HandoffRecord {
  timestamp: string;
  from_role: string;
  to_role: string;
  artifacts: { path: string; hash: string; version: string }[];
  context_summary: string;
  unresolved_items: string[];
}

export interface HandoffResult {
  success: boolean;
  handoff_id: string;
  recorded_at: string;
  artifacts_count: number;
}
