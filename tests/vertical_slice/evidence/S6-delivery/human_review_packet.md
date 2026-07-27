# Phase Delivery Decision Packet — Delivery

**Packet ID:** HRP-VS-DELIVERY-001
**Generated:** 2026-07-22 16:00 UTC

## What We Did

We completed building the Simple Task Manager — a small web application that lets people create accounts and manage their personal to-do lists. The application has a login page, a task dashboard, and a detail page for each task. Users can register, log in, create tasks, update task status, and search their tasks.

The work went through quality checks and an initial review found three issues that needed attention: a security concern with how searches were handled, some missing checks on what information users could enter, and a structural issue with how the code was organized. All three issues have been fixed and verified.

## What Changed

Compared to the initial delivery attempt, we fixed three items:
1. A data safety issue — searches are now handled safely so that a harmful user cannot access information they should not see
2. Input checking — the system now verifies that information entered by users (like usernames and emails) follows expected rules before saving it
3. Code organization — the structure has been cleaned up so that each part of the system is independent, which makes future changes easier

These fixes were reviewed by safety experts, quality experts, and design experts. All checks now pass.

## Key Choices

### 1. How should the system handle task searches?

| We Chose | Did Not Choose | Why |
|----------|---------------|-----|
| A safe approach where the search terms are kept separate from the database instructions | Mixing the search terms directly into database instructions | Keeping data and instructions separate prevents safety issues |

**Why not the alternative:** Mixing user input directly into database instructions is like giving someone the keys to your filing cabinet instead of just the file they asked for. It is faster to write but much riskier.

**If we are wrong:** If our safe approach has a bug, searches might not work correctly. But the fix is simple and would not expose data.

### 2. How should the system check user input?

| We Chose | Did Not Choose | Why |
|----------|---------------|-----|
| Check every piece of information before saving it (username length, email format, password strength) | Accept whatever the user types without checking | Checking at the entrance prevents bad data from getting into the system |

**Why not the alternative:** Not checking input is like a restaurant serving any order without confirming it is on the menu — you end up with problems later. It seems faster at first but creates more work.

**If we are wrong:** If our checks are too strict, some valid information might be rejected. But we can easily adjust the rules.

### 3. How should the code modules be organized?

| We Chose | Did Not Choose | Why |
|----------|---------------|-----|
| Each module stands on its own; they communicate through a shared middle layer | Modules directly reference each other in both directions | Independent modules are easier to test, change, and reuse |

**Why not the alternative:** Two modules depending on each other is like two people each holding the other's keys — neither can act alone. It makes testing and future changes much harder.

**If we are wrong:** The shared middle layer adds a small amount of extra code, but it is worth the clarity and independence it provides.

## Main Risks

| Risk | Likelihood | Impact | What We Did |
|------|-----------|--------|-------------|
| A user could try to break in through the search box | Low (we have safeguards in place) | They could see or change data they should not access | We separated search terms from database instructions, and a safety tool confirmed the fix |
| Someone creates an account with garbled information | Medium (users make mistakes) | The database could fill with bad data, making reports unreliable | We added checks on username length, email format, and password strength |
| The code structure makes future changes difficult | Low (we reorganized it) | Adding new features would take longer and risk breaking existing ones | We reorganized the code so each part is self-contained |

- **Data safety concern** — *Analogy:* Like letting someone who asks for a specific file to instead give instructions to your filing system. We now keep the request and the filing system instructions separate.
- **Input checking gap** — *Analogy:* Like a form that accepts any scribble in the name field. We now have clear rules for what each field should look like.
- **Code structure issue** — *Analogy:* Like two neighbors who each have the only key to the other's house. Neither can get in without the other. We gave each their own key and a shared hallway.

## Quality Check

- All 18 automated checks pass
- Safety scanning tool reports no issues
- Code organization checker reports no problems
- All changes verified by an independent reviewer

## Who Reviewed This Work

- A safety expert (reviewed the search fix and password handling)
- A quality expert (reviewed the input checks)
- A design expert (reviewed the code organization)
- An independent reviewer (reviewed everything as a whole)
- A delivery manager (confirmed the package is ready)

## You Need to Decide

**Do you approve delivering the Simple Task Manager as it stands?**

- [ ] Approve — the application is ready
- [ ] Request changes — I want something adjusted
- [ ] Pause — I need time to think

**Our recommendation:** We recommend approving. All three issues found by the review process have been fixed and verified. The application does what was planned, and the quality checks all pass. If anything looks unclear, choose "Request changes" and tell us what to adjust.

Please decide by **2026-07-25**. If you have questions, your product manager can walk through each piece with you.
