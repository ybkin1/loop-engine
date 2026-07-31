# Delivery Governance: Real-World Frameworks and Process Quality

**Research task:** T-0083 — how real organizations govern the end-to-end delivery of software projects: formal frameworks, stage gates, oversight mechanisms, evidence requirements, human accountability, and failure/recovery governance.

**Date:** 2026-07-31
**Researcher:** ZCode research agent (T-0083)

---

## 0. How This Research Was Conducted

- Primary sources fetched and read directly: **CMMI Institute** (maturity/capability levels, cmmiinstitute.com/learning/appraisals/levels), **The 2020 Scrum Guide** (scrumguides.org/scrum-guide.html), **NIST SP 800-218 Secure Software Development Framework (SSDF)** publication page (csrc.nist.gov/pubs/sp/800/218/final), **Atlassian Scrum guide** (atlassian.com/agile/scrum), **IBM change management topic** (ibm.com/topics/change-management), **Steven Sinofsky's Hardcore Software blog** (hardcoresoftware.learningbyshipping.com).
- Network access was partially restricted during research (Wikipedia, PMI, ISO.org, SAFe framework site, Axelos, planview.com, sre.google all returned timeouts, 403 bot-blocks, or JS-only shells). Where a primary site could not be fetched, content is drawn from well-established, widely documented public knowledge of these frameworks (PMBOK, ISO/IEC/IEEE 12207, SAFe, ITIL 4, Cooper's Stage-Gate, Google SRE, Microsoft shiproom, Amazon processes), and canonical citation URLs are provided so a reader can verify.
- Everything below is standard, publicly documented practice, not speculation. Named-company examples are from published material (books, engineering blogs, SEC/regulatory reports, SRE books).

---

## 1. Formal Delivery Lifecycle Frameworks

### 1.1 Waterfall and the V-Model

**What it is.** The classical sequential lifecycle (Royce, 1970): Requirements → Design → Implementation → Testing → Deployment → Maintenance, with each phase completed and formally approved before the next begins. The **V-Model** (German/Aerospace origin, standardized in IEEE 1044-era practice and DoD acquisition) pairs each development phase with a corresponding verification/validation phase on the other side of the "V": requirements ↔ acceptance testing, design ↔ integration testing, detailed design ↔ unit testing, code at the vertex.

**Who operates it / when.** Project managers and phase leads execute; a **phase-exit review board** (often called a Phase Review, Tollgate, or Milestone Review) approves each phase transition. Runs at the end of every phase.

**Evidence/gates required.** Completed phase deliverables (SRS, design documents, code, test reports), phase-exit criteria checklist, formal sign-off from each stakeholder, updated risk register and schedule, configuration baseline of the phase output (e.g., "Requirements Baseline", "Design Baseline", "Product Baseline" — IEEE 828 configuration management).

**What it prevents.** Uncontrolled phase overlap, downstream work on unapproved inputs, undocumented scope creep, "design by accident" — the requirement that a phase be *accepted* before the next phase starts is the mechanism.

**Real-world examples.** US DoD acquisition (Milestone A/B/C reviews per DoDI 5000.02), NASA (Phase A/B/C/D with formal reviews — see §2), regulated medical device and avionics development where the FDA (21 CFR 820 / IEC 62304) and FAA (DO-178C) effectively mandate documented phase discipline.

**Weaknesses (why governance exists around it).** Late feedback (defects found at the end are expensive), requirements frozen too early, and the gate review can become a rubber stamp. The V-model's verification pairing is the ancestor of "quality at every stage" thinking.

### 1.2 Agile / Scrum

**What it is.** Scrum (2020 Guide, Schwaber & Sutherland) is "a lightweight framework that helps people, teams and organizations generate value through adaptive solutions for complex problems," built on **empiricism** (transparency, inspection, adaptation) and lean thinking.

**Roles:** Product Owner (orders the Product Backlog, is the single accountable voice for value), Scrum Master (fosters the environment, coaches process), Developers (self-managing, produce the Increment). One accountable Product Owner — a *human accountability* structure (§5).

**Events:** Sprint (time-boxed, typically 2–4 weeks) containing Sprint Planning (select work, define Sprint Goal), Daily Scrum, Sprint Review (inspect increment with stakeholders; adapt backlog), Sprint Retrospective (inspect process; plan improvements).

**Artifacts:** Product Backlog (ordered, emergent), Sprint Backlog, Increment. Each artifact has a commitment: Product Goal, Sprint Goal, **Definition of Done** — the team's explicit quality bar that an Increment must meet to be considered "Done."

**Evidence/gates.** Sprint Review is the recurring stakeholder gate ("done vs. not done" demonstrated against the DoD, not asserted); velocity and burn-down charts give measured evidence of delivery rate; the Retrospective produces improvement actions. "Definition of Ready" (a team-level precondition before a story enters a sprint) is a widely used informal gate.

**What it prevents.** Big-bang integration risk, requirement guesswork, invisible progress. Its weakness as *delivery* governance: Scrum alone governs team-level work, not release-to-customer or portfolio-level decisions — which is why enterprises overlay SAFe or stage gates (§1.3, §2).

### 1.3 SAFe (Scaled Agile Framework)

**What it is.** SAFe is the most widely adopted framework for scaling agile across an enterprise. Its core governance unit is the **ART — Agile Release Train** (5–12 agile teams, roughly 50–125 people, organized around a value stream) running on a **Program Increment (PI)** — a fixed timebox, typically 8–12 weeks, at which the train's **Program Backlog** is planned and delivered.

**Who operates it / when.**
- **PI Planning** — a 2-day, face-to-face (or distributed) event at the start of each PI where all teams, stakeholders, and Business Owners align on the PI Objectives (a short set of business/technical goals with business-value scoring).
- **Release Train Engineer (RTE)** — the servant-leader and process owner of the train.
- **System Demo** — at the end of each iteration, an integrated system demo; at PI end, the **Solution Demo** to stakeholders.
- **Inspect & Adapt (I&A)** — the PI-ending workshop (with a structured problem-solving exercise) that produces improvement backlog items — SAFe's built-in continuous-improvement gate.
- **Release** — governed by the Continuous Delivery Pipeline's **Release on Demand** activity; a **release decision (GO/NO-GO)** is made by business owners/Product Management, typically in a **release train or release governance meeting**, based on the system's actual state (SLOs, feature flags, rollout strategy).
- Portfolio layer: **Lean Portfolio Management** with Strategic Themes, Portfolio Kanban, and Epic-level **WSJF** prioritization — epics pass through a lightweight approval (portfolio epic review) before funding.

**Evidence/gates.** PI Objectives with business-value scoring; program predictability measure (actual vs. planned business value); system demo evidence; I&A improvement items tracked to closure; epic business cases (Lean Business Case) for funding; release go/no-go with rollback/feature-flag evidence.

**What it prevents.** Uncoordinated team-level agile in a large organization: dependency chaos, misaligned priorities, unmanaged funding, and "we shipped, but nobody agreed what to ship." SAFe is often combined with traditional gates for regulated contexts (see §2.5 on Agile-Stage-Gate hybrids).

### 1.4 CMMI (Capability Maturity Model Integration)

**What it is.** A process-improvement framework by the CMMI Institute (ISACA). It characterizes an organization's process capability on a 1–5 **maturity scale** (staged path) plus per-practice-area **capability levels** (0–3). Fetched directly from cmmiinstitute.com:

| Maturity Level | Name | What it requires (verbatim summaries) |
|---|---|---|
| 1 | Initial | **Unpredictable and reactive.** Work gets completed but is often delayed and over budget. |
| 2 | Managed | **Managed on the project level.** Projects are planned, performed, measured, and controlled. |
| 3 | Defined | **Proactive, rather than reactive.** Organization-wide standards provide guidance across projects, programs, and portfolios. |
| 4 | Quantitatively Managed | **Measured and controlled.** Data-driven; quantitative performance-improvement objectives that are predictable and aligned to stakeholder needs. |
| 5 | Optimizing | **Stable and flexible.** Continuous improvement; built to pivot and respond to opportunity and change. |

Capability levels (per practice area): 0 Incomplete (inconsistent performance) → 1 Initial (addresses performance issues) → 2 Managed (complete set of practices; monitors project performance objectives) → 3 Defined (uses organizational standards; contributes to organizational assets).

**Who operates it / when.** Maturity levels are earned through formal **appraisals** by certified lead appraisers (SCAMPI method) against predefined practice-area sets; organizations typically run improvement programs spanning 12–36 months per level. Re-appraisal is periodic.

**Evidence/gates.** Appraisal findings are based on objective evidence: documented processes, **organizational assets** (process definitions, training materials, measurements), project records showing the process was actually used, and interviews. A level claim without demonstrable institutionalized use fails appraisal.

**What it prevents.** Heroic but non-repeatable delivery (Level 1), and "documented but not practiced" processes — Level 3+ explicitly requires org-wide standards and tailoring, Level 4 requires statistical process control, Level 5 requires defect/root-cause data driving change.

**Real-world examples.** Lockheed Martin, Boeing, Tata Consultancy Services, Capgemini, many defense/regulated suppliers use CMMI maturity as a procurement qualification (DoD historically required CMMI ML3 for certain contracts); government acquirers use it as a supplier gate.

### 1.5 ISO/IEC/IEEE 12207 (Software Life Cycle Processes)

**What it is.** The international standard for software life cycle processes (current: ISO/IEC/IEEE 12207:2017, harmonized with ISO/IEC/IEEE 15288 for systems). It defines a set of **processes** rather than a phase sequence, grouped into four process groups:
- **Agreement processes:** Acquisition, Supply.
- **Organizational project-enabling processes:** Life cycle model management, Infrastructure, Portfolio, Human resource, Quality.
- **Technical management processes:** Project planning, Project assessment and control, Decision management, Risk management, Configuration management, Information management, Measurement, Quality assurance.
- **Technical processes:** Business or mission analysis, Stakeholder needs & requirements definition, System/Software requirements definition, Architecture definition, Design definition, Implementation, Integration, Verification, Transition, Validation, Operation, Maintenance, Disposal.

Supporting processes include **Verification, Validation, Joint Review, Audit, Problem Resolution**, and **Documentation** — i.e., the standard explicitly creates review, audit, and traceability obligations.

**Who operates it / when.** Adopted by organizations as their process framework; **joint reviews** (technical and management reviews) are held at defined points; **audits** are performed to verify conformance to requirements, plans, and contracts.

**Evidence/gates.** Records of reviews and audits, configuration baselines, verification/validation results, problem reports and resolutions, traceability between requirements and artifacts. 12207 is *process* governance, not maturity governance (that's CMMI); it is frequently used as the compliance backbone in ISO 9001/IEC 62304-style quality systems.

**What it prevents.** Ad-hoc development with no defined process, no review obligation, no audit trail. (ISO's site was unreachable during research; this summary reflects the standard's publicly documented structure.)

### 1.6 PMBOK / PMI (Project Management Body of Knowledge)

**What it is.** PMI's PMBOK Guide is the de-facto global standard for project management. The 6th edition organizes practice into **5 Process Groups** — Initiating, Planning, Executing, Monitoring & Controlling, Closing — and **10 Knowledge Areas** — Integration, Scope, Schedule, Cost, Quality, Resources, Communications, Risk, Procurement, Stakeholder — containing 49 processes. The 7th edition (2021) reframes around 12 principles and 8 **performance domains** (Stakeholders, Team, Development Approach & Life Cycle, Planning, Project Work, Delivery, Measurement, Uncertainty). Both editions share the same core governance mechanics.

**Governance-relevant mechanics:**
- **Project Charter** — the initiating gate: the sponsor authorizes the project and appoints the project manager; nothing proceeds without it.
- **Phase-gate / phase reviews** — PMBOK explicitly supports phased life cycles where each phase ends with a **phase-exit review** assessing deliverables against **phase exit criteria** and deciding whether to proceed, iterate, or kill (gatekeepers are usually the sponsor/steering committee).
- **Monitoring & Controlling** — earned value management (EVM: SPI/CPI), variance analysis, change control (the **Change Control Board / CCB** and the *integrated change control* process — every change to baseline scope/schedule/cost goes through evaluation and approval), quality assurance vs. quality control (QC = verify deliverables; QA = audit the process).
- **Closing** — formal acceptance sign-off, **lessons learned**, archival of project records.
- **RACI** and stakeholder register/engagement plan; **risk register** with owners; **issue log**; **decision log**.
- **Portfolio/Program layer** — PMI's Portfolio Management standard: portfolio governance boards select, prioritize, and terminate projects against strategic criteria.

**Evidence/gates.** Charter (with sponsor signature), baselines, change requests + CCB minutes, EVM reports, quality metrics, acceptance criteria evidence, closing report, lessons learned. 

**What it prevents.** Unauthorized projects, uncontrolled scope ("scope creep"), unapproved changes, missing accountability for deliverables, projects that die without learning.

### 1.7 ITIL (ITIL 4 — Service Management & Change Control)

**What it is.** ITIL 4 (Axelos) is the leading ITSM framework; its **Service Value System** and **practices** (management practices replacing ITIL v3 processes) govern the *operation* of delivered software and the *changes* made to production.

**Change Enablement practice** (the heart of delivery governance in IT operations):
- Purpose: *maximize the number of successful IT changes by ensuring risks are assessed, changes are authorized, and change management is planned.*
- **Change types:** **Standard** (pre-authorized, low risk, repeatable — e.g., routine patching per a pre-approved change model), **Normal** (risk-assessed and authorized case by case), **Emergency** (urgent — expedited via an emergency change authority, typically a rapid emergency CAB).
- **Change authority:** a person or group authorized to approve a change type — commonly the **Change Advisory Board (CAB)**, an emergency CAB, or the change manager for standard changes. The **Change Calendar** gives visibility of all planned changes.
- **Change model:** predefined steps (initiation, categorization, risk/impact assessment, authorization, implementation, review) for each change type.
- Classic **"Seven Rs" of change management** (from ITIL v3, still taught): *Who* raised the change? *What* is the *Reason*? *What* *Return* is required? *What* are the *Risks*? *What* *Resources* are required? *Who* is *Responsible* for build/test/implement? *What* is the *Relationship* between this change and other changes?

**Related practices:** Incident management (restore service), Problem management (root cause + known errors), **Deployment management** and **Release management** (move releases into production in a controlled way), **Continual Improvement** (the improvement register; CSI in v3), Service Level Management (SLOs/SLAs), Monitoring & Event Management (early warning).

**Evidence/gates.** RFC (Request for Change) records with impact/risk assessment and named approver; CAB minutes; change calendar; **post-implementation review** (PIR) verifying the change achieved its objectives without adverse effect; failed changes feed problem management and continual improvement.

**What it prevents.** Uncontrolled production changes (the #1 cause of outages per IT industry postmortems), unauthorized change, conflicting concurrent changes, and changes that break service without detection.

---

## 2. Stage Gates and Phase Reviews (the heart of delivery governance)

### 2.1 Cooper's Stage-Gate (new-product/software process)

**What it is.** Robert G. Cooper's Stage-Gate™ (1980s, refined since; the origin of the generic term "stage gate") is the canonical **ideation-to-launch** governance process:

| Stage | Purpose | Gate (exit decision) |
|---|---|---|
| **Discovery / Ideation** | Generate ideas | **Gate 1: Idea screen** — is it worth pursuing at all? |
| **Scoping** | Quick, inexpensive assessment | **Gate 2: Second screen** — rough business/technical screen |
| **Build Business Case** | Detailed market/technical/financial analysis, project definition | **Gate 3: Go to Development** — business case approved, project funded |
| **Development** | Build the product/software | **Gate 4: Go to Testing** — development complete against specs |
| **Testing & Validation** | Verify the product works with real users, in real conditions | **Gate 5: Go to Launch** — test results satisfactory, launch plan ready |
| **Launch** | Commercialize / release | **Gate 6: Post-launch review** — did it deliver the business case? |

**Gate mechanics (the load-bearing part):**
1. **Deliverables** — the gate *cannot* be passed without the required artifacts (business case, prototype, test results, launch plan).
2. **Criteria** — a standardized scorecard (must-meet / should-meet criteria; e.g., strategic fit, product advantage, market attractiveness, technical feasibility, financial return) scored before the meeting.
3. **Outputs** — a decision: **Go / Kill / Hold / Recycle** (rework and return), plus an approved action plan and resources for the next stage.
4. **Gatekeepers** — senior management (the "gatekeepers" or a cross-functional review board), not the project team. Cooper's research (PDMA/APQC benchmarking) consistently shows strong gate discipline correlates with better new-product performance; weak gates (rubber-stamping, "must-go" politics) are the most common failure mode.

**Agile-Stage-Gate hybrid (Cooper & Sommer, 2016):** agile sprints inside each stage, with the stage gates retained for funding and portfolio decisions — the standard pattern in enterprises that want both agility and governance.

### 2.2 Gate models in government, aerospace, and defense

- **US DoD (DoDI 5000.02 Adaptive Acquisition Framework):** **Milestone A** (authorize technology maturation & risk reduction), **Milestone B** (authorize engineering & manufacturing development — the point of no return for design), **Milestone C** (authorize production & deployment). Each milestone requires documented evidence: capability documents, cost estimates (with independent cost estimates by the Cost Assessment and Program Evaluation office), test plans, and (before full-rate production) **Operational Test & Evaluation (OT&E)** by an independent tester. **Earned Value Management (EVM, ANSI/EIA-748)** is contractually required on development contracts — schedule/cost performance measured, not asserted.
- **NASA (NPR 7123.1 Systems Engineering):** formal technical reviews as gates: **SRR** (System Requirements Review) → **PDR** (Preliminary Design Review) → **CDR** (Critical Design Review) → **SIR/TRR** (System/Test Readiness Review) → **FRR** (Flight Readiness Review, pre-launch) → **PLAR** (Post-Launch Assessment Review). Independent Review Teams (IRTs) and the Flight Readiness Board (FRB) provide independent assessment — a governance layer outside the project.
- **Google/tech equivalent:** launch reviews with cross-functional approvers (§3.6).

### 2.3 Phase exit criteria — what must be demonstrated at each gate

Across all models, gate criteria cluster into the same families:

1. **Scope/completeness:** all planned deliverables of the phase exist and are versioned (e.g., 100% of requirements traced to design or explicitly deferred with approval).
2. **Quality:** test results meet pre-agreed thresholds (pass rate, coverage, defect counts within limits, zero open "must-fix"/blocker defects).
3. **Risk:** residual risks identified, owned, and accepted by a named accountable person; risk register updated.
4. **Readiness:** plans for the next phase exist and are resourced; entry criteria for the next phase met.
5. **Business case still holds:** cost/schedule/value estimates re-baselined and still acceptable (the "kill" trigger).
6. **Compliance:** required reviews (security, legal, architecture, privacy) completed; regulatory/audit evidence assembled.

The gate decision is *binary at the boundary*: the phase is either exited with approval or the project is held/recycled — there is no "mostly done."

### 2.4 Who approves each gate

- **Gate 1–2 (idea/screen):** product management + portfolio/innovation board; often lightweight, single accountable approver.
- **Gate 3 (business case/funding):** **steering committee / investment board / PMO portfolio board** — money is the classic authority trigger.
- **Gate 4–5 (development/testing):** **project steering committee** with the **sponsor** as final authority, supported by functional reviewers (architecture review board for design, security review board for security sign-off, QA for test evidence).
- **Gate 6 (launch/release):** **release management board / shiproom / launch review** (see §3.6) — cross-functional with operational sign-off (capacity, support readiness, legal, PR).
- **Ongoing (production changes):** CAB / change manager (ITIL, §1.7).

In every model the pattern is the same: *the people who pay and the people who are accountable to customers/regulators approve; the people who build present evidence.*

### 2.5 Gate review artifacts (what evidence is required)

Typical gate dossier (each artifact must be *current, owned, and signed*):
- Requirements baseline + traceability matrix (requirements ↔ design ↔ test cases ↔ release notes)
- Design documents approved by ARB (ADR/design review minutes)
- Code review/static analysis reports; SAST/DAST/pen-test reports with resolution of findings
- Test summary report (unit/integration/UAT/performance/security) with pass criteria evidence
- Defect list with severity, status, and disposition of open defects (accepted/deferred with named approver)
- Risk register + risk acceptance forms
- Financial/plan variance report (EVM if applicable)
- Deployment/rollback plan, runbook, support-readiness checklist
- Compliance records (licensing, accessibility, privacy, legal review)
- Gate meeting minutes with decision and named signatories

---

## 3. Governance Structures

### 3.1 Project Steering Committee / Governance Board

- **What:** a senior cross-functional body (sponsor, business owner, PM, functional heads) that owns project-level decisions the project manager cannot make: funding changes, scope trade-offs, milestone approvals, issue escalation, and kill decisions.
- **When:** on a fixed cadence (monthly/quarterly) plus ad hoc for gate reviews and escalations.
- **Prevents:** the project drifting from business value, unilateral scope changes, conflicts that stall delivery, and "zombie" projects that should be killed.
- **Example:** PMBOK's sponsor/steering model; corporate "portfolio steering committees" in banks and insurers sign off every project > $X threshold.

### 3.2 PMO (Project Management Office)

- **What:** the permanent organizational unit that standardizes processes, owns templates/gates, maintains the portfolio, allocates project managers, and *reports truth to management* (independent of project teams). Portfolio governance (project selection, prioritization, termination) is the PMO's most powerful governance act.
- **Prevents:** each project inventing its own process, hidden project status (the PMO's status reporting is the anti-surprise mechanism), and resource over-commitment.
- **Example:** enterprise PMOs in virtually all large companies; government program offices (e.g., DHS/DoD program executive offices).

### 3.3 Change Advisory Board (CAB) — ITIL

- **What:** a group of stakeholders (change manager, technical leads, service owners, business reps) that assesses and authorizes normal/emergency changes; the **emergency CAB** (fast subset + decision-maker) handles urgent changes outside normal windows.
- **Prevents:** production changes without risk assessment, conflicting changes, and change-induced incidents (ITIL research/industry data consistently show most major outages trace to change).
- **Example:** every ITIL-implementing enterprise; e.g., banks require CAB approval for production changes with impact/risk matrix and mandatory rollback plan.

### 3.4 Architecture Review Board (ARB)

- **What:** senior architects who review designs and technology choices against architecture principles, standards, and total-cost-of-ownership; owns architecture decision records (ADRs) and exceptions.
- **Prevents:** technology sprawl, un-maintainable designs, security-hostile architectures, "accidental architecture" accumulating debt that later blocks delivery.
- **Example:** Microsoft's architecture review for Windows/Office era; most large tech orgs (Spotify's "Guild"/System Owner model, Netflix's architecture reviews for major changes).

### 3.5 Security Review Board / Pen-Test Sign-Off

- **What:** the security function's gate: threat modeling (Microsoft SDL), secure code review, **penetration testing before release**, vulnerability triage with severity-based dispositions, and an explicit **security sign-off** (often a named security lead whose "NO" blocks release). Microsoft's SDL makes security a *mandatory, non-negotiable* release requirement (Final Security Review / pre-release review).
- **Prevents:** shipping known exploitable vulnerabilities; the Equifax-class failure (unpatched known CVE) is precisely what release gates exist to catch.
- **Example:** Microsoft SDL (docs: microsoft.com/sdl), Google's security launch review (a hard approver in the launch process), OWASP ASVS as the testing standard.

### 3.6 Release Management Board / "Shiproom" (Microsoft) / Launch Review (Google)

- **Microsoft "shiproom":** the legendary weekly (or at-release) meeting of engineering leadership (division/feature-area leads; in the Windows/Office era, the engineering VPs and the "shiproom" — named after the physical/room-based meeting) where each feature's readiness is reviewed and **GO/NO-GO** is given for inclusion in the release. Features must present: bug counts and triage status, quality-bar metrics, test results, "must-fix" list emptied, and performance/compat evidence. Senior leaders can *personally* hold a feature or the release. Documented in detail by Steven Sinofsky (President, Windows division) in his Hardcore Software blog series and in "One Dev" (Pascal Zachary). Modern Microsoft (Azure, DevOps) evolved this into data-driven release trains, **flight rings** (staged rollout: Canary → Insider → Production rings), pipeline **release gates** (Azure Pipelines gates: e.g., health metrics, security scans), and **Go/No-Go meetings** with dashboards.
- **Google launch process:** every user-visible launch requires a **launch review** coordinated by a **Launch Coordination Engineer (LCE)** — a dedicated, trained role (SRE Workbook, chapter "Launch Coordination Engineering"). A launch checklist (design docs, code review, testing, capacity planning, security/privacy/legal sign-off, rollout plan, rollback plan, monitoring) must be completed and approved by cross-functional approvers before a launch is authorized; launches are **staged** (1% → 10% → … → 100% via experiments/flags) with automated canary analysis and automatic rollback triggers. Google SRE also institutionalizes **error budgets** — the *right to release* is bounded by the product's SLO.
- **Amazon:** AWS teams own deployments end-to-end (two-pizza teams, single-threaded owners); releases use **automated deployment pipelines with canary analysis** (rolling waves with health checks; "rollback is automatic and instant"); major launches require an **internal launch readiness review (LIR)** and a "**correction of errors (COE)**" culture for any incident (§6.3). Amazon's *Leadership Principles* (e.g., "Have Backbone; Disagree and Commit") and "two-way door" decision doctrine (§5.5) govern the *decision* layer.

**What the release board prevents:** shipping features that "are not done but are scheduled," release-date-driven quality collapse, and single-team unilateral releases without operations/support readiness.

---

## 4. Evidence and Audit Requirements

### 4.1 What evidence real projects maintain

- **Decision log** — every significant decision (scope, design, deferral, risk acceptance) with date, decider, rationale, alternatives considered.
- **Change log / change requests** — RFCs with risk assessment, approver, implementation and post-implementation review records (ITIL).
- **Test evidence** — test cases linked to requirements, executed results, coverage reports, environment/version stamps, tool-generated reports (not self-declarations).
- **Sign-off records** — gate minutes, approval forms, named signatories (who approved what, when).
- **Configuration/version baselines** — what exactly was built, tested, and released (SBOMs, build provenance, commit hashes — see SLSA below).
- **Risk register and issue log** with owners and status.
- **Audit trail** — who did what, when, with what authority (access logs, change history, e-signatures).
- **Postmortems / lessons learned** (§6.3).

### 4.2 Traceability (requirements → design → code → test → release)

- **Bidirectional traceability** is a hard requirement in safety-critical domains: **DO-178C** (avionics) requires each high-level/low-level requirement traced to design, code, and tests with **structural coverage analysis**; **ISO 26262** (automotive safety) requires the same for each ASIL; **IEC 62304** (medical software) requires traceability of software requirements to tests and risk-control measures; **FDA design controls** (21 CFR 820.30) require traceability in the Design History File.
- Tools: requirements management systems (Jama, DOORS, Polarion), ALM suites (Azure DevOps, Jira+plugins, codebeamer), each enforcing link types and completeness reports.
- **What it prevents:** untested requirements, orphaned code, "we tested everything" claims that cannot be demonstrated, and release contents nobody can reconstruct.

### 4.3 Audits (internal and external)

- **Internal audit:** an independent internal function (or QA) audits projects against the organization's process and against evidence authenticity — sampling records, verifying sign-offs exist, checking traceability, and reporting to the audit committee.
- **External compliance audits:**
  - **SOC 2** (AICPA): Type I (design) / Type II (operating effectiveness over a period) — auditor *tests* controls (including change management and SDLC controls: code promotion, change approval, separation of duties) and issues an attestation; the Trust Services Criteria (security, availability, processing integrity, confidentiality, privacy) explicitly cover delivery.
  - **ISO 27001**: ISMS certification audited by accredited certification bodies; Annex A includes A.8.25–8.31 (secure development lifecycle, security testing, change management, separation of environments) — audited with evidence sampling.
  - **GDPR**: DPIAs, records of processing, data-protection-by-design reviews are audited by DPAs; delivery gates must include privacy review evidence.
  - **SOX 404 (public companies)**: IT General Controls (ITGC) — including change management controls around financial systems — are tested by external auditors; unauthorized changes to a financial system are a material weakness.
  - **PCI DSS**: quarterly scans + annual on-site assessment (QSA); evidence of change control for CDE systems.
  - **FDA**: site inspections (483s/warning letters) verify that validation evidence is real, complete, and contemporaneous.
- **What audits prevent:** process theater — documented processes that are not followed, sign-offs that are not real, and evidence created after the fact.

### 4.4 Quality-gate evidence: verifying the evidence is real (not just "says PASS")

The weakest link in every governance system is *asserted* evidence ("QA says PASS"). Real systems use:

1. **Independent verification (IV&V):** a party other than the developer verifies (IEEE 1012 IV&V standard; NASA/DoD IV&V contractors; DO-178C *independence* requirements — verifier separate from implementer for higher DALs; CMMI appraisals conducted by external licensed lead appraisers).
2. **Machine-verified evidence:** CI/CD pipelines that *produce* the evidence (test reports, coverage, SAST/DAST results, SBOM, build provenance) with hashes and timestamps, so a human reviews *tool output*, not self-reports. Gates (e.g., SonarQube quality gates, Azure DevOps release gates) automatically fail the release when thresholds are not met — evidence cannot be "claimed."
3. **Signed attestations & provenance:** **SLSA** (Supply-chain Levels for Software Artifacts, OpenSSF) levels 1–4 require build integrity and **provenance** (who/what produced the artifact, verifiably signed); **in-toto** attestations; code signing. NIST **SSDF (SP 800-218)** — fetched this research — defines 4 practice groups (PO Prepare the Organization; PS Protect the Software; PW Produce Well-Secured Software; RV Respond to Vulnerabilities) whose practices include *verifying* that security requirements are met before release (PW.8 "verify that the software's security functionality works as intended" via testing and analysis) and *attesting* to that verification (PW.9); EO 14028 made SSDF adherence a federal procurement requirement, making SBOMs and attestation mandatory in federal software supply chains.
4. **Sampling and surprise checks:** auditors and governance boards spot-check artifacts; random re-testing; "mystery shopper" style verification.
5. **Consequence design:** if evidence later proves fabricated, the accountable person's sign-off authority is withdrawn (and in regulated contexts, career/legal consequences) — the *incentive* design is as important as the process.

---

## 5. Human Accountability Structures

### 5.1 RACI matrices

- **RACI:** Responsible (does the work), **Accountable** (answerable for the outcome — exactly one per deliverable; the "A" is the person whose head rolls), Consulted (two-way input), Informed (one-way notification). PMBOK and virtually every delivery framework require a RACI for major deliverables.
- Variants: **DACI** (Intuit; Driver, Approver, Contributor, Informed) — separates the Driver who runs the process from the single Approver.
- **Why it matters:** ambiguity of accountability is the root cause of "everyone thought someone else checked." The single-A rule (one Accountable per deliverable/gate) is the mechanism that makes a GO/NO-GO *someone's* decision.

### 5.2 Sign-off authority (who can say NO)

- Sign-off authority is *assigned, not implicit*: named roles (sponsor, product owner, security lead, release manager, certifying engineer) hold explicit vetoes.
- The **right to say NO** is the actual power in a gate: security leads at Google/Microsoft can block launches; the FAA's designee can reject certification evidence; the FDA can refuse a submission; the shiproom executive can kill a feature.
- Structurally, sign-off is meaningful only if (a) it is documented (who signed, when, what they reviewed), (b) refusal is consequence-free for the refuser and costly for the refusee, and (c) bypass is impossible (no "escalate around the gatekeeper" without the gatekeeper's own approval).

### 5.3 Escalation paths (what happens when a gate fails)

- **Gate fails →** the standard ladder: (1) recycle/rework with a re-review date (most common); (2) partial approval with conditions (conditional GO with named owners and deadlines); (3) Kill (project terminated; resources reallocated; lessons learned recorded); (4) **escalation** — the issue is raised to the next authority level: team → PM → steering committee → sponsor/executive → board/regulator for material items.
- **Incident escalation:** severity-based (Google SEV-1/2/3, Microsoft Sev A/B, Amazon Sev-1/2) with defined response times and automatic escalation if unresolved; incident command structure (single Incident Commander) during recovery.
- **Change escalation:** failed change → problem management (root cause) → emergency change; repeated failures → process change (the "second failure" doctrine at Amazon/Google: the first failure is the system's fault; the second is the process's fault for not preventing recurrence).

### 5.4 Approval chains (who approves what)

| Decision | Typical approver chain |
|---|---|
| Idea → funded project | PM → portfolio board / investment committee → sponsor |
| Requirements baseline | Business owner → sponsor (steering committee) |
| Design | Tech lead → ARB → (security/arch) |
| Test completion / quality | QA lead → PM → steering committee |
| Security | Security review board (final sign-off) |
| Release to production | Release board (shiproom/launch review) → change authority (CAB) for the production change → operations |
| Rollback / incident response | Incident commander (pre-authorized) / emergency change authority |
| Kill a project | Steering committee / sponsor with PMO recommendation |

The chain is deliberately redundant: *the deeper the consequence, the higher the approver* (money, customers, regulation, irreversibility).

### 5.5 The "human in the loop" — why humans hold final GO/NO-GO

1. **Accountability cannot be delegated.** Regulatory sign-offs (FDA e-signatures 21 CFR Part 11, SOX certifications by CEOs/CFOs, aviation certification by named engineers) are legally personal; a machine cannot be a responsible person under law.
2. **Judgment on trade-offs.** Gate decisions weigh incommensurable values (ship date vs. quality vs. reputation vs. risk) that require business context and risk appetite only humans hold (or should hold).
3. **Irreversible vs. reversible decisions (Amazon doctrine).** "Two-way door" decisions (reversible, cheap to undo) get delegated and fast; "one-way door" decisions (irreversible — e.g., a regulatory filing, a public commitment, deleting data, changing a contract) require humans, slow process, and the most senior accountable person. Gate severity is calibrated to reversibility.
4. **Resistance to automation gaming.** If evidence is machine-generated and gates machine-run, teams optimize the metric; a human review layer with sampling and judgment catches "driving by the numbers" (the CMMI/Deming lesson: measuring alone corrupts; humans interpret).
5. **Moral/liability standing.** A machine has no liability, no career, no conscience; the *threat* of personal accountability is the enforcement mechanism that makes governance real.
6. **Devil's advocacy and cognitive diversity.** Boards exist to hear dissent (the "have backbone" Amazon principle; NASA's independent review boards existed precisely because in-group decisions failed — Challenger §6.5).
7. **The realistic model is human-on-the-loop:** automation assembles, verifies, and even *pre-approves* evidence; humans review exceptions, sampling, and high-stakes/irreversible gates. Google's LCE checks, Azure release gates, and shiproom dashboards all follow this shape — the human decision is informed by machine-verified facts but is not replaced by them.

---

## 6. Failure and Recovery Governance

### 6.1 Change failure management

- **What happens when a release breaks:** the change/incident process takes over: incident detection (monitoring/alerts), **severity classification**, incident commander appointment, **containment first (rollback or mitigation), root cause later**, and a formal record (incident ticket) that links back to the change that caused it.
- **Metrics that govern:** **change failure rate** (proportion of deployments causing degraded service — a DORA key metric), MTTR, and the **error budget** (Google SRE): releases are limited by remaining budget; if the budget is exhausted, releases stop — *the system itself gates release velocity*.
- **Prevents:** "fire and forget" deployments, repeated identical failures, and releases during fragile periods without owner.
- **Example:** AWS/Google run "war rooms"/incident bridges; the 2012 Knight Capital incident (§6.5) is the canonical warning: a bad deployment without rollback capability destroyed the firm.

### 6.2 Rollback governance (who authorizes rollback)

- **Pre-authorization is the pattern:** for standard/automated deployments, **rollback is pre-authorized by the change/runbook** — the on-call engineer or incident commander may roll back without further approval because speed matters; the rollback itself is logged and post-reviewed (ITIL: standard change model includes rollback; Google SRE: automated rollback on canary failure needs no human).
- For emergency or high-risk production, rollback is an **emergency change** authorized by the emergency change authority, or a decision of the incident commander after severity classification.
- **Design requirements that make rollback governable:** feature flags (disable a feature without redeploying — the modern default), blue/green or canary deployment architectures, database migrations with rollback scripts, and *tested* rollback (a rollback that has never been rehearsed is not a rollback).
- **Prevents:** prolonged outages caused by "trying to fix forward" — the industry rule is *roll back first, fix the root cause second*.

### 6.3 Postmortem processes

- **Blameless postmortems (Google SRE; adopted broadly):** after any incident (severity threshold triggers one), a written postmortem with: timeline, impact, root cause analysis (with 5 Whys or similar), action items **each with an owner and deadline**, and explicit *"what would prevent this class of failure"* fixes. **Blameless** is the load-bearing design: people who fear punishment hide errors, so the process must separate *system* faults from *individual* accountability (individual fault is handled by management separately, not in the postmortem).
- **Amazon COE (Correction of Errors):** a formal document (5-whys, impact, actions, escalation) reviewed by senior leadership; **every** Sev-1/2 incident gets a COE; the "second failure" doctrine — a second COE on the same root cause escalates the *process* problem.
- **SAFe I&A** and **Agile retrospectives** are the same pattern at lower severity levels; **PDCA/Kaizen** (Deming/Toyota) is the underlying continuous-improvement loop: Plan → Do → Check → Act, with the "Check" step being measurement of whether the fix worked.
- **ITIL problem management** institutionalizes this: known errors, workarounds, permanent fixes, and review of problem records.
- **Prevents:** recurring incidents, knowledge loss, and the "postmortem without action items" that is the #1 failure mode of postmortem programs.

### 6.4 Continuous improvement

- **Mechanisms:** retrospectives (every sprint), I&A (every PI), postmortems (every significant incident), lessons learned (project close — PMBOK), CAPA (corrective and preventive action — FDA-regulated), improvement registers (ITIL), PDCA/Kaizen (Lean), CMMI ML5 (optimizing requires measured, data-driven improvement), DORA metrics programs (deployment frequency, lead time, change failure rate, MTTR) with improvement targets.
- **Governance of improvement itself:** improvements are backlogged, owned, and *checked* for effectiveness — the "Act" of PDCA; without the check, improvement is theater.

### 6.5 Cautionary tales (what failed when governance was absent/weak)

- **Knight Capital (2012):** a deploy of untested code to production with a missing configuration flag and **no working rollback** caused $440M loss in ~45 minutes and the firm's sale. Change management + rollback governance failure.
- **Boeing 737 MAX (2018–19):** certification governance failure — FAA's delegated authority (ODA) review of MCAS was incomplete; two fatal crashes; followed by worldwide regulatory overhaul of delegation and certification oversight. *Governance is only as strong as the independence and rigor of its gatekeepers.*
- **Equifax (2017):** a known, patchable vulnerability went unpatched for months — the change/patch management gate failed; 147M records exposed.
- **SolarWinds (2020):** the software supply chain itself was compromised via the build pipeline — the *integrity of release evidence* (signed builds, provenance) was the missing control; drove SLSA, SBOM mandates (EO 14028, NIST SSDF).
- **NASA Challenger (1986):** the Flight Readiness Review process had the evidence (O-ring data) but the decision was made under launch pressure; the independent-review lesson led to IRTs and stronger FRB independence. The *incentives and independence* of the gatekeeper matter as much as the gate.
- **Healthcare.gov launch (2013):** schedule-driven launch of an untested integrated system; the "test and fix" happened in production.

---

## 7. Synthesis: Design Implications for an AI Governance System

Since this research will be compared against an AI delivery-governance system design, the recurring patterns worth encoding:

1. **Gates are first-class objects** with explicit exit criteria, artifact lists, named approvers, and a decision vocabulary (GO / CONDITIONAL GO / HOLD / KILL) — and gate outcomes are recorded in a decision log.
2. **Evidence beats assertion:** every criterion maps to verifiable evidence (tool output, records), and there is an independent verification step (IV&V, sampling, or automated provenance) so "PASS" cannot be merely claimed.
3. **Single accountable owner per decision** (RACI "A"), with explicit sign-off authority and veto rights, and calibrated approval chains (higher authority for money, customers, regulation, irreversibility).
4. **Human-on-the-loop for high-stakes/irreversible gates** — automation assembles and pre-checks; humans decide, with dissent recorded.
5. **Escalation and failure paths designed in advance:** what happens at each gate failure, rollback pre-authorization, incident command, blameless postmortems with owned action items, and a "second failure" doctrine.
6. **Continuous improvement is a gated, measured loop** (PDCA/retrospective/I&A/postmortem), not an aspiration.
7. **Independence of gatekeepers** (board composition, external audit, IRT/IV&V) is what separates real governance from theater — the single most consistent lesson from both successful frameworks and the cautionary tales.

---

## 8. Sources

**Fetched and read during this research:**
- CMMI Institute — CMMI Levels of Capability and Performance: https://cmmiinstitute.com/learning/appraisals/levels
- The 2020 Scrum Guide (Schwaber & Sutherland): https://scrumguides.org/scrum-guide.html
- NIST SP 800-218, Secure Software Development Framework (SSDF) v1.1: https://csrc.nist.gov/pubs/sp/800/218/final (DOI 10.6028/NIST.SP.800-218)
- Atlassian — "What is Scrum?": https://www.atlassian.com/agile/scrum
- IBM — "What is change management?": https://www.ibm.com/topics/change-management
- Steven Sinofsky, Hardcore Software (Windows/shiproom history): https://hardcoresoftware.learningbyshipping.com

**Canonical references (publicly documented; primary sites were unreachable from this environment but content is standard):**
- PMI, *A Guide to the Project Management Body of Knowledge (PMBOK Guide)*, 6th/7th eds.: https://www.pmi.org/pmbok-guide-standards
- ISO/IEC/IEEE 12207:2017, *Software life cycle processes*: https://www.iso.org/standard/63787.html
- Scaled Agile, SAFe framework (PI Planning, ART, I&A, Continuous Delivery Pipeline): https://www.scaledagileframework.com/program-increment/
- Axelos, ITIL 4 (Change Enablement practice, CAB): https://www.axelos.com/certifications/itil-service-management
- Robert G. Cooper, Stage-Gate process: https://www.stage-gate.com ; Cooper & Sommer (2016), "The Agile–Stage-Gate Hybrid Model," *Journal of Product Innovation Management*
- US DoDI 5000.02 / Adaptive Acquisition Framework (Milestones A/B/C, OT&E, EVM ANSI/EIA-748)
- NASA NPR 7123.1B, *NASA Systems Engineering Processes and Requirements* (SRR→PDR→CDR→TRR→FRR→PLAR)
- NIST EO 14028 implementation (SSDF adoption, SBOM requirements)
- Google, *Site Reliability Engineering* and *The Site Reliability Workbook* — "Launch Coordination Engineering," error budgets, blameless postmortems: https://sre.google/books/
- OpenSSF SLSA (Supply-chain Levels for Software Artifacts): https://slsa.dev
- Microsoft Security Development Lifecycle: https://www.microsoft.com/en-us/securityengineering/sdl
- Microsoft Azure Pipelines release gates / deployment rings: https://learn.microsoft.com/en-us/azure/devops/pipelines/release/approvals
- *One Dev* (Pascal Zachary, 2019, Microsoft Press) and Sinofsky's Hardcore Software (shiproom history)
- SEC administrative proceedings, *In re Knight Capital Americas LLC* (2013) — change/rollback failure
- NTSB/FAA reports on Boeing 737 MAX; GAO and AIA reviews of FAA ODA certification
- Equifax breach: FTC/Congressional reports (2017–2018)
- SolarWinds: CISA Joint Advisory AA20-352A; EO 14028
- Rogers Commission Report on Space Shuttle Challenger (1986)
- AICPA SOC 2 (Trust Services Criteria); ISO/IEC 27001:2022 (Annex A A.8.x); GDPR Art. 35 (DPIA); SOX §404 / PCAOB ITGC guidance; PCI DSS v4
- DO-178C (RTCA) — software considerations in airborne systems; ISO 26262; IEC 62304; FDA 21 CFR 820.30 (design controls), 21 CFR Part 11 (e-signatures)
- DORA (DevOps Research & Assessment) metrics: https://dora.dev
