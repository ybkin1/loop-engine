# Software Engineering Roles and How Each Role Guarantees Quality

**Task:** T-0083 — Research real-world software engineering ROLES and how each role guarantees quality
**Date:** 2026-07-31
**Purpose:** Evidence base for loop-engine's governance design — which quality mechanisms real organizations (Google, Microsoft, Amazon, enterprise/agile/startup practice) attach to which roles, what artifacts those roles produce, and which gates they control.
**Method:** Web research on primary sources (Google Engineering Practices, "Software Engineering at Google" book, Google SRE book, Microsoft Learn DevOps resource center, .NET Shiproom documentation, DORA, Scrum Guide, OWASP, ISTQB, SEI, trunkbaseddevelopment.com, adr.github.io, Diátaxis, Martin Fowler) plus established industry knowledge where noted. Every claim is tagged `[source]` or `[knowledge]` (established practice from training knowledge where a live URL was unavailable).

---

## Table of Contents

1. [Executive Summary](#0-executive-summary)
2. [Role 1: Software Engineer / Developer](#1-software-engineer--developer)
3. [Role 2: Tech Lead / Senior Engineer](#2-tech-lead--senior-engineer)
4. [Role 3: Architect (System/Application)](#3-architect-systemapplication)
5. [Role 4: QA Engineer / SDET](#4-qa-engineer--sdet)
6. [Role 5: Test Engineer](#5-test-engineer)
7. [Role 6: Project Manager / Scrum Master](#6-project-manager--scrum-master)
8. [Role 7: Product Manager](#7-product-manager)
9. [Role 8: Release Engineer / DevOps](#8-release-engineer--devops)
10. [Role 9: Delivery Manager](#9-delivery-manager)
11. [Role 10: Site Reliability Engineer (SRE)](#10-site-reliability-engineer-sre)
12. [Role 11: Security Engineer](#11-security-engineer)
13. [Role 12: Tech Writer / Documentation](#12-tech-writer--documentation)
14. [Cross-role quality mechanisms](#cross-role-quality-mechanisms)
15. [Synthesis: gates by role](#synthesis-gates-by-role)
16. [Source register](#source-register)

---

## 0. Executive Summary

Real engineering organizations do not rely on a single "QA step"; they distribute quality control across every role, and each role holds specific **gates** it can pull. The recurring pattern:

- **Quality is pushed as early as possible** ("shift left"): the developer is the primary quality owner; tests, static analysis, and code review happen before merge — Google calls this the "Beyoncé Rule": *test everything you don't want to break* `[source: SWE book ch11]`.
- **Every role produces durable artifacts** (design docs, ADRs, test plans, SLOs, postmortems) that serve as reviewable, auditable quality records.
- **Named ceremonies formalize the gates**: code review (LGTM / branch policies), design doc reviews, ATAM-style architecture evaluation, shiproom release reviews, GO/NO-GO release readiness reviews, sprint reviews/retrospectives, blameless incident postmortems.
- **Data-driven escalation replaces politics**: SRE error budgets decide whether releases proceed; DORA metrics (deployment frequency, lead time, change fail rate, recovery time) measure whether the delivery system is healthy; Microsoft measures OKRs and "changes in incident frequency", explicitly rejecting velocity/burndown/LOC as quality metrics.
- **Accountability is enforced through consequences**: Google's Build Cop rolls back breaking changes; Microsoft's "bug cap" (engineers × 5) forces teams to stop features and fix bugs; a depleted error budget freezes releases; a failed deployment triggers a blameless postmortem with tracked action items.

The single most consistent cross-company quality backbone is: **trunk-based development + mandatory pre-merge review + automated tests as merge gates + staged deployment with rollback + measurable service objectives + postmortems that close the loop**.

---

## 1. Software Engineer / Developer

*Synonyms: Developer, SWE, Programmer, Engineer I-IV.*

### Core responsibilities
- Write code and tests for assigned features/bug fixes; own the change end-to-end from branch to merge.
- In Scrum (2020 Guide), "Developers" are accountable for the Increment: creating a plan for the Sprint, instilling quality by adhering to the Definition of Done, and adapting their plan daily toward the Sprint Goal `[source: Scrum Guide]`.
- At Microsoft, engineering "builds the products and ensures their quality" `[source: MS how-microsoft-plans-devops]`.
- Maintain code health: pay down bugs as they go; Microsoft caps bugs at `# engineers × 5`; if the count exceeds the cap at sprint end, the team stops feature work until under the cap `[source: MS how-microsoft-plans-devops]`.

### Quality mechanisms
- **Mandatory precommit code review** — Google: no change enters the codebase without review; approval signal is **LGTM** ("looks good to me"); ~35% of changes touch a single file; most changes reviewed by exactly one reviewer `[source: SWE book ch09]`.
- **Small changes** — Google: ~200 LOC per change is the norm; reviewers may reject a CL purely for being too large; large changes must be split (stacking, by-file, horizontal, vertical, grid) `[source: SWE book ch09; eng-practices small-cls]`.
- **Self-review before sending** — the CL author is expected to review their own change, test it, and write a good description before requesting review `[knowledge: eng-practices author guide; confirmed by the "handling-comments" and reviewer guidance which assume author diligence]`.
- **Tests in the same change** — Google: add unit/integration/e2e tests in the same CL unless emergency; human reviewers verify tests because "tests do not test themselves" `[source: eng-practices looking-for]`.
- **The Beyoncé Rule** — "If you liked it, then you shoulda put a test on it": test everything you don't want to break; developers write tests for their own code `[source: SWE book ch11]`.
- **Test sizes** — small (single process/thread, no I/O), medium (multi-process, localhost network), large (multi-machine/e2e); distribution target ~80% small, 15% medium, 5% large `[source: SWE book ch11]`.
- **Presubmit checks and static analysis in review** — Google runs analyzers (Error Prone, clang-tidy via Tricorder) on every code review change; reviewers push "Please Fix" (thousands of times/day); auto-fixes applied from review comments `[source: SWE book ch20]`.
- **TDD and pair programming** — classic XP/agile practices where developers write tests first and review each other's work in real time `[knowledge]`.
- **Readability / style guide compliance** — Google's style guides are "canon"; formatting enforced by clang-format/gofmt and presubmit rejection of unformatted code `[source: SWE book ch08]`.
- **Definition of Done adherence** — the team-level quality contract (see cross-role section) `[source: Scrum Guide]`.

### Artifacts produced
- Pull request / changelist with a clear description (first line summarizes the change) `[source: SWE book ch09]`.
- Unit/integration tests, test doubles, fixtures.
- Code comments ("explain why, not what") `[source: eng-practices looking-for]`.
- Feature-flag wiring for staged rollout `[source: MS how-microsoft-develops-devops]`.
- Input to design docs (rarely the sole author for complex changes) `[source: industrialempathy design-docs]`.

### Gates controlled
- **Can block others**: a developer reviewing a peer's CL owns the code and may deny approval ("the reviewer is responsible for the code under review... may deny approval even if the change is well designed") `[source: eng-practices standard]`.
- **Is gated by**: LGTM + OWNERS approval + readability approval at Google `[source: SWE book ch09]`; at Microsoft, branch policies (build validation incl. ~60,000 tests in <5 min, code-owner sign-off, external policy checks) `[source: MS how-microsoft-develops-devops]`.

### Interactions
- Reviews peers' code; escalates disagreements to tech lead / maintainer / engineering manager `[source: eng-practices standard]`.
- Works with QA/SDET on test frameworks; with Release Engineer when a build breaks; with SRE on operational readiness of the change; with PM on acceptance criteria.

### Accountability
- Slow or sloppy reviews hurt team velocity — Google sets "one business day max" response and "always unblock the developer" norms `[source: eng-practices speed]`.
- Breaking the build: Google teams rotate a **Build Cop** whose job is to restore the build, usually by rolling back the offending change `[source: SWE book ch23]`.
- Flaky tests destroy trust in the suite (Google tracks flakiness to ~0.15%) `[source: SWE book ch11]`.
- Post-submit failures are bisected back to the responsible change; cherry-picked into release branches with review `[source: SWE book ch23; MS how-microsoft-develops-devops]`.

---

## 2. Tech Lead / Senior Engineer

*Synonyms: Tech Lead, TL, Senior SWE, Staff Engineer (larger scope).*

### Core responsibilities
- Own the technical direction of a team: architecture decisions at team scope, design docs, code-review gatekeeping, technical debt management, mentoring.
- Google's model: tech leads still write code (~30% of time `[knowledge]`) and review the bulk of the team's changes; they are the escalation point when author/reviewer disagree `[source: eng-practices standard: "escalate to... Tech Lead, maintainer, or Engineering Manager"]`.
- OWNERS files: per-directory approval lists enforced at commit time — the tech lead typically owns key directories `[source: SWE book ch16]`.

### Quality mechanisms
- **Design docs before code** — Google practice: 10–20 page design docs (1–3 pages for "mini design docs") covering context/scope, goals & non-goals, design, alternatives considered, cross-cutting concerns (security, privacy, observability); reviewed by senior engineers, often in formal review meetings; the doc is updated as reality changes `[source: industrialempathy design-docs-at-google]`.
- **Code review as a teaching gate** — reviewers treat the author's questions as "customers"; unclear code = future maintenance problem; "don't accept CLs that degrade the code health of the system" `[source: eng-practices looking-for]`.
- **Technical debt management** — debt is a conscious "loan" with interest `[knowledge: SWE book terminology]`; Microsoft's "zero debt" sprint policy + bug cap `[source: MS how-microsoft-plans-devops]`; Google's **Large-Scale Changes (LSC)** program for cross-cutting refactors (Rosie sharding, global approver, TAP train batching, deprecation enforcement via Tricorder flagging deprecated API use at review time) `[source: SWE book ch22]`.
- **Readability certification** — senior engineers mentor juniors through Google's readability process so they internalize style-guide habits; readability is a separate approval bit that scales review `[source: SWE book ch08, ch09]`.
- **Consistent standards** — contributes to and enforces the team's engineering practices; Google's eng-practices documents are exactly this kind of artifact (review standard, speed norms, comment etiquette, pushback handling) `[source: eng-practices]`.
- **Definition of Done enforcement** — the tech lead usually champions the team's DoD and holds the line at sprint boundaries `[knowledge; Scrum Guide: "instill quality by adhering to the Definition of Done"]`.

### Artifacts produced
- Design docs, ADRs (decision records), OWNERS files, tech-debt backlog, coding standards / review checklists, mentoring review comments, architecture review board submissions `[sources: industrialempathy; adr.github.io; SWE book ch16]`.

### Gates controlled
- Approves/denies merges in owned directories (OWNERS) `[source: SWE book ch16]`.
- Approves or rejects design docs before implementation starts.
- Decides what debt is acceptable; can force refactoring work into the roadmap.
- Can escalate review deadlocks and has the final word on team-scope technical disputes `[source: eng-practices standard]`.

### Interactions
- Up: Architect (system-level decisions), Engineering Manager, Delivery Manager (release readiness input).
- Down: mentors engineers; reviews their CLs; assigns design doc authorship.
- Sideways: PM (feasibility, effort), QA (test strategy), SRE (SLO feasibility, production readiness).

### Accountability
- Design failures trace back to the design doc and its alternatives analysis — the doc is the audit trail `[source: industrialempathy]`.
- Refactoring debt that never gets paid shows up as rising change fail rate / lead time (DORA metrics) `[source: dora.dev]`.
- If the team's build breaks repeatedly, the Build Cop process and postmortems point at systemic review gaps the tech lead owns `[source: SWE book ch23]`.

---

## 3. Architect (System/Application)

*Synonyms: System Architect, Application Architect, Principal Engineer, Chief Architect, Solution Architect.*

### Core responsibilities
- System-level architecture: structure, NFRs (performance, availability, scalability, security), interface contracts, technology selection, cross-system consistency.
- In Microsoft's model, "strict guidelines in certain tiers ensure uniformity among teams across the product" — the architectural layer that enforces those guidelines `[source: MS how-microsoft-plans-devops]`.

### Quality mechanisms
- **Architecture Decision Records (ADRs)** — a justified design choice addressing an architecturally significant requirement, with rationale, trade-offs, and consequences; the collection is a **decision log**; popularized by Michael Nygard (2011) `[source: adr.github.io]`.
- **ATAM (Architecture Tradeoff Analysis Method)** — SEI's leading architecture evaluation method: scenario-based analysis of quality attributes, a quality-attribute utility tree, identification of risks, sensitivity points and tradeoff points; participants include the architect, stakeholders, and an independent evaluation team; output is a risk register for the architecture `[knowledge: SEI ATAM — the SEI site confirms ATAM as "the leading method in the area of software architecture evaluation"; steps from established SEI material]`.
- **Design doc review with cross-cutting concern owners** — Google's design docs explicitly include security, privacy, and observability sections, and there are dedicated privacy/security review processes attached to design `[source: industrialempathy]`.
- **Interface contracts and API review** — e.g., the .NET/ASP.NET Core **API review process** (docs/APIReviewProcess.md): proposed API changes go through a formal review board before acceptance because APIs are contracts that can't be broken later; the servicing bar additionally forbids any public API change in patch releases `[source: dotnet/aspnetcore docs; Servicing.md]`.
- **NFR definition and handoff to SLOs** — NFRs (e.g., "GCE availability target 99.95%") become SLO inputs that SRE operationalizes `[source: SRE book ch4]`.
- **Technology selection with evidence** — proof-of-concept prototypes ("I tried it out and it works" is the strongest argument), build-vs-buy analysis, technology radar (ThoughtWorks-style), "boring technology" preference `[knowledge]`.
- **Architecture review boards / design councils** — recurring forums where cross-cutting designs are presented before investment `[knowledge]`.
- **IEEE 42010 / ISO/IEC/IEEE 42010** — standard for architecture description: architecture views and viewpoints for different stakeholders `[knowledge]`.
- **C4 model / arc42** — documentation conventions that make architecture reviewable `[knowledge]`.

### Artifacts produced
- Architecture docs (views/viewpoints), ADRs + decision log, interface/API contracts (OpenAPI, protobuf), NFR documents, technology assessments, architecture review reports (ATAM outputs: risks, sensitivity/tradeoff points), tech radar entries `[sources: adr.github.io; SEI; knowledge]`.

### Gates controlled
- **Architecture sign-off**: can block design docs / feature implementations that violate NFRs or architectural principles.
- **API compatibility gates**: versioning policy (semver; "no API changes in patch releases" `[source: dotnet Servicing.md]`).
- **Technology selection veto**: can reject dependencies/languages/frameworks that fail governance criteria `[knowledge]`.
- Input to release readiness: architecture risk review for complex releases `[knowledge]`.

### Interactions
- Tech leads (team-level design consistency), SRE (NFR → SLO translation; capacity), Security (threat model integration), PM (non-functional priorities, cost of reliability), Delivery Manager (risk assessment), Release Engineer (deployment topology constraints).

### Accountability
- ATAM-style reviews surface architectural risks before they become production failures `[knowledge: SEI]`.
- ADRs make decisions auditable — a bad call is visible with its alternatives and can be revisited `[source: adr.github.io]`.
- NFR misses in production (latency, availability) trace to architecture and become SLO/error-budget failures the architect must address `[source: SRE book ch3-4]`.

---

## 4. QA Engineer / SDET

*Synonyms: QA Engineer, SDET (Software Development Engineer in Test), Test Automation Engineer, Quality Engineer.*

### Core responsibilities
- Own the **test strategy**: what to test at which level, with what tools, and how fast.
- Build and maintain test automation frameworks; ensure tests run reliably in CI.
- Drive "shift left": detect errors in minutes, not days `[source: MS how-microsoft-develops-devops]`.
- Advise developers on testability and test design; enforce the test pyramid.

### Quality mechanisms
- **Test pyramid** — many unit tests, fewer service/integration tests, fewest e2e/GUI tests; e2e tests are "brittle, expensive to write, and time consuming to run" and are a "second line of test defense" `[source: Martin Fowler TestPyramid; SWE book ch11 80/15/5]`.
- **Test sizes & hermeticity** — Google classifies small/medium/large and prefers hermetic tests; record/replay proxies capture real traffic for smaller tests; A/B diff regression testing compares old vs new systems on real traffic `[source: SWE book ch11, ch14]`.
- **Flakiness management** — Google tracks flakiness to ~0.15% to preserve trust; larger tests get quarantine, bug-tagged disablement, clear owners, and understandable failure messages `[source: SWE book ch11, ch14]`.
- **CI integration** — TAP (Test Automation Platform) runs suites on every change; presubmit runs fast small tests, post-submit runs broader suites asynchronously `[source: SWE book ch23]`.
- **Chaos and disaster testing** — Google's DiRT (Disaster Recovery Testing) and Catzilla (chaos engineering) validate recovery; probers and canary analysis smoke-test production `[source: SWE book ch14]`.
- **Exploratory testing and bug bashes** — manual discovery of unanticipated issues, organized as events `[source: SWE book ch14]`.
- **Mutation testing, coverage dashboards, property-based testing** — standard SDET tooling to verify the tests themselves `[knowledge]`.
- Microsoft: PR builds run "first- and second-level test suites (~60,000 tests in under five minutes)" — speed of the suite is a QA engineering problem, not just a dev one `[source: MS how-microsoft-develops-devops]`.

### Artifacts produced
- Test strategy/plan, automated test suites and frameworks, test reports and dashboards, flakiness/coverage metrics, defect reports with root-cause analysis, testability recommendations in design docs `[sources: Fowler; SWE book ch11/14]`.

### Gates controlled
- **Merge gates**: failing tests block merges (branch policy build validation) `[source: MS how-microsoft-develops-devops]`.
- **Release gates**: test sign-off for release candidates; can block a release on test failures `[knowledge]`.
- **Flaky-test policy**: can quarantine/disable flaky tests with a bug attached — a quality decision in itself `[source: SWE book ch23]`.

### Interactions
- Developers (they write unit tests; SDET provides frameworks and review), Test Engineers (manual/exploratory/UAT), Release Engineer (pipeline gates), SRE (probers, canary validation), PM (acceptance criteria → automated acceptance tests).

### Accountability
- Escaped defects → test-gap analysis in the postmortem (why did no test catch it?).
- If the suite becomes slow/flaky, developers bypass it — Google keeps false-positive rates <5% for analysis checks `[source: SWE book ch20]`.
- "Tests do not test themselves" — the quality of the tests is reviewed like code `[source: eng-practices looking-for]`.

---

## 5. Test Engineer

*Synonyms: Tester, Test Analyst, Manual QA, Quality Analyst. (In ISTQB terms: the test role in the test process.)*

### Core responsibilities
- **Test planning and test case design** from requirements; regression suite maintenance; coordination of User Acceptance Testing (UAT); exploratory testing execution.
- ISTQB (CTFL) defines the fundamental test process: test planning, test monitoring & control, test analysis, test design, test implementation, test execution, test completion `[knowledge: ISTQB CTFL syllabus v4.0]`.

### Quality mechanisms
- **Test levels** — component, integration, system, acceptance; each level has defined objectives and entry/exit criteria `[knowledge: ISTQB]`.
- **Black-box test design techniques** — equivalence partitioning, boundary value analysis, decision tables, state transition testing, use-case testing `[knowledge: ISTQB]`.
- **White-box techniques** — statement and decision coverage; coverage measured against exit criteria `[knowledge: ISTQB]`.
- **Requirements traceability matrix (RTM)** — every requirement mapped to test cases; the mechanism that proves coverage and detects requirement gaps `[knowledge: PMI/ISTQB practice]`.
- **Risk-based testing** — prioritize test effort by failure likelihood × impact `[knowledge: ISTQB]`.
- **UAT coordination** — structured acceptance testing with business users against acceptance criteria; documented sign-off `[knowledge; UAT mentioned in SWE book ch14 as a user-focused verification practice]`.
- **Session-based exploratory testing** — time-boxed charters, debriefs `[knowledge]`.
- **Regression suite selection** — deciding which tests re-run per change level, balancing coverage and speed `[knowledge: ISTQB regression testing]`.
- **IEEE 829 test documentation** — standard for test plans, test case specs, test summary reports `[knowledge]`.

### Artifacts produced
- Test plan, test cases, regression suite, UAT scripts and results, test summary report, defect reports (severity/priority, reproducible steps), RTM, exit-criteria assessment `[knowledge: ISTQB/IEEE 829]`.

### Gates controlled
- **Exit criteria sign-off**: declares when testing is complete for a release.
- **UAT sign-off**: business/user acceptance is a hard gate before production for many products `[knowledge]`.
- Defect triage voice: can escalate blocking defects to the delivery decision.

### Interactions
- QA/SDET (which tests to automate), Developers (defect triage, reproductions), PM (acceptance criteria quality), Delivery Manager (test status input to GO/NO-GO), Tech Writer (docs to verify against behavior).

### Accountability
- Escaped defects and UAT failures trigger coverage/process reviews; incomplete RTMs are an audit finding; the test summary report is the historical evidence of what was verified `[knowledge]`.

---

## 6. Project Manager / Scrum Master

*Synonyms: PM (delivery), Scrum Master, Agile Coach, Delivery Lead (delivery-focused PM).*

### Core responsibilities
- Sprint/iteration planning, scope control, risk management, status reporting, blocker removal, facilitating ceremonies.
- Scrum Master accountability (Scrum Guide 2020): effectiveness of the Scrum Team; coaching self-management; **causing removal of impediments**; ensuring all Scrum events happen and are timeboxed; helping the PO with backlog management; leading organizational Scrum adoption `[source: Scrum Guide]`.

### Quality mechanisms
- **Sprint Planning (two topics)** — "What can be Done this Sprint?" (with the PO selecting from the Product Backlog) and "How will the chosen work get done?" (developers decompose into items ≤1 day); forecasts depend on past performance, capacity, and Definition of Done `[source: Scrum Guide]`.
- **Sprint Review** — inspect the Increment and adapt the Product Backlog; the PO's decisions are "visible... through the inspectable Increment at the Sprint Review" `[source: Scrum Guide]`.
- **Sprint Retrospective** — inspect quality, effectiveness, and the DoD; plan improvements `[source: Scrum Guide]`.
- **Scope control** — the PO owns backlog ordering ("one person, not a committee"); change requests are routed through the PO, not dumped on the team `[source: Scrum Guide]`.
- **Risk management** — PMI practice: risk register, RAID log (Risks, Assumptions, Issues, Dependencies), probability/impact scoring, mitigation owners, regular risk review `[knowledge: PMBOK]`.
- **Status reporting** — Microsoft: every team sends an end-of-sprint mail reporting what was accomplished and what's next — transparency and accountability `[source: MS how-microsoft-plans-devops]`.
- **Metrics that matter** — Microsoft explicitly avoids velocity, burndown, hours, LOC, and bug counts as management metrics ("they aren't helpful for tracking progress toward objectives"); it tracks leading indicators: changes in adoption growth, performance, time-to-learn, incident frequency `[source: MS how-microsoft-plans-devops]`.
- **Planning horizons** — Microsoft: Sprints (3 weeks), Plans (3 sprints), Seasons (6 months), Strategies (12 months) `[source: MS how-microsoft-plans-devops]`.
- **Kanban/flow** — WIP limits and cycle-time focus where continuous flow beats sprints `[knowledge]`.

### Artifacts produced
- Sprint plan, product/sprint backlog hygiene, risk register/RAID log, status reports, sprint review/retrospective outcomes (action items), impediment log, meeting facilitation records `[sources: Scrum Guide; MS; knowledge]`.

### Gates controlled
- **Scope gate**: protects the sprint commitment; new work goes through the PO.
- **Readiness gate**: nothing enters a sprint unless it meets backlog-item readiness (refined, estimated, acceptance criteria clear) `[knowledge]`.
- **Escalation gate**: unblocks or escalates impediments the team can't remove `[source: Scrum Guide]`.

### Interactions
- PO (backlog), Developers (commitment), Delivery Manager (milestone status), stakeholders (status), other Scrum Masters (cross-team impediments), Release Engineer (release cadence alignment).

### Accountability
- If the team repeatedly misses commitments, the retrospective and forecast calibration absorb the lesson; the SM is accountable for the team's *effectiveness*, not the outcome `[source: Scrum Guide]`.
- Eisenhower, quoted in Microsoft's planning docs: "Plans are worthless, but planning is everything" — the process value is the planning itself `[source: MS how-microsoft-plans-devops]`.

---

## 7. Product Manager

*Synonyms: Product Owner (Scrum), PM, Product Manager, Program Manager (Microsoft legacy).*

### Core responsibilities
- Define **what to build and why** (Microsoft: "PM defines what Microsoft builds, and why") `[source: MS how-microsoft-plans-devops]`.
- Requirements definition, acceptance criteria, prioritization, feature definition, and — at Google — setting the reliability tolerance for the product `[source: SRE book ch3]`.

### Quality mechanisms
- **Amazon's Working Backwards / PRFAQ** — a product idea is written as a press release + FAQ (4–6 pages) from the customer's perspective before any code; iterated with stakeholders until it stands; this is the requirements gate for product quality: if the story doesn't hold, the feature doesn't get built `[knowledge: "Working Backwards" (Bryar & Carr); template structure confirmed `[source: PRFAQ template repo]`].
- **Acceptance criteria** — concrete, testable conditions attached to each user story; they become the Test Engineer's test basis and the developer's DoD input `[knowledge]`.
- **Prioritization frameworks** — RICE (reach/impact/confidence/effort), MoSCoW, WSJF (weighted shortest job first in SAFe) `[knowledge]`.
- **Outcome metrics over output** — Microsoft OKRs: objectives are qualitative, key results are quantified outcomes (e.g., "increase external NPS from 21 to 35"); metrics drive the backlog — teams "don't just ship features, but look to see whether and how people are using them" `[source: MS how-microsoft-plans-devops, how-microsoft-delivers-devops]`.
- **SLO/error budget input** — at Google "product management sets the SLO"; the PM decides how much reliability the product *needs* (trading features vs. uptime) `[source: SRE book ch3]`.
- **Scrum PO accountability** — the PO is accountable for value, backlog ordering, and transparency; "those wanting to change the Product Backlog can do so by trying to convince the Product Owner" `[source: Scrum Guide]`.
- **A/B testing and experimentation** — launch decisions informed by experiments, not opinions `[source: SWE book ch24; knowledge]`.
- **PowerPoint specs** — Microsoft moved from 100-page specs to compact specs to keep requirements living and reviewable `[source: MS how-microsoft-plans-devops]`.

### Artifacts produced
- PRFAQ, one-pager/PRD, user stories with acceptance criteria, ordered Product Backlog, roadmap, OKRs, launch plan, experiment plans, release notes input `[sources: PRFAQ template; MS; Scrum Guide]`.

### Gates controlled
- **Backlog gate**: nothing is built that isn't ordered into the backlog — "the Product Owner is one person, not a committee" `[source: Scrum Guide]`.
- **Acceptance gate**: decides whether delivered functionality meets the agreed criteria (usually delegated in part to QA/UAT).
- **Scope/priority veto**: can kill or defer features; can decide to spend the error budget `[source: SRE book ch3]`.

### Interactions
- Tech Lead/Architect (feasibility), Developers (refinement), QA (acceptance criteria → tests), SRE (SLO setting, budget tradeoffs), Delivery Manager (launch readiness), Tech Writer (feature docs), users/stakeholders (validation).

### Accountability
- Product failure shows up in outcome metrics and A/B data — the OKR/telemetry loop is the feedback mechanism `[source: MS how-microsoft-plans-devops]`.
- Poor acceptance criteria → rework and escaped defects; PRFAQ process makes weak ideas fail cheaply and early `[knowledge]`.

---

## 8. Release Engineer / DevOps

*Synonyms: Release Engineer, Release Manager (engineering side), DevOps Engineer, Build/Release Engineer, CI/CD Engineer.*

### Core responsibilities
- Own CI/CD pipelines, release gates, deployment automation, rollback plans, change management, build reproducibility.
- Google: release engineers "handle the labor of building, testing, and troubleshooting" releases, with automation and policy enforcement (access control on release actions), audit trails, and reports of all changes in each release `[source: SRE book ch8]`.

### Quality mechanisms
- **Hermetic builds** — self-contained, reproducible builds regardless of machine `[source: SRE book ch8]`.
- **Release trains** — fixed release cadence: "if you're late for the release train, it will leave without you"; Google's Search binary moved to a release every other day; "faster is safer" — small frequent releases reduce risk `[source: SWE book ch24]`.
- **Push on Green / release candidates** — deploy builds that pass tests; canary deployments; select builds from a pool based on test results `[source: SRE book ch8]`.
- **Staged rollout & canarying** — Google: canary to a small % of traffic, staged percentage increases, A/B deployments, change-neutral releases, flag guards to decouple code from feature exposure `[source: SWE book ch24]`.
- **Rollback / rollforward** — automatic rollbacks, culprit finding, dry-run verification `[source: SWE book ch24]`.
- **Microsoft release flow** — trunk-based main branch, topic branches with branch policies, release branches cut per sprint (`releases/M129`), cherry-pick hotfixes with full re-review, **ring-based deployment** (5 tiers: internal → small DC → public free accounts → large/internal + international → everyone) with **bake time** (~24h incl. peak) between rings; hotfix severity rules (Sev 0 can skip rings, Sev 1 must pass tier 0) `[source: MS how-microsoft-develops-devops; safe-deployment-practices]`.
- **Branch policies and permissions** — prevent direct pushes to main; only release managers create `releases/*` branches; pipeline checks: build, tests, security/compliance policy validation, owner sign-off, external checks `[source: MS how-microsoft-develops-devops]`.
- **One Engineering System (1ES)** — Microsoft's standardized engineering system (Git branching + release flow + Azure Pipelines) across the company `[source: MS how-microsoft-develops-devops]`.
- **DORA capabilities** — deployment automation, continuous delivery ("deploying software... on demand at any time"), version control traceability, and **streamlining change approval** ("replace heavyweight change-approval processes with peer review" — i.e., the CI/CD pipeline + review replaces the ITIL change board) `[source: dora.dev capabilities]`.
- **Infrastructure as code** — removes manual ops changes `[source: MS safe-deployment-practices]`.
- **Deployment during working hours** — with zero-downtime deployment, deploy early in the day/week to control blast radius `[source: MS safe-deployment-practices]`.

### Artifacts produced
- CI/CD pipelines (pipeline-as-code), deployment runbooks and rollback plans, release notes/manifests, versioned artifacts and SBOMs, environment definitions (IaC), audit trails of releases, release dashboards (DORA metrics) `[sources: MS; SRE book ch8; knowledge]`.

### Gates controlled
- **Pipeline gates**: each stage has gates (tests, approvals, health checks) — nothing promotes without passing `[source: MS]`.
- **Release freeze / train membership**: decides what makes the train `[source: SWE book ch24]`.
- **Environment access**: who can deploy where (release-manager-only branch permissions) `[source: MS]`.
- **Rollback decision authority** in automated pipelines `[source: SWE book ch24]`.

### Interactions
- Developers (build breaks, PR policies), SRE (deployment health, rollback collaboration — "working with SREs to roll back problem features" `[source: SRE book ch8]`), Delivery Manager (GO/NO-GO and release readiness), Security (signing, compliance gates), Test teams (test environment parity).

### Accountability
- **DORA metrics** measure the release process itself: deployment frequency, change lead time, change fail rate, failed-deployment recovery time `[source: dora.dev]`.
- Failed deployments trigger immediate rollback + postmortem; "bad deployments proceed and can't be rolled back" is called out as a top failure mode to engineer away `[source: MS safe-deployment-practices]`.

---

## 9. Delivery Manager

*Synonyms: Delivery Manager, Release Manager (business side), Delivery Lead, Program Manager (delivery), Release Train Engineer (SAFe).*

### Core responsibilities
- Delivery assurance across teams: milestone planning, release readiness reviews, **GO/NO-GO decisions**, stakeholder sign-off, cross-team coordination.
- Owns the question "are we really ready to ship this?" with evidence.

### Quality mechanisms
- **The Shiproom** — Microsoft's release-review meeting, publicly documented by the .NET team: meets ~twice weekly; reviews every servicing PR against a fixed **servicing bar** (significant user impact, no suitable workaround, no public API change, behavioral changes opt-in); decisions are recorded as labels: `servicing-approved` (moved to release milestone), `servicing-more-info` (re-present), or rejection; attendees are stakeholders from across the stack (runtime, libraries, app models, SDK); a fully-filled template is required so the bug is well-represented even if the author can't attend `[source: dotnet/aspnetcore docs/Servicing.md]`.
- **Milestone reviews / synch-and-stabilize** — Microsoft's classic (documented in Cusumano & Selby, "Microsoft Secrets"): scheduled milestone reviews with go/no-go decisions, daily builds ("synch"), and stabilization ("stabilize") phases with buffer time `[knowledge: Microsoft Secrets, 1995]`.
- **Release readiness review** — a checklist-driven review before each deployment stage: features done per DoD, all test levels passed, docs and runbooks updated, rollback plan verified, security sign-off, error budget available, known issues assessed `[knowledge: common practice; components verified across sources: MS shiproom bar, safe-deployment-practices, SRE error budgets]`.
- **GO/NO-GO gates** — explicit recorded decision points before build, deploy, and GA; a NO-GO is always an option and is not a failure `[knowledge]`.
- **Stakeholder sign-off matrix** — each release requires named sign-offs (product, engineering, security, ops) `[knowledge]`.
- **Release trains (SAFe)** — Program Increment planning, train-level integration and demo points, Release Train Engineer as chief-mechanic `[knowledge: SAFe — scaledagileframework.com not reachable from this environment; content from established SAFe practice]`.
- **Risk-based release decisions** — error budget state and DORA change-fail-rate inform the decision `[source: SRE book ch3; dora.dev]`.

### Artifacts produced
- Release readiness checklist, GO/NO-GO records, shiproom/minutes with labeled decisions, milestone plans, sign-off matrix, risk assessments, launch checklists, post-release review reports `[sources: dotnet Servicing.md; knowledge]`.

### Gates controlled
- **The final release gate**: can stop a release at any stage; requires rollback readiness before GO.
- Can demand re-testing, re-documentation, or security re-review.
- Escalates to executive leadership on unresolvable blockers.

### Interactions
- All roles: PM (scope), Tech Lead (risk), QA/Test (exit criteria), Release Engineer (pipeline state), SRE (SLO/error budget), Security (sign-off), executives (escalation), customers (communication of delays).

### Accountability
- If a release ships broken despite the readiness process, the postmortem reviews the process, not just the bug — the shiproom's labeled, template-driven record is the evidence `[source: dotnet Servicing.md]`.
- The delivery manager is accountable for *decision quality*, not for perfection — a NO-GO with evidence is a success `[knowledge]`.

---

## 10. Site Reliability Engineer (SRE)

*Core source: Google SRE book (chapters 3-5, 8, 14-15) `[source via mirror]` + established SRE practice.*

### Core responsibilities
- Run the production service: SLIs/SLOs, error budgets, incident management, on-call, capacity planning, monitoring, and toil elimination.
- Google: SRE is "software engineering applied to operations" — the SRE team owns the service's reliability contract `[knowledge: SRE book preface]`.

### Quality mechanisms
- **SLIs / SLOs / SLAs** — SLIs are quantitative measures (latency percentiles, error rate, throughput, availability, durability); SLOs are targets (e.g., GCE availability 99.95%, Shakespeare search latency ≤100ms); SLAs are user contracts with consequences — SRE helps define SLIs and avoid SLO failure but does not set the SLA `[source: SRE book ch4]`.
- **SLOs as floor and ceiling** — SREs avoid over-delivering reliability because it wastes resources; keep a safety margin (e.g., Chubby's planned outages) `[source: SRE book ch4]`.
- **Error budgets** — the product manager sets the SLO; actual availability vs. SLO defines a quarterly error budget (e.g., 99.99% allows ~52.56 minutes downtime per quarter); **healthy budget → launches proceed; depleted budget → releases slowed or halted** until the budget recovers; replaces political negotiation with data `[source: SRE book ch3]`.
- **Error budget policies** (SRE Workbook) — explicit written policies for what happens when the budget is exhausted; burn-rate alerts to catch fast budget consumption `[knowledge: SRE Workbook ch1]`.
- **Monitoring and alerting** — page on unplanned downtime that consumes the budget; alerts must be actionable (Microsoft: "Is this alert actionable?"; over-alerting trains people to ignore alerts) `[source: SRE book ch3; MS how-microsoft-operates-devops]`.
- **Incident management** — structured response: Incident Commander, Operations Lead, Communications Lead, Planner; focus on mitigation before root cause `[source: SRE book ch14; mirror confirmed the process; role names from established SRE practice]`.
- **Blameless postmortems** — every significant incident gets a postmortem; blameless culture ("blameless postmortem" — the goal is system improvement, not punishment); action items tracked to completion `[knowledge: SRE book ch15]`.
- **Toil elimination** — SREs spend engineering effort automating; toil is capped (target <50% of SRE time) `[knowledge: SRE book ch5]`.
- **Capacity planning** — demand forecasting, load testing, provisioning ahead of growth `[knowledge: SRE book ch26]`.
- **Production readiness reviews** — new services must pass a checklist (monitoring, alerting, runbooks, capacity, rollback, on-call) before launch `[knowledge: SRE practice]`.
- **Game days / DiRT** — rehearsed disaster scenarios `[source: SWE book ch14]`.

### Artifacts produced
- SLO/SLI dashboards, error budget reports and policies, incident reports and postmortems, runbooks/playbooks, on-call rotations and escalation policies, capacity plans, production readiness review checklists `[sources: SRE book; SWE book ch14]`.

### Gates controlled
- **Release gate via error budget**: can freeze or slow releases when the budget is exhausted `[source: SRE book ch3]`.
- **Production readiness gate**: can block a new service/feature from going to production without readiness evidence `[knowledge]`.
- **On-call gate**: can reject changes that are un-rollbackable or unmonitorable `[knowledge]`.

### Interactions
- Developers (budget-conscious changes), PM (SLO setting — the tradeoff conversation), Release Engineer (rollout safety), Security (incident response, war games), Tech Writer (runbook accuracy), Delivery Manager (release risk input).

### Accountability
- SLO misses deplete the budget → product consequences (release freezes) are automatic, not personal `[source: SRE book ch3]`.
- Incident response quality is measured (MTTD/MTTR), and postmortem action items are tracked to closure `[knowledge: SRE book ch15]`.
- Microsoft's live-site culture: "engineering pays the price for live site issues... When you get called at 2 AM to fix something you broke, you remember" `[source: MS how-microsoft-operates-devops]`.

---

## 11. Security Engineer

*Synonyms: Security Engineer, AppSec Engineer, Product Security, Security Architect.*

### Core responsibilities
- Threat modeling, security reviews, penetration testing, SAST/DAST, security gates in CI/CD, security incident response, security policy and training.

### Quality mechanisms
- **Threat modeling** — OWASP's four questions: "What are we working on? What can go wrong? What are we going to do about it? Did we do a good job?"; structured methods: **STRIDE**, kill chains, attack trees; produces a prioritized list of security improvements; continuous — updated after features, incidents, architecture changes `[source: OWASP Threat Modeling]`.
- **Microsoft Security Development Lifecycle (SDL)** — the original structured security process: training, requirements, design (threat models), implementation (static analysis), verification (dynamic/fuzz testing), release (incident response plan), response `[knowledge: Microsoft SDL; corroborated by MS security-in-devops which lists SDL among "preventing breaches" techniques]`.
- **War games (red team / blue team)** — Microsoft practice: red team attacks, blue team defends; code of conduct (do no harm, no external customer data, no destructive actions) and rules of engagement; deliverables: a **backlog of repair items with SLAs** (severe risks ASAP, minor within two sprints) and an org-wide lessons-learned report `[source: MS security-in-devops]`.
- **SAST / DAST / SCA** — static application security testing (OWASP source-code analysis tools, GitHub Advanced Security/CodeQL), dynamic testing, dependency/vulnerability scanning, secret scanning; **security checks as branch policies** in the PR pipeline (Microsoft: "doesn't violate any security or compliance policies") `[source: MS how-microsoft-develops-devops; MS security-in-devops]`.
- **Assume breach** — plan for detection and response: improve mean-time-to-detect and mean-time-to-recover; defense in depth; post-breach assessments of policies and adherence `[source: MS security-in-devops]`.
- **Security reviews for designs** — Google design docs carry dedicated security/privacy review `[source: industrialempathy]`.
- **Penetration testing and bug bounties** — external validation of defenses; Google's Vulnerability Rewards Program is the canonical bounty `[knowledge]`.
- **Secret management** — vaults (Azure Key Vault etc.), hierarchy of vaults, deploy-time vs run-time secrets `[source: MS security-in-devops]`.

### Artifacts produced
- Threat models, security review reports, pentest reports, SAST/DAST findings, security sign-offs, security backlog with SLAs, incident/breach reports, policy documents, training materials `[sources: OWASP; MS]`.

### Gates controlled
- **Security sign-off gate**: required before launch/release (critical vulnerabilities block).
- **CI/CD security gates**: fail builds on critical findings; signed builds `[source: MS]`.
- Can force-feature disablement via flag guards on discovered vulnerabilities `[knowledge]`.
- Vulnerability remediation SLAs (Sev-based) `[source: MS security-in-devops]`.

### Interactions
- Architect (threat model in design), Developers (remediation), Release Engineer (gates in pipeline), SRE (incident response, war games), PM (risk acceptance), Delivery Manager (security readiness at GO/NO-GO).

### Accountability
- Breaches → post-breach assessment; every real or practiced breach is "an opportunity to improve" `[source: MS security-in-devops]`.
- Unfixed high-severity findings block releases — the gate is enforced by the pipeline, not by persuasion `[source: MS]`.

---

## 12. Tech Writer / Documentation

*Synonyms: Technical Writer, Documentation Engineer, DevRel Docs, Information Developer (Microsoft legacy).*

### Core responsibilities
- Produce and maintain user documentation, API reference, design/conceptual docs, runbooks, release notes; ensure docs are correct, current, and usable.
- Google: engineers write most docs themselves, but dedicated technical writers own the hard cases; docs are treated like code — under source control, owned, reviewed, and updated `[source: SWE book ch10]`.

### Quality mechanisms
- **Docs-as-code (g3doc)** — docs live beside source, go through the same review workflow; Google's wiki (GooWiki) failed because docs lacked owners; moving docs into source control fixed it `[source: SWE book ch10]`.
- **"Write for your audience, not yourself"** — identify primary audiences, seekers vs stumblers, customers vs providers; docs framed by WHO/WHAT/WHEN/WHERE/WHY `[source: SWE book ch10]`.
- **Diátaxis four modes** — tutorials (learning), how-to guides (tasks), reference (information), explanation (understanding); each mode serves a distinct user need `[source: diataxis.fr]`.
- **Doc reviews** — technical, audience, and writing reviews; style guides (Google developer documentation style guide) `[source: SWE book ch10; knowledge]`.
- **Freshness and ownership** — freshness dates and named owners keep docs from rotting `[source: SWE book ch10]`.
- **Runbooks** — operationally critical docs (incident runbooks, deployment runbooks) validated in game days/DiRT `[source: SWE book ch14; knowledge]`.
- **API reference quality** — generated from contracts (OpenAPI) plus curated explanations; API review boards gate the APIs the docs describe `[source: dotnet APIReviewProcess; knowledge]`.
- **TL;DRs and landing pages** — each doc has "a singular purpose" `[source: SWE book ch10]`.

### Artifacts produced
- User guides, API reference, conceptual docs, tutorials, how-tos, runbooks, release notes, onboarding guides, READMEs, doc tests (docs that are executable) `[sources: SWE book ch10; diataxis]`.

### Gates controlled
- **Docs-complete gate**: if documentation is in the Definition of Done, missing docs block release readiness `[knowledge]`.
- Sign-off on user-facing content accuracy at launch `[knowledge]`.

### Interactions
- Developers (technical accuracy), SRE (runbooks), PM (feature docs), Support (escalation docs), Release Engineer (release notes), QA (docs verified against behavior).

### Accountability
- Documentation debt shows up as support load and user confusion; Google's "TL;DR" and freshness-with-owner norms make stale docs visible `[source: SWE book ch10]`.

---

## Cross-role quality mechanisms

### 13.1 Code review culture

- **Google's code review standard** (eng-practices): approve when the change "definitely improves the overall code health of the system" — not perfection; never approve changes that worsen code health except in emergencies; design is not style — "if the author can show several approaches are equally valid, the reviewer should accept the preference of the author"; non-mandatory comments are marked "Nit:"; the reviewer **owns** the code under review and can deny approval for any addition they don't want in the system; disagreements escalate: consensus → face-to-face → broader team/tech lead/EM — "don't let a CL sit around because the author and reviewer can't agree" `[source: eng-practices standard]`.
- **What reviewers check** (in order): design, functionality (edge cases, concurrency, UI demos), complexity ("too complex... can't be understood quickly"), tests (added in the same CL, verified by humans), naming, comments ("why" not "what"), style, consistency, documentation; review **every line**; "LGTM with comments" for partial reviews `[source: eng-practices looking-for]`.
- **Velocity norms**: respond within one business day; don't interrupt focused work; ask to split oversized CLs; "always unblock the developer" `[source: eng-practices speed]`.
- **Pushback etiquette**: genuinely consider whether the author is right; don't accept vague "I'll clean up later" promises — insist on cleanup now or file a bug with a TODO `[source: eng-practices pushback]`.
- **Microsoft's PR culture**: branch policies make review mechanical (build validation, owner sign-off, external checks); code review "picks up where the automated tests left off, and is particularly useful for spotting architectural problems"; reviewers are auto-added as code owners; optional expert reviewers for shared components `[source: MS how-microsoft-develops-devops]`.
- **Readability certification** (Google): a company-wide language certification; a third approval bit beside LGTM and OWNERS; authors with readability may self-approve style; owners usually have it — this is how review scales to a 50,000-engineer codebase `[source: SWE book ch08/09]`.

### 13.2 Definition of Done

- Scrum Guide (2020): the **Definition of Done is a formal commitment** — "a formal description of the state of the Increment when it meets the quality measures required for the product"; if a Product Backlog item doesn't meet the DoD, it cannot be released or even presented at the Sprint Review; the DoD is created by the Scrum Team (or inherited from the organization) and "may be enhanced over time"; no one may bypass it `[source: Scrum Guide]`.
- Organizational variants are checklist-driven: code reviewed and merged, tests pass (unit/integration/e2e), coverage thresholds met, no open P1/P2 defects, documentation updated, feature flag wired, rollback plan verified, security reviewed `[knowledge]`.
- Microsoft operationalizes DoD with the **bug cap** (`# engineers × 5`): if bugs exceed the cap, feature work stops — a hard, quantified quality contract `[source: MS how-microsoft-plans-devops]`.

### 13.3 Quality gates in CI/CD

- **Trunk-based development** (DORA capability with "strong positive correlation with good technical outcomes"): commit to trunk at least once per 24h, ideally multiple times a day; short-lived branches only for review+CI; feature flags and branch-by-abstraction for large changes `[source: trunkbaseddevelopment.com; SWE book ch16; dora.dev]`.
- **Mainline quality ("keep the build green")**: Google's presubmit runs fast reliable tests; post-submit runs broader suites via TAP; failed batches are bisected to the culprit; each team has a **Build Cop** who rolls back breaking changes; "green head" vs "true head" lets teams sync to stable `[source: SWE book ch23]`.
- **Static analysis as a merge gate**: Tricorder runs 100+ analyzers on 50,000+ review changes/day; checks must be actionable with <10% effective false positives (actual <5%); ERROR-level checks compile-block after cleanup; "Not useful" feedback disables bad analyzers `[source: SWE book ch20]`.
- **Branch policies** (Microsoft/Azure DevOps): required reviewers, build validation, status checks, enforced merge queue `[source: MS how-microsoft-develops-devops]`.
- **Deployment-stage gates**: pipeline approvals, health-check monitoring between rings, bake time, rollback triggers `[source: MS safe-deployment-practices]`.
- **DORA's counterintuitive finding**: heavyweight change-approval processes *reduce* quality; peer review + automated checks outperform change advisory boards `[source: dora.dev]`.

### 13.4 Release readiness reviews / release trains

- **Google release trains**: fixed cadence with hard deadlines; "if you're late for the train, it leaves without you"; small frequent releases (Search: every other day) lower risk; release candidates from green builds; canary + staged rollout; rollback/rollforward with flag guards `[source: SWE book ch24]`.
- **.NET Shiproom** (Microsoft): the documented release review body — twice-weekly, cross-stack stakeholders, template-driven servicing PRs, labeled decisions (`servicing-approved`, `servicing-more-info`, rejected), criteria-based "servicing bar" `[source: dotnet Servicing.md]`.
- **Milestone reviews**: Microsoft's synch-and-stabilize tradition — daily builds, milestone go/no-go reviews, buffer time at the end of the cycle `[knowledge: Microsoft Secrets (Cusumano & Selby, 1995)]`.
- **Release trains in SAFe**: train-level PI planning, integration demos, Release Train Engineer `[knowledge]`.
- **SRE input**: error budget state is part of the release decision; releases are the primary consumer of the budget `[source: SRE book ch3]`.

### 13.5 Retrospectives and continuous improvement loops

- Scrum: the **Sprint Retrospective** inspects the last Sprint "regarding individuals, interactions, processes, tools, and their Definition of Done" and produces an improvement plan; it is the team's quality loop `[source: Scrum Guide]`.
- Microsoft: metrics are reviewed "at the highest leadership levels" every six weeks (health, business, scenarios, customer telemetry); teams adjust backlogs from usage metrics `[source: MS how-microsoft-delivers-devops]`.
- Google: postmortems and LSC retrospectives feed process improvement; the eng-practices docs themselves evolve from experience `[source: SWE book ch22; eng-practices]`.
- DORA: measurement (the five metrics) is itself the improvement loop — teams track and trend them `[source: dora.dev]`.

### 13.6 Incident postmortems (blameless culture)

- Google SRE: **blameless postmortems** — every significant incident gets one; focus on systems and processes, not individuals; postmortems produce action items tracked to closure `[knowledge: SRE book ch15 — "Postmortem Culture: Learning from Failure"]`.
- Amazon: **COE (Correction of Errors)** — the internal postmortem process with a structured write-up and executive review `[knowledge]`.
- Microsoft: live-site culture with hotfix process; incidents drive the "change in frequency of incidents" metric; war games treat every practiced breach as a learning event `[source: MS how-microsoft-operates-devops; security-in-devops]`.
- The point of blamelessness: if people fear punishment they hide problems; postmortem quality is measured by whether action items actually land `[knowledge]`.

---

## Synthesis: gates by role

| Role | Can block / gate | Key quality artifact | Primary quality mechanism |
|---|---|---|---|
| Software Engineer | Peer merges (review), own code blocked by review | CL/PR + tests | Precommit review, tests in same CL, presubmit checks |
| Tech Lead | Merges in owned dirs (OWNERS), design docs | Design docs, ADRs, OWNERS | Design review, readability mentoring, debt control (bug cap) |
| Architect | Architecture sign-off, API compatibility, tech choice | ADRs, NFRs, contracts | ATAM evaluation, ADR decision log, API review board |
| QA / SDET | Merge gate (tests), release test sign-off | Test strategy, suites, dashboards | Test pyramid, hermetic tests, flakiness control (~0.15%) |
| Test Engineer | Exit criteria, UAT sign-off | Test plan, cases, RTM | ISTQB process, traceability matrix, risk-based testing |
| PM / Scrum Master | Scope gate, sprint commitment, impediment escalation | Sprint plan, risk register, status report | Sprint ceremonies, bug cap, RAID log |
| Product Manager | Backlog gate, acceptance criteria, SLO tolerance | PRFAQ/PRD, acceptance criteria, OKRs | Working Backwards, outcome metrics, error budget input |
| Release Engineer / DevOps | Pipeline gates, release freeze, environment access | Pipelines, runbooks, rollback plans | Release trains, rings/bake time, IaC, DORA metrics |
| Delivery Manager | **GO/NO-GO**, release readiness, stakeholder sign-off | Shiproom records, readiness checklist | Shiproom, milestone reviews, sign-off matrix |
| SRE | Release freeze via error budget, prod-readiness | SLOs, error budget, postmortems | SLI/SLO/error budget, on-call, capacity planning |
| Security Engineer | Security sign-off, CI/CD security gates | Threat models, pentest reports | Threat modeling (STRIDE), SDL, SAST/DAST, war games |
| Tech Writer | Docs-complete gate (if in DoD) | Docs-as-code, runbooks | Diátaxis, docs review, freshness/owners |

**Cross-cutting conclusion for loop-engine:** a governance system should model quality as a set of *role-owned gates*, each with named ceremonies (review, design doc review, shiproom, GO/NO-GO, postmortem), durable artifacts (ADRs, test plans, SLOs, readiness checklists), and measurable consequences (error budgets, bug caps, DORA metrics, flakiness targets). The most robust organizations make gates *mechanical where possible* (pipeline checks, branch policies, presubmit analyzers) and *social where judgment is needed* (code review, design review, shiproom) — with clear escalation paths in both.

---

## Source register

### Verified online (fetched 2026-07-31)
1. Google Engineering Practices (eng-practices) — review standard, what to look for, speed, pushback, small CLs, handling comments — https://github.com/google/eng-practices (raw: google.github.io/eng-practices)
2. "Software Engineering at Google" (Winters, Manshreck, Wright, 2020), free HTML — ch8 Style Guides, ch9 Code Review, ch10 Documentation, ch11 Testing Overview, ch14 Larger Testing, ch16 Version Control & Branch Management, ch20 Static Analysis, ch22 Large-Scale Changes, ch23 Continuous Integration, ch24 Continuous Delivery — https://abseil.io/resources/swe-book/html/
3. Google SRE Book — ch3 Embracing Risk, ch4 Service Level Objectives, ch8 Release Engineering (via public mirror of the book text; original at sre.google/sre-book) — https://sre.google/sre-book/
4. Design Docs at Google (Malte Ubl, industrialempathy.com) — https://www.industrialempathy.com/posts/design-docs-at-google/
5. Microsoft Learn DevOps Resource Center — How Microsoft plans/develops/delivers/operates with DevOps; Safe deployment practices; Security in DevOps — https://learn.microsoft.com/en-us/devops/
6. .NET / ASP.NET Core docs — Servicing process with Shiproom template and servicing bar; API review process — https://github.com/dotnet/aspnetcore/blob/main/docs/Servicing.md
7. DORA (DevOps Research & Assessment) — metrics guide and capability catalog — https://dora.dev/
8. Scrum Guide (2020) — Definition of Done, accountabilities, events — https://scrumguides.org/scrum-guide.html
9. OWASP Threat Modeling — https://owasp.org/www-community/Threat_Modeling
10. Trunk-Based Development — https://trunkbaseddevelopment.com/
11. ADR (Architecture Decision Records) — https://adr.github.io/
12. Diátaxis documentation framework — https://diataxis.fr/
13. Martin Fowler — TestPyramid — https://martinfowler.com/bliki/TestPyramid.html
14. SEI (CMU) — ATAM (page reachable; details from established SEI material) — https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-atam/
15. Amazon PRFAQ template (structure of a PRFAQ: press release + customer FAQ, 4–6 pages) — GitHub template repositories (e.g., thinkbigleaders/claude-innovation-skills)

### Established practice references (knowledge-based, standard public documentation)
16. Google SRE book ch14 Managing Incidents, ch15 Postmortem Culture (blameless postmortems), ch5 Toil, ch26 Capacity Planning; SRE Workbook error-budget policies
17. ISTQB Certified Tester Foundation Level syllabus (test process, test levels, black-box/white-box techniques, exit criteria); IEEE 829 test documentation; IEEE/ISO 42010 architecture description
18. Cusumano & Selby, "Microsoft Secrets" (1995) — synch-and-stabilize, milestone reviews, daily builds
19. Bryar & Carr, "Working Backwards" (2021) — Amazon PRFAQ process, six-pagers, single-threaded owners; Amazon COE postmortems
20. Microsoft SDL (Security Development Lifecycle); STRIDE threat model (Microsoft); OWASP SAMM
21. PMI PMBOK (scope/risk/RAID/status reporting); SAFe (release trains, PI planning, WSJF); XP/agile (TDD, pair programming, velocity); Mike Cohn test pyramid; "Testing at the Speed and Scale of Google"; Google developer documentation style guide; ThoughtWorks Technology Radar; ITIL change management (as the legacy model DORA argues against)
