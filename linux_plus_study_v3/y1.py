# Create two markdown templates for the user: a printable checklist and a Notion-friendly template.
from pathlib import Path

base = Path(".")

printable = base / "Vibe-Coding-Checklist-PRINT.md"
notion = base / "Vibe-Coding-Template-NOTION.md"

printable_content = """# Vibe Coding — Big Project Checklist (Printable)

*Use: pick any 3–5 questions per session. Keep answers short and decisive. Repeat daily.*
  
**Project:** ____________________________    **Date:** ____________________  
**Session Goal (1 sentence):** _______________________________________________________  
**Timebox:** ☐ 25m ☐ 50m ☐ 90m ☐ Other: __________

---

## Daily Five (pick and answer before you start)
1. ______________________________________________________
2. ______________________________________________________
3. ______________________________________________________
4. ______________________________________________________
5. ______________________________________________________

---

## North Star
- [ ] What am I actually shipping in one sentence?  
  → ______________________________________________________
- [ ] Who uses it first, and what’s the first “wow” moment?  
  → ______________________________________________________
- [ ] What’s the smallest end-to-end path I can make work today?  
  → ______________________________________________________
- [ ] What must be true for me to call this day a win?  
  → ______________________________________________________
- [ ] If the project disappeared tomorrow, what value would be missed?  
  → ______________________________________________________

## Scope & Constraints
- [ ] What’s explicitly out of scope for v1? → ______________________________________
- [ ] Hard limits (time/mem/CPU/budget/team)? → _____________________________________
- [ ] Which external systems/APIs can’t move for me? → ______________________________
- [ ] Day-one vs month-six data sizes? → ____________________________________________
- [ ] What can I mock/stub safely right now? → ______________________________________

## Architecture & Boundaries
- [ ] Natural domains/modules? → ____________________________________________________
- [ ] Strict vs relaxed boundaries? → _______________________________________________
- [ ] What must be sync vs async/evented? → _________________________________________
- [ ] Where does state live; who owns it? → _________________________________________
- [ ] One diagram I should draw today: ______________________________________________

## Data & State
- [ ] Canonical models & lifecycles? → ______________________________________________
- [ ] Fields that are stable contracts? → ___________________________________________
- [ ] Migration story if schema evolves? → __________________________________________
- [ ] Cache strategy & invalidation? → ______________________________________________
- [ ] Invariants that must never break? → ___________________________________________

## Interfaces & Contracts
- [ ] Simplest public API shape? → _________________________________________________
- [ ] Guarantees (idempotency, ordering, timeouts)? → _______________________________
- [ ] Versioning/deprecation plan? → ________________________________________________
- [ ] Error types callers rely on? → ________________________________________________
- [ ] Test double (mock/fake) for this contract? → __________________________________

## Execution & Concurrency
- [ ] Parallelizable work? → ________________________________________________________
- [ ] Backpressure/rate limiting needed? → __________________________________________
- [ ] Contention hotspot under load? → ______________________________________________
- [ ] Retries (with jitter)? Circuit breaker? → _____________________________________
- [ ] Graceful shutdown path? → _____________________________________________________

## Errors, Logging, Observability
- [ ] Acceptable vs catastrophic failures? → ________________________________________
- [ ] Log at INFO/WARN/ERROR? → ____________________________________________________
- [ ] Metrics/SLIs (latency, error %, queue depth)? → _______________________________
- [ ] “Trace one user’s path” plan? → _______________________________________________
- [ ] Reproduce prod locally how? → _________________________________________________

## Performance & Scale
- [ ] Slow path I can avoid building? → _____________________________________________
- [ ] Which paths must be O(1) or O(log n)? → ______________________________________
- [ ] Top 3 perf hypotheses to validate? → _________________________________________
- [ ] Where to batch/stream/precompute? → __________________________________________
- [ ] Max tolerable p95 latency (core actions)? → ___________________________________

## Security & Privacy
- [ ] Untrusted inputs & validation? → ______________________________________________
- [ ] Secrets: where do they live? → ________________________________________________
- [ ] Least privilege / sandboxing? → ______________________________________________
- [ ] Personal data stored—can I avoid it? → ________________________________________
- [ ] Audit trail for sensitive actions? → __________________________________________

## Tooling & Dev-Ex
- [ ] Build/run/test in one command? → _____________________________________________
- [ ] Minimal scaffolding that removes friction? → __________________________________
- [ ] Codegen/templates to keep consistent? → _______________________________________
- [ ] Style/lint rules to catch my mistakes? → ______________________________________
- [ ] Local fixtures/test data for speed? → _________________________________________

## Testing Strategy
- [ ] One high-value integration test? → ___________________________________________
- [ ] Pure functions needing tight unit tests? → ____________________________________
- [ ] Property/fuzz testing targets? → _____________________________________________
- [ ] Golden-path e2e test in CI? → ________________________________________________
- [ ] Flaky test signal & quarantine plan? → ________________________________________

## Migration & Compatibility
- [ ] Feature flags or shadow mode? → ______________________________________________
- [ ] Write-through/read-old pattern? → ____________________________________________
- [ ] Rollback without data loss? → ________________________________________________
- [ ] Safe first schema change? → _________________________________________________
- [ ] Telemetry that says “flip the switch”? → ______________________________________

## Docs & Naming
- [ ] Micro-README to write now: ____________________________________________________
- [ ] Names to clarify up front: ____________________________________________________
- [ ] Glossary terms to define once: _______________________________________________
- [ ] Example snippet to unlock a new contributor: __________________________________
- [ ] “Why it’s like this” note: ___________________________________________________

## Collaboration & Review
- [ ] Smallest reviewable slice? → _________________________________________________
- [ ] PR description context required? → ___________________________________________
- [ ] Split mechanical vs semantic PRs? → __________________________________________
- [ ] Who must sign off risky areas? → _____________________________________________
- [ ] Rollback/kill-switch tied to this PR? → ______________________________________

## Risk & Unknowns
- [ ] Riskiest assumption & 90-min spike? → ________________________________________
- [ ] What hurts most to change later? → ___________________________________________
- [ ] Cheapest experiment this week? → _____________________________________________
- [ ] “Stop digging” signal? → _____________________________________________________
- [ ] Plan B? → ____________________________________________________________________

## Refactoring & Debt
- [ ] Acceptable smells vs landmines? → ____________________________________________
- [ ] Refactor that halves future complexity? → ____________________________________
- [ ] Where to add seams (ports/adapters)? → _______________________________________
- [ ] TODO that deserves timestamp & owner? → _______________________________________
- [ ] Tests required before refactor? → ____________________________________________

## Release & Operate
- [ ] Release artifact & build path? → _____________________________________________
- [ ] Health checks & readiness gates? → ___________________________________________
- [ ] Runbook for common pages/alerts? → ___________________________________________
- [ ] Feature-flag dangerous bits? → _______________________________________________
- [ ] “Healthy 10 min after deploy” signals? → _____________________________________

## Giant-File Sanity (Thousands of LOC)
- [ ] Logical regions with headers/markers? → ______________________________________
- [ ] Split by responsibility without cycles? → ____________________________________
- [ ] 3–5 public functions, rest internal? → _______________________________________
- [ ] Code map at top explaining sections? → _______________________________________
- [ ] Editor tooling (symbols/folds/tags) set up? → _________________________________

---

## End-of-Day Reflection (5 minutes)
- Biggest win: _________________________________________________________________
- Biggest surprise: ____________________________________________________________
- What to do first tomorrow: ___________________________________________________

"""

notion_content = """# Vibe Coding — Big Project Template (Notion/Markdown)

**How to use**
- Duplicate this page per project.
- Before each session, check 3–5 prompts below and jot quick answers.
- Properties you may add in Notion: `Status`, `Milestone`, `Owner`, `Risk (Low/Med/High)`, `Confidence (0–100%)`, `Complexity (S/M/L)`

---

## Session Header
- **Date:**  
- **Session goal (1 sentence):**  
- **Timebox:** 25m / 50m / 90m / Other  

### Daily Five (choose and answer)
- [ ] ______________________________________________________
- [ ] ______________________________________________________
- [ ] ______________________________________________________
- [ ] ______________________________________________________
- [ ] ______________________________________________________

---

## North Star
- [ ] What am I actually shipping in one sentence?
- [ ] Who uses it first, and what’s the first “wow” moment?
- [ ] What’s the smallest end-to-end path I can make work today?
- [ ] What must be true for me to call this day a win?
- [ ] If the project disappeared tomorrow, what value would be missed?

## Scope & Constraints
- [ ] What’s explicitly out of scope for v1?
- [ ] Hard limits (time/memory/CPU/budget/team)?
- [ ] Which external systems/APIs can’t move for me?
- [ ] Day-one vs month-six data sizes?
- [ ] What can I mock/stub safely right now?

## Architecture & Boundaries
- [ ] Natural domains/modules?
- [ ] Where do boundaries need to be strict vs relaxed?
- [ ] What must be synchronous vs async/evented?
- [ ] Where does state live, and who owns it?
- [ ] One diagram to draw today.

## Data & State
- [ ] Canonical data models and lifecycles.
- [ ] Fields that are user-facing contracts.
- [ ] Migration story if schema evolves.
- [ ] Cache strategy and invalidation.
- [ ] Invariants that must never be broken.

## Interfaces & Contracts
- [ ] Simplest public API shape.
- [ ] Guarantees (idempotency, ordering, timeouts).
- [ ] Versioning / deprecation plan.
- [ ] Error types callers rely on.
- [ ] Test double (mock/fake) for this contract.

## Execution & Concurrency
- [ ] Safe parallelism?
- [ ] Backpressure/rate limiting?
- [ ] Contention hotspot if load spikes?
- [ ] Retries (with jitter) / circuit breaker?
- [ ] Graceful shutdown path.

## Errors, Logging, Observability
- [ ] Acceptable vs catastrophic failures.
- [ ] What to log at INFO/WARN/ERROR.
- [ ] Metrics/SLIs (latency, error %, queue depth).
- [ ] Plan to trace a single user’s path.
- [ ] How to reproduce prod issues locally.

## Performance & Scale
- [ ] Slow path to avoid building.
- [ ] Code paths that must be O(1) or O(log n).
- [ ] Top 3 performance hypotheses to validate.
- [ ] Where to batch/stream/precompute.
- [ ] Max tolerable p95 latency for core actions.

## Security & Privacy
- [ ] Untrusted inputs & validation.
- [ ] Secrets inventory and storage.
- [ ] Least privilege / sandboxing candidates.
- [ ] Personal data stored—can it be avoided?
- [ ] Audit trail for sensitive actions.

## Tooling & Dev-Ex
- [ ] Build/run/test with one command.
- [ ] Minimal scaffolding to remove friction.
- [ ] Codegen/templates to keep consistent.
- [ ] Style/lint rules tuned to me.
- [ ] Local fixtures/test data.

## Testing Strategy
- [ ] One high-value integration test.
- [ ] Pure functions with tight unit tests.
- [ ] Property/fuzz testing targets.
- [ ] Golden-path e2e in CI.
- [ ] Flaky test signal & quarantine plan.

## Migration & Compatibility
- [ ] Feature flags/shadow mode.
- [ ] Write-through/read-old pattern.
- [ ] Rollback without data loss.
- [ ] Safe first schema change.
- [ ] Telemetry to flip the switch.

## Docs & Naming
- [ ] Micro-README now.
- [ ] Names to clarify.
- [ ] Glossary to define once.
- [ ] Example snippet for contributors.
- [ ] “Why it’s like this” note.

## Collaboration & Review
- [ ] Smallest reviewable slice.
- [ ] PR description context.
- [ ] Split mechanical vs semantic PRs.
- [ ] Required sign-offs.
- [ ] Rollback/kill-switch tied to the PR.

## Risk & Unknowns
- [ ] Riskiest assumption & 90-min spike.
- [ ] What hurts to change later.
- [ ] Cheapest experiment this week.
- [ ] “Stop digging” signal.
- [ ] Plan B.

## Refactoring & Debt
- [ ] Acceptable smells vs landmines.
- [ ] Refactor that halves future complexity.
- [ ] Add seams (ports/adapters).
- [ ] TODO with timestamp & owner.
- [ ] Tests required before refactor.

## Release & Operate
- [ ] Release artifact & build path.
- [ ] Health checks & readiness gates.
- [ ] Runbook for common pages/alerts.
- [ ] Feature-flag dangerous bits.
- [ ] “Healthy 10 minutes after deploy” signals.

## Giant-File Sanity (Thousands of LOC)
- [ ] Logical regions with headers/markers.
- [ ] Split by responsibility (no cycles).
- [ ] 3–5 public functions; rest internal.
- [ ] Code map at the top.
- [ ] Editor tooling (symbols/folds/tags).

---

## End-of-Day Reflection
- **Biggest win:**  
- **Biggest surprise:**  
- **First task tomorrow:**  
"""

printable.write_text(printable_content, encoding="utf-8")
notion.write_text(notion_content, encoding="utf-8")

print("Created files:")
print(printable)
print(notion)

