export type { ProjectState, PhaseRecord, StateStore, PhaseId, LegacyPhaseId, PhaseStatus, ProjectStatus, LoopMode, UserApproval } from "./state.js";
export type { GateStatus, GateCondition, GateDefinition, GatesRegistry, GateCheckResult, GateAdvanceResult } from "./gate.js";
export type { RoleStatus, RoleSpec, RoleActivation, RoleActivateResult, RoleStatusResult, RoleContract, RoleIdentity } from "./role.js";
export type { EvidenceStatus, EvidenceRecord, EvidenceSubmitParams, EvidenceSubmitResult, EvidenceVerifyResult, HandoffRecord, HandoffResult } from "./evidence.js";
export type { SubagentStatus, SubagentSpec, SubagentManifest, SubagentResult, ManifestExecutionResult } from "./subagent.js";
export { LessonCategory, LessonStatus } from "./lesson.js";
export type { LessonRecord, LessonQuery, LessonCategoryStats, LessonPhaseStats, LessonStatistics, LessonIntegrity } from "./lesson.js";
