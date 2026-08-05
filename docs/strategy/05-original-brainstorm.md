# All Things Agentic Hackathon — Brainstorm: Collaborative Partner Track

**Contest:** All Things Agentic Hackathon (Google/Devpost) · Deadline Aug 31, 2026, 5pm PT
**Scope for this brainstorm:** domain-agnostic, focused on **Collaborative Partner**, solo/duo build, limited time.

---

## 1. What the track actually requires

**Collaborative Partner** (from the rules): *"Create an agent that guides users interactively. It must ask clarifying questions, guide the user step-by-step, and have a clear way to capture feedback, so it constantly adapts to the user's unique way of thinking."*

Judging weights: Innovation & Operational Utility 40% ("does it eliminate real-world friction? is the Twist present?"), Architectural Discipline & Tech Stack 30%, Demo & Production Readiness 30% (4-min video showing it running on Google Cloud).

Mandatory tech: Gemini 3.5+, one Google agent framework (ADK / GenAI SDK / Antigravity SDK / GenKit), one Google Cloud infra service (Cloud Run, Cloud SQL, Firestore, GKE, Pub/Sub).

## 2. What Google already ships (so we don't rebuild it)

| Shipped thing | What it already does |
|---|---|
| **Agent Memory Bank** (GEAP) | Automatically extracts and retrieves personalized user info across sessions — the exact "remembers your preferences over time" mechanic. |
| **Agent Registry** (GEAP) | Centralized catalog/discovery of agents — not directly relevant to this track. |
| **Agent Runtime** | Managed hosting for long-running (up to 7-day) async agents. |
| **Agent Gateway / Identity + Model Armor** | Access control, prompt-injection/PII-leak protection. |
| **Gemini Deep Research Agent** (Agent Garden sample) | A prebuilt guided-research/Q&A agent — closest analog to a generic "asks clarifying questions to help you research something" idea. |
| **Google Workspace "Help me write" / Gemini in Docs** | Adaptive writing assistance inside docs — closest analog to a generic "AI drafting assistant" idea. |

**Implication:** Memory Bank means *cross-session personalization by itself is infrastructure, not a differentiator* — it's fine (expected, even) to build on it, but the pitch can't rest on "it remembers you." The idea needs a twist Memory Bank doesn't give you for free: real action/writeback, a judgment call on *when to stop and ask*, or institutional memory that outlives one user.

---

## 3. Candidate ideas (Collaborative Partner)

| # | Idea | One-line | Effort |
|---|---|---|---|
| 1 | **Ledger** — decision co-pilot that writes ADRs | Socratic clarifying-question loop that turns a messy technical decision conversation into a committed Architecture Decision Record in your repo — and refuses to finalize until the key risks are actually resolved. | Medium |
| 2 | **Scope Partner** — client/SOW intake agent | Adaptive intake interview for freelancers/consultants that adjusts question depth to the client's inferred risk profile and outputs a usable SOW. | Medium |
| 3 | **Onboarding Buddy** — shared learning-graph tutor | Calibrates depth to what a new hire already knows, and writes back a durable "curriculum state" graph the next hire's agent can also read. | Medium-High |
| 4 | **Deal Prep** — sales negotiation partner | Asks a rep clarifying questions about an upcoming renewal/pricing negotiation, drafts a scenario tree, and refuses to hand over a script until deal-specific risk is resolved; explicit feedback ("didn't land with this customer type") reshapes future prep. | Low-Medium |
| 5 | **The Refuser** — uncertainty-first meta-agent | A wrapper pattern: instead of guessing, it surfaces exactly what it doesn't know as targeted questions, and the user teaches it thresholds over time ("always ask about X, never about Y"). | Low (but abstract — needs a host task to be demoable) |
| 6 | **Skill Coach** — career/learning planner | Clarifies goals/constraints, builds an adaptive plan, adjusts on explicit "that didn't work" feedback. | Low |

*(Ideas 1 and 4 both incorporate #5's "refuse until resolved" mechanism rather than shipping it standalone — it's a strong differentiator but too abstract to demo alone in 4 minutes.)*

---

## 4. Audit against shipped features

| # | Closest shipped thing | Classification | Twist needed / already present |
|---|---|---|---|
| 1 Ledger | Gemini in Docs / generic AI drafting assistants | ⚠️ → ✅ with twist | Twist present: real writeback (commits an actual file to the repo, not just chat text) + refusal-until-resolved (negative case) + institutional memory (the ADR outlives the session). |
| 2 Scope Partner | Generic AI intake-form fillers | ⚠️ | Needs: question depth must visibly change based on inferred client risk, not just fill blanks — otherwise reads as a form wizard. |
| 3 Onboarding Buddy | Generic onboarding chatbots / internal wikis | ✅ | Clean gap — the cross-user shared graph writeback is the institutional-memory differentiator; nothing shipped does this. |
| 4 Deal Prep | Generic sales-coaching chatbots | ⚠️ → ✅ with twist | Twist present: refusal mechanism + feedback that visibly reshapes the *next* session (not just "remembers a fact") — action/judgment beats generic advice-giving. |
| 5 The Refuser | N/A (a pattern, not a product) | ✅ but too abstract standalone | Fold into #1 or #4 rather than building alone. |
| 6 Skill Coach | Many existing AI career-coach products | ❌ | No credible twist found — drop. |

---

## 5. Scoring (survivors)

| # | Idea | Effort (fits solo/duo timeline) | Originality | Platform depth | Notes |
|---|---|---|---|---|---|
| 1 | Ledger | 4/5 | 4/5 | 4/5 | Real GitHub/repo writeback demos cleanly; ADK multi-turn state + Memory Bank for style adaptation + Firestore for session state. Falls back gracefully if live demo hiccups (show the already-committed ADR). |
| 4 | Deal Prep | 5/5 | 3/5 | 3/5 | Easiest to demo live (a real back-and-forth reads well on camera), narrower tech surface, but "operational utility" story is a bit softer unless framed tightly around a real enterprise workflow (renewals/pricing). |
| 3 | Onboarding Buddy | 2/5 | 4/5 | 4/5 | Strongest differentiation story (institutional memory), but the multi-agent shared-graph piece is the kind of thing that quietly eats a week solo. Risky for "limited time." |
| 2 | Scope Partner | 3/5 | 2/5 | 3/5 | Workable but the twist is the weakest of the four — closest to "form wizard with extra steps" if not executed carefully. |

**Ranking for solo/duo + limited time: Ledger (1) > Deal Prep (4) > Onboarding Buddy (3) > Scope Partner (2).**

---

## 6. Edge check on the top pick (Ledger)

- **Vs. a generic coding agent:** Ledger's output isn't code — it's a *decision*, captured with rationale and the risks that were actually resolved in conversation. A coding agent pointed at the same repo has no access to the human reasoning that produced the decision; Ledger's clarifying-question transcript *is* the differentiator.
- **Vs. a chatbot:** It doesn't just answer — it refuses to close out the ADR until specific risk fields are filled, and it writes back a durable artifact (a real commit) unprompted by a second ask. That's acting, not just responding.
- **Vs. Gemini in Docs / shipped writing assistants:** Those help you *write text*; Ledger's mechanism is *refusal + structured extraction + repo writeback*, not prose generation.
- **One-sentence differentiation claim:** *Ledger doesn't draft your decision doc for you — it interrogates you until you actually have a defensible decision, then commits it as an ADR your team will find later.*

---

## 7. Final pick: **Ledger**

**One-paragraph pitch:** Ledger is a Collaborative Partner agent for engineering teams making a real technical decision (framework choice, migration strategy, API contract). Instead of generating a decision doc from a one-line prompt, it runs a Socratic clarifying-question loop — asking about constraints, alternatives considered, and specific risks — and explicitly *refuses* to finalize the record until the risk fields are actually answered, not guessed. Feedback on past ADRs (via Memory Bank) adapts how deep it probes for that team over time — a team that always documents rollback plans gets asked about rollback by default; one that never cares about vendor lock-in stops being asked. When the conversation converges, Ledger writes a properly formatted ADR directly to the repo as a real commit (or PR), giving the team a durable, discoverable artifact the next engineer — human or agent — can actually find.

**Differentiation claim (one sentence):** Ledger doesn't draft your decision doc for you — it interrogates you until you actually have a defensible decision, then commits it as an ADR your team will find later.

**Biggest risk to flag before building:** the "adapts to the user's unique way of thinking" judging language needs to be *visibly* demoed in 4 minutes — show two short sessions back-to-back where the second one's questions are visibly different because of stored feedback from the first, or a judge has to take the adaptation on faith.

---

## Appendix: quick alternate-track sketches (if you reconsider the track choice)

- **Taskmaster:** an agent that closes the loop on stale cloud infra — finds orphaned/idle GCP resources, drafts and (with approval) executes the teardown, logging cost saved. Real action beats a reporting dashboard.
- **Fortified Enterprise Fleet:** heavy overlap with GEAP's own Agent Registry/Gateway/Observability — hardest track to differentiate on without out-building Google's own platform team; not recommended for solo/duo.

---

## 8. Final scoping call: solo hobbyist, a few evenings/weekend

You flagged interest in both **Collaborative Partner** and **Fortified Enterprise Fleet**, and a real build budget of just a few evenings/a weekend. On that budget, pick **Collaborative Partner only** — here's why, directly:

- **Fortified Enterprise Fleet's own submission bar is production infrastructure**, not a feature: agent discovery/cataloging, zero-trust access control, policy enforcement, prompt-injection/PII guardrails, and OpenTelemetry-compliant audit logging — *all required, not optional, per the rules*. That's a multi-week team build even before you get to differentiating it from GEAP's own Agent Registry, Agent Gateway, and Agent Observability, which already ship exactly these capabilities. A few evenings gets you a thin wrapper around Google's own platform, which is the single worst outcome on the "Innovation" criterion (40% of the score). Drop it for this budget.
- **Collaborative Partner scales down cleanly** to a single evening-sized core loop: one Gemini-backed multi-turn conversation (ADK), one narrow decision type, one real write-back action, deployed on Cloud Run. That's a complete, honestly-scoped submission rather than a half-built enterprise platform.

**Re-scoped Ledger, sized for a few evenings (domain-agnostic):**
Drop the team-adaptation/Memory Bank piece — that's the part most likely to eat a whole evening on its own for marginal demo value at this size. Keep only:
1. A single ADK conversational loop that asks 3–5 targeted clarifying questions about *one* concrete decision (e.g., "should we use library A or B for X").
2. A hard rule: it will not produce the final output until every risk field has a real answer — if the user tries to skip, it pushes back once, concretely (this is the "Twist" a judge can see in 30 seconds).
3. One real write-back: format the resolved decision as a markdown ADR and commit it to a GitHub repo via the API (or open a PR) — this is the one integration worth spending an evening on, since "did it actually take action" is exactly what separates Collaborative Partner from a chatbot.
4. Skip persistent cross-session memory entirely for the submission; if there's time left, a hardcoded two-session demo (canned "session 1" then "session 2 asks differently because of noted feedback") sells the adaptation claim without needing a real learning system.

This keeps all three required tracks' pieces (Gemini 3.5, ADK, Cloud Run) while cutting everything that doesn't demo in under 4 minutes.
