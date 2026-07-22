---
version: "1.0"
name: atlas
description: "ATLAS workflow: a 5-step methodology for building applications with AI assistance. Architect, Trace, Link, Assemble, Stress-test. Ensures apps are production-ready, not demos."
license: MIT
metadata:
  version: "1.0"
  origin: aetos
  inherited_by: gleipnir
  inheritance: near-verbatim
  amendments:
    - "Layer-2 caveat: ATLAS phase sequencing and gate caps are G-5 engine-controlled, not LLM-narrated; only the per-phase validation/report judgment is an LLM step."
    - "Plan-persistence discipline carried forward unchanged (aligns with Gleipnir plan-format requirement)."
---

> **GLEIPNIR INHERITANCE NOTE (read first).** This is the AETOS ATLAS v1.0
> skill inherited near-verbatim. ATLAS is a build methodology largely
> orthogonal to enforcement, so it copies cleanly — with one caveat carried
> in from the GOTCHA layer mapping. ATLAS maps **Stress-test → Orchestration**
> (see "GOTCHA Layer Mapping" below), and under G-5 the Orchestration layer is
> the deterministic engine, not the LLM. So: the validation-and-report
> *judgment* within Stress-test is an LLM step, but the *sequencing* of ATLAS
> phases and their gate caps is **engine-controlled, not LLM-narrated**. This
> is the same layer-2 collision resolved in GOTCHA Amendment 1. The caveat is
> marked inline with **[GLEIPNIR]**. ATLAS and GOTCHA are prerequisites to
> planning: run Architect/Trace before any plan is drafted.

# ATLAS Workflow

A 5-step process for building applications with AI assistance within the
GOTCHA framework. This workflow ensures apps are production-ready, not just
demos.

| Step | Phase | What You Do |
|---|---|---|
| **A** | Architect | Define problem, users, success metrics |
| **T** | Trace | Data schema, integrations map, stack proposal |
| **L** | Link | Validate ALL connections before building |
| **A** | Assemble | Build with layered architecture |
| **S** | Stress-test | Test functionality, error handling |

Optional production extensions:

- **V** -- Validate (security, input sanitisation, edge cases, unit tests)
- **M** -- Monitor (logging, observability, alerts)

---

## A -- Architect

**Purpose:** Know exactly what you are building before touching code.

### Questions to Answer

1. **What problem does this solve?**
   One sentence. If you cannot say it simply, you do not understand it.

2. **Who is this for?**
   A specific user. Not "everyone".

3. **What does success look like?**
   A measurable outcome. Not "it works".

4. **What are the constraints?**
   Budget (API costs), time (MVP vs full build), technical (must use X).

### Pre-Flight Checklist

Before designing, ensure operational readiness:

1. **Write the plan to disk** -- Persist the design document to
   `.gleipnir/plans/` (or the target project's `.opencode/plans/`)
   immediately. Chat-only designs are lost
   on compaction. The plan is the artifact, not the conversation. **Plan
   file writes are never blocked by read-only or plan mode -- writing a
   plan IS planning. Never defer this.** **[GLEIPNIR]** This discipline is
   carried forward unchanged; it aligns with Gleipnir's plan-format
   requirement (K-1).
2. **Initiate issue tracking** -- If working against a platform (GitLab,
   GitHub), create or assign the parent issue, create a milestone if scoped,
   and break the work into sub-issues before designing. The issue board
   should reflect the planned work before the first line of code.

### Output

```markdown
## App Brief
- **Problem:** [One sentence]
- **User:** [Who specifically]
- **Success:** [Measurable outcome]
- **Constraints:** [List]
```

The brief and any design documents must be written to disk (not only in chat).

---

## T -- Trace

**Purpose:** Design before building. This is where most projects fail.

### Data Schema

Define the source of truth BEFORE building:

```
Tables:
- users (id, email, name, created_at)
- items (id, user_id, title, content, source, created_at)
- metrics (id, user_id, platform, value, date)

Relationships:
- users 1:N items
- users 1:N metrics
```

### Integrations Map

List every external connection:

| Service | Purpose | Auth Type | Notes |
|---|---|---|---|
| Database | Storage | API Key / Connection string | |
| External API | Data source | OAuth / API Key | Rate limits? |
| Third-party | Feature X | API Key | MCP available? |

### Technology Stack Proposal

Based on requirements, propose:

- Database
- Backend
- Frontend
- Any other services needed

User approves or overrides before proceeding.

### Edge Cases

Document what could break:

- API rate limits
- Auth token expiry
- Database connection timeout
- Invalid user input
- Service unavailability

### Output

- Data schema diagram or markdown table
- Technology stack (approved by user)
- Integrations checklist
- Edge cases documented

---

## L -- Link

**Purpose:** Validate all connections BEFORE building. Nothing worse than
building for 2 hours then discovering the API does not work.

### Connection Validation Checklist

```
[ ] Database connection tested
[ ] All API keys verified
[ ] External services responding
[ ] OAuth flows working
[ ] Environment variables set
[ ] Rate limits understood
```

### How to Test

**Database:** Make a simple query. Should return data or empty result, not error.

**APIs:** Make a simple GET request. Verify response format matches expectations.

**Services:** List available operations. Test one simple operation.

### Output

All green checkmarks. If anything fails, fix it before proceeding.

---

## A -- Assemble

**Purpose:** Build the actual application with proper architecture.

### Architecture Layers

Follow GOTCHA separation:

1. **Frontend** -- UI components, user interactions, display logic
2. **Backend** -- API routes, business logic, data validation
3. **Database** -- Schema implementation, migrations, indexes

### Build Order

1. Database schema first
2. Backend API routes second
3. Frontend UI last

This order prevents building UI for data structures that do not exist.

### Component Strategy

- Use existing component libraries (do not reinvent buttons)
- Keep components small and focused
- Document any non-obvious logic

### Output

Working application with:

- Functional database
- API endpoints responding
- UI rendering correctly

---

## S -- Stress-test

**Purpose:** Test before shipping. This is the step most AI-assisted
development skips entirely.

### Functional Testing

```
[ ] All buttons do what they should
[ ] Data saves to database
[ ] Data retrieves correctly
[ ] Navigation works
[ ] Error states handled
```

### Integration Testing

```
[ ] API calls succeed
[ ] External service operations work
[ ] Auth persists across sessions
[ ] Rate limits not exceeded
```

### Edge Case Testing

```
[ ] Invalid input handled gracefully
[ ] Empty states display correctly
[ ] Network errors show feedback
[ ] Long text does not break layout
```

### User Acceptance

```
[ ] Solves the original problem
[ ] User can accomplish their goal
[ ] No major friction points
```

### Output

Test report with: what passed, what failed, what needs fixing.

---

## V -- Validate (Production Extension)

Add when the build is destined for production:

- Security audit (input sanitisation, auth, data exposure)
- Edge case hardening
- Unit and integration tests
- Dependency vulnerability scan

---

## M -- Monitor (Production Extension)

Add when the build is deployed:

- Structured logging
- Error tracking and alerting
- Performance metrics
- Uptime monitoring

---

## GOTCHA Layer Mapping

| ATLAS Step | GOTCHA Layer | Why |
|---|---|---|
| Architect | Goals | Define the process |
| Trace | Context | Reference patterns and data models |
| Link | Args | Environment setup and configuration |
| Assemble | Tools | Execution of deterministic work |
| Stress-test | Orchestration | AI validates and reports |

> **[GLEIPNIR — layer-2 caveat on Stress-test → Orchestration.]** Under G-5,
> Orchestration is the deterministic engine, not the LLM (see GOTCHA
> Amendment 1). The Stress-test *judgment* — "did this pass, what failed,
> what needs fixing" — remains an LLM step. But the *sequencing* of ATLAS
> phases (A→T→L→A→S) and their gate caps are enforced by the G-5 engine in
> code; the LLM does not decide when a phase is done or narrate the phase
> order. This keeps ATLAS's methodology intact while binding its composition
> to the enforcement layer.

---

## Anti-Patterns

These are mistakes to avoid:

1. **Building before designing** -- You end up rewriting everything
2. **Skipping connection validation** -- Hours wasted on broken integrations
3. **No data modelling** -- Schema changes cascade into UI rewrites
4. **No testing** -- Ship broken code, lose trust
5. **Hardcoding everything** -- No flexibility for changes

---

## Deployment

Deployment is **not part of this workflow**. It is a separate, user-initiated
action. When you are ready to deploy, explicitly ask. This keeps deployment
decisions in the user's control, not automated.
