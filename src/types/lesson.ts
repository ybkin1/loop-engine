/**
 * lesson.ts — Knowledge Sedimentation type definitions
 *
 * Defines the data model for capturing lessons learned from
 * RETURN_FOR_REWORK, QUALITY_CHECK FAILED, constraint violations,
 * and other failure paths in the Loop Engineering lifecycle.
 *
 * Each lesson is an append-only, chain-hashed record that feeds
 * back into the governance system to improve future decisions.
 */

// ── Lesson Category ──────────────────────────────────────────────────────────

/** Root-cause classification for a captured lesson. */
export enum LessonCategory {
  /** Code contains a logic error (wrong algorithm, incorrect condition, etc.) */
  LOGIC_ERROR = "LOGIC_ERROR",
  /** Architectural or design-level flaw (wrong abstraction, missing module, etc.) */
  DESIGN_FLAW = "DESIGN_FLAW",
  /** A bug that was not caught by existing tests or quality gates */
  UNDETECTED_BUG = "UNDETECTED_BUG",
  /** Hard constraint violated (C1-C8), indicating process non-compliance */
  CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION",
  /** Test gap — missing test coverage allowed the defect to slip through */
  TEST_GAP = "TEST_GAP",
  /** Security vulnerability or missing security control */
  SECURITY_GAP = "SECURITY_GAP",
  /** Process or workflow issue (wrong role order, missing handoff, etc.) */
  PROCESS_GAP = "PROCESS_GAP",
  /** Performance or resource issue */
  PERFORMANCE_ISSUE = "PERFORMANCE_ISSUE",
  /** Other — use when none of the above fit */
  OTHER = "OTHER",
}

// ── Lesson Status ────────────────────────────────────────────────────────────

/** Lifecycle status of a lesson. */
export enum LessonStatus {
  /** Newly captured, not yet analyzed */
  OPEN = "OPEN",
  /** Root cause confirmed, resolution in progress */
  ACKNOWLEDGED = "ACKNOWLEDGED",
  /** Fix applied and verified */
  RESOLVED = "RESOLVED",
  /** No longer applicable (code removed, process changed, etc.) */
  SUPERSEDED = "SUPERSEDED",
  /** Cannot reproduce or insufficient information */
  WONT_FIX = "WONT_FIX",
}

// ── Lesson Record ────────────────────────────────────────────────────────────

/**
 * A single entry in the knowledge ledger.
 *
 * Each record captures a failure event with enough context to enable
 * future pattern matching and automated diagnosis.
 */
export interface LessonRecord {
  /** Unique lesson identifier (e.g. "lesson-001") */
  lesson_id: string;

  /** Monotonically increasing sequence number (1-based) */
  seq: number;

  /** SHA-256 chain hash for tamper-evident integrity */
  chain_hash: string;

  /** Chain hash of the previous entry */
  prev_chain_hash: string;

  /** ISO-8601 timestamp of when the lesson was captured */
  timestamp: string;

  // ── Context: where did it happen ──

  /** Phase in which the failure occurred (e.g. "S4-implementation") */
  phase_id: string;

  /** Role that was executing when the failure occurred */
  role_id: string;

  /** Task ID if the failure is task-scoped */
  task_id?: string;

  /** Execution ID from ExecutionLedger, for cross-referencing */
  execution_id?: string;

  // ── Classification ──

  /** Root-cause category */
  category: LessonCategory;

  /** Severity level (reuses BLOCKER/WARNING from hard_constraints) */
  severity: "BLOCKER" | "WARNING";

  // ── Symptom ──

  /** Human-readable summary of what went wrong (1-2 sentences) */
  symptom: string;

  /** Raw error message or stack trace snippet */
  error_message: string;

  /** Related constraint IDs if this was a constraint violation */
  constraint_violations?: string[];

  // ── Resolution ──

  /** Current lifecycle status */
  status: LessonStatus;

  /** How the issue was resolved (filled when status=RESOLVED) */
  resolution?: string;

  /** ISO-8601 timestamp when resolved */
  resolved_at?: string;

  /** Phase in which the resolution was applied */
  resolved_in_phase?: string;

  // ── Longitudinal Validation (aligned with Better Harness) ──

  /**
   * Validation status of the fix over time.
   * - `pending_no_later_window`: fix applied, awaiting comparable later tasks
   * - `verified`: a comparable later task/outcome confirmed the fix works
   * - `regressed`: a later comparable task showed the issue recurred
   */
  validation_status?: "pending_no_later_window" | "verified" | "regressed";

  /** ISO-8601 timestamp when longitudinal validation was last updated. */
  validated_at?: string;

  /**
   * Reference to the comparable later task/execution that confirmed
   * (or disproved) the fix effectiveness.
   */
  validation_evidence_ref?: string;

  // ── Searchability ──

  /** Search tags (e.g. ["typescript", "null-check", "async-await"]) */
  tags: string[];

  /** IDs of related lessons for pattern discovery */
  related_lessons?: string[];
}

// ── Query Types ──────────────────────────────────────────────────────────────

/** Filter criteria for querying the knowledge ledger. */
export interface LessonQuery {
  /** Filter by phase (exact match) */
  phase_id?: string;

  /** Filter by role (exact match) */
  role_id?: string;

  /** Filter by category */
  category?: LessonCategory;

  /** Filter by status */
  status?: LessonStatus;

  /** Filter by severity */
  severity?: "BLOCKER" | "WARNING";

  /** Filter by tags (ANY match) */
  tags?: string[];

  /** Maximum number of results to return */
  limit?: number;

  /** Return entries after this timestamp */
  since?: string;
}

// ── Lesson Statistics ────────────────────────────────────────────────────────

/** Aggregate statistics for lessons by category. */
export interface LessonCategoryStats {
  category: LessonCategory;
  count: number;
  resolved: number;
  open: number;
}

/** Aggregate statistics for lessons by phase. */
export interface LessonPhaseStats {
  phase_id: string;
  count: number;
  blocker_count: number;
  warning_count: number;
}

/** Top-level statistics for the knowledge ledger. */
export interface LessonStatistics {
  total: number;
  open: number;
  resolved: number;
  by_category: LessonCategoryStats[];
  by_phase: LessonPhaseStats[];
}

// ── Integrity ────────────────────────────────────────────────────────────────

/** Result of verifying the knowledge ledger's chain-hash integrity. */
export interface LessonIntegrity {
  valid: boolean;
  firstInvalidSeq: number | null;
  totalEntries: number;
}
