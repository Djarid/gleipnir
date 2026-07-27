---
version: "1.2"
name: decision-frameworks
description: "Structured decision-making skill — a catalog of 10+ decision frameworks, 12 cognitive bias detectors, and automatic framework selection based on decision type. Integrates with the brainstorming workflow so the appropriate framework activates when a decision point is detected."
license: MIT
metadata:
  version: "1.2"
  origin: aetos
  inherited_by: gleipnir
  inheritance: near-verbatim
  amendments:
    - "This IS the spec's K-3 (decision-frameworks + bias-detector catalogue). Its Decision Analysis is the INPUT to the precept-10 convergence gate (brainstorm skill), never the decision. Bias warnings feed G-4c novelty/triage signal."
---

> **GLEIPNIR INHERITANCE NOTE (read first).** Inherited near-verbatim from AETOS
> (MIT, origin: aetos). This skill **is Gleipnir's K-3** ("decision-frameworks
> and bias-detector catalogue" named in the spec, Part K). Gleipnir binding
> (marked `[GLEIPNIR]` below): the `## Decision Analysis` this skill produces is
> the **input to the operator's convergence decision** (the brainstorm skill's
> Phase-4 precept-10 gate) — it frames options, applies a framework, and runs
> the bias detectors to produce a *recommendation*; it never **makes** the
> decision. A material design tradeoff analysed here must be surfaced to the
> operator to decide, not resolved by the agent. (The 12 bias detectors also
> feed the G-4c novelty/triage signal once the bus exists.)

# Decision Frameworks Skill

Use this skill when a task involves a **decision point** — a choice between
options, a tradeoff between approaches, or a prioritisation call. This skill
provides structured frameworks that turn vague "what should we do?" questions
into rigorous, documented analyses.

Load alongside `brainstorm` and `gotcha` during design exploration. When a
decision point is detected, consult the Framework Selection table (below) to
choose the right tool, then run the cognitive bias detectors against the analysis.

## When to Use

- Any decision with two or more viable options
- Prioritisation calls (what to build first, what to defer)
- Architectural tradeoffs with long-term consequences
- Risk assessment before committing to an irreversible path
- When you suspect a cognitive bias may be distorting the analysis

---

## Framework Catalog

Each framework follows a standard structure: **When to Use**, **Process Steps**,
and **Output Format**.

---

### 1. Reversibility Filter

#### When to Use

Apply as the **first step in any decision**. Classify the decision as a
"two-way door" (reversible) or "one-way door" (irreversible) before deciding
whether deeper analysis is warranted. Trivial reversible decisions should be
fast-tracked; irreversible decisions require the full catalog.

#### Process Steps

1. Ask: "If we choose this option and it turns out to be wrong, how expensive
   is it to undo?" (time, money, risk to other systems)
2. Apply the threshold: if reversal cost is low (hours/days of work, no data
   loss, no external commitment), classify as **Two-Way Door**.
3. If reversal cost is high (data migration, external API lock-in, public
   commitments, significant re-architecture), classify as **One-Way Door**.
4. Two-Way Door → fast-track: make a quick choice and move forward.
5. One-Way Door → apply a deeper framework (see Framework Selection table below).

#### Output Format

```
Reversibility: [Two-Way Door | One-Way Door]
Reversal cost: <description of what undoing this decision would require>
Recommendation: [Fast-track | Apply deeper analysis]
Next framework: <framework name if One-Way Door>
```

---

### 2. Weighted Decision Matrix

#### When to Use

Use when comparing **3 or more options** across multiple criteria and you need
an objective score to guide the decision. Good for complex comparisons
where gut feel is insufficient.

#### Process Steps

1. List all options (columns) and all evaluation criteria (rows).
2. Assign a weight (0–10) to each criterion based on its relative importance.
3. Score each option against each criterion (0–10).
4. Multiply score × weight for each cell.
5. Sum the weighted scores per option.
6. The highest total score is the recommended option — document why if you
   deviate from it.

#### Output Format

```
| Criterion       | Weight | Option A | Option B | Option C |
|-----------------|--------|----------|----------|----------|
| <criterion 1>   | <w>    | <s×w>    | <s×w>    | <s×w>    |
| <criterion 2>   | <w>    | <s×w>    | <s×w>    | <s×w>    |
| **Total**       |        | <sum A>  | <sum B>  | <sum C>  |

Recommended: Option <X> (score: <N>)
Caveats: <any criteria where the winner scores poorly that matter>
```

---

### 3. Hypothesis-Driven Analysis

#### When to Use

Use when the decision involves **uncertainty about facts** — when you need to
validate assumptions before committing to a path. Good for novel technical
decisions where evidence is thin.

#### Process Steps

1. Frame each option as a **hypothesis**: "If we choose X, then Y will happen
   because Z."
2. Identify the key assumption embedded in each hypothesis.
3. For each assumption, list evidence for and evidence against.
4. Rate confidence in each hypothesis (Low / Medium / High).
5. Identify what experiment or spike would increase confidence.
6. Select the hypothesis with the best evidence/confidence profile, or run
   the spike before deciding.

#### Output Format

```
Hypothesis A: If we <option>, then <outcome> because <mechanism>.
  Key assumption: <assumption>
  Evidence for: <list>
  Evidence against: <list>
  Confidence: [Low | Medium | High]
  Validation: <spike or experiment to increase confidence>

Hypothesis B: (same structure)

Recommended: Hypothesis <X> — confidence <level>
Rationale: <why this hypothesis has the best evidence profile>
```

---

### 4. Pre-Mortem

#### When to Use

Use for **high-stakes or irreversible decisions** where you want to stress-test
a chosen path before committing. Assume the decision failed — work backward to
find failure modes. Pairs well with the Reversibility Filter for One-Way Door
decisions.

#### Process Steps

1. State the chosen option clearly.
2. Fast-forward to 6 months (or the relevant horizon) and assume: "We chose
   this option, and it was a failure."
3. Brainstorm all the ways it could have gone wrong (aim for at least 5).
4. For each failure mode, assess likelihood (Low/Medium/High) and impact
   (Low/Medium/High).
5. Identify the top 2–3 risks and define mitigations.
6. Decide: do the mitigations adequately cover the top risks? If not, reconsider
   the decision.

#### Output Format

```
Pre-Mortem: <chosen option>
Assumed outcome: FAILURE (at <time horizon>)

Failure modes:
| # | Failure Mode | Likelihood | Impact | Mitigation |
|---|--------------|------------|--------|------------|
| 1 | <mode>       | H/M/L      | H/M/L  | <action>   |
| 2 | ...          |            |        |            |

Top risks: #<N>, #<M>
Verdict: [Proceed with mitigations | Reconsider option | Reject option]
```

---

### 5. Pros-Cons-Fixes

#### When to Use

Use as a **follow-up to the Reversibility Filter** for A/B decisions, or as a
standalone framework when you need a constructive evaluation that goes beyond
listing negatives. The "Fixes" step forces you to propose a mitigation for each
con rather than using cons as blockers.

#### Process Steps

1. List pros (at least 2) for the option.
2. List cons (at least 1) for the option.
3. For each con, propose a **Fix** — a mitigation or workaround that reduces or
   eliminates the downside.
4. Evaluate: after fixes, does this option remain viable?
5. Repeat for each option under consideration.
6. Compare the options by their post-fix profiles.

#### Output Format

```
Option: <name>

Pros:
- <pro 1>
- <pro 2>

Cons and Fixes:
| Con | Fix |
|-----|-----|
| <con 1> | <fix 1> |
| <con 2> | <fix 2> |

Post-fix verdict: [Viable | Marginal | Not viable]
```

---

### 6. Second-Order Thinking

#### When to Use

Use for **architectural or strategic decisions** with long-term consequences.
Maps downstream effects at multiple time horizons. Prevents decisions that look
good in the short term but create compounding problems later.

#### Process Steps

1. State the decision and its immediate (first-order) effect.
2. For each first-order effect, ask: "And then what happens?" — this is the
   second-order effect.
3. For each second-order effect, ask the same question to get third-order effects
   (optional but valuable for high-stakes decisions).
4. Use two time horizons: **near term** (3–6 months) and **far term** (1–2 years).
5. Identify effects that are negative at the far horizon even if positive at the
   near horizon.
6. Adjust or reject the decision if second-order effects are unacceptable.

#### Output Format

```
Decision: <option>

Near term (3–6 months):
  First-order: <immediate effect>
  Second-order: <consequence of first-order>

Far term (1–2 years):
  First-order: <long-term direct effect>
  Second-order: <downstream consequence>
  Third-order (if applicable): <further consequence>

Key insight: <the non-obvious downstream effect that matters most>
Verdict: [Proceed | Caution — monitor <effect> | Reject — unacceptable second-order]
```

---

### 7. Regret Minimisation

#### When to Use

Use for **go/no-go or strategic choices** where you need to evaluate which
option you'll regret less in the long run. Particularly useful when the options
have asymmetric downside risks.

#### Process Steps

1. Project yourself forward to a "regret horizon" — typically 5–10 years, or
   the end of the relevant project.
2. For each option, ask: "If I choose this and it turns out wrong, how much will
   I regret it?"
3. Rate regret for each option on a scale of 1–10 (10 = maximum regret).
4. Also ask: "If I don't choose this and I should have, how much will I regret
   missing out?" (regret of omission).
5. Compare regret-of-commission vs regret-of-omission for each option.
6. Choose the option that minimises maximum regret.

#### Output Format

```
Regret horizon: <timeframe>

| Option | Regret if wrong (1–10) | Regret if not chosen (1–10) | Max regret |
|--------|------------------------|------------------------------|------------|
| A      | <N>                    | <N>                          | <max>      |
| B      | <N>                    | <N>                          | <max>      |

Minimum-regret choice: Option <X>
Rationale: <why this option has the lowest maximum regret>
```

---

### 8. Opportunity Cost Analysis

#### When to Use

Use when **choosing one option means forgoing others** — especially when
resources (time, budget, engineering capacity) are constrained. Surfaces the
hidden cost of not doing the alternatives.

#### Process Steps

1. List all options under consideration.
2. For each option, list what you are **explicitly giving up** by choosing it —
   the next-best alternative you forego.
3. Estimate the value of each foregone alternative (qualitative or quantitative).
4. Compare: is the chosen option worth more than the sum of what you give up?
5. If the opportunity cost is higher than expected, reconsider the allocation of
   resources.

#### Output Format

```
Option chosen: <name>

Opportunity costs:
| Option Not Chosen | What We Forgo | Estimated Value |
|-------------------|---------------|-----------------|
| <option B>        | <what B gave> | <value>         |
| <option C>        | <what C gave> | <value>         |

Total opportunity cost: <qualitative/quantitative summary>
Verdict: [Option <X> is worth more than opportunity costs | Reconsider allocation]
```

---

### 9. RICE Scoring

#### When to Use

Use for **prioritisation decisions** — what to build first, what to defer, what
to drop. Scores items across four dimensions: Reach, Impact, Confidence, Effort.

#### Process Steps

1. **Reach**: How many users/systems are affected per time period? (number)
2. **Impact**: How much does this move the key metric per user? (0.25=minimal,
   0.5=low, 1=medium, 2=high, 3=massive)
3. **Confidence**: How sure are you about Reach and Impact estimates? (percent:
   50%=low, 80%=medium, 100%=high)
4. **Effort**: Total person-months of work required (estimate)
5. Calculate: **RICE Score = (Reach × Impact × Confidence) / Effort**
6. Rank items by RICE score — higher score = higher priority.

#### Output Format

```
| Item | Reach | Impact | Confidence | Effort | RICE Score |
|------|-------|--------|------------|--------|------------|
| <A>  | <N>   | <N>    | <N>%       | <N>    | <score>    |
| <B>  | <N>   | <N>    | <N>%       | <N>    | <score>    |

Priority order: <A>, <B>, ...
Notes: <caveats about the estimates>
```

---

### 10. Eisenhower Matrix

#### When to Use

Use for **task prioritisation decisions** when the challenge is distinguishing
between urgency and importance. Prevents spending all time on urgent-but-unimportant
work at the expense of important-but-not-urgent work.

#### Process Steps

1. For each task/decision, assess: **Is it urgent?** (deadline-driven, immediate
   consequences if delayed)
2. For each task/decision, assess: **Is it important?** (significant long-term
   impact, contributes to key goals)
3. Place each item in the appropriate quadrant:
   - Q1 — Urgent + Important → **Do now**
   - Q2 — Not Urgent + Important → **Schedule** (most valuable quadrant)
   - Q3 — Urgent + Not Important → **Delegate or batch**
   - Q4 — Not Urgent + Not Important → **Eliminate**
4. Identify Q2 items that are being neglected due to Q3/Q4 distractions.
5. Restructure workload to protect Q2 time.

#### Output Format

```
Eisenhower Matrix:

| | Urgent | Not Urgent |
|---|--------|------------|
| **Important** | Q1: Do now | Q2: Schedule |
| | <items> | <items> |
| **Not Important** | Q3: Delegate/batch | Q4: Eliminate |
| | <items> | <items> |

Q2 alert: <items that should be protected but are being squeezed>
Recommendation: <prioritisation guidance>
```

---

## Cognitive Bias Detectors

When the agent's analysis matches a bias trigger pattern, surface the warning
inline. Present at most the 3 most relevant biases if multiple trigger
simultaneously (note others are available on request).

---

### Anchoring Bias

**Bias name:** Anchoring Bias

**Trigger pattern:** The analysis relies heavily on the first piece of
information introduced (first estimate, first option presented, first number
mentioned). Subsequent evaluations are adjustments from that anchor rather than
independent assessments.

**Warning text:** ⚠️ *Anchoring Bias detected: The first option/number
introduced may be exerting undue influence. Re-evaluate each option
independently from scratch, ignoring the initial anchor.*

---

### Confirmation Bias

**Bias name:** Confirmation Bias

**Trigger pattern:** Evidence-gathering has focused on information that
supports an already-preferred option. Counter-evidence has been minimised,
dismissed, or not sought. The analysis reads as advocacy rather than evaluation.

**Warning text:** ⚠️ *Confirmation Bias detected: The analysis appears to
favour evidence that confirms a pre-existing preference. Deliberately seek
counter-evidence for the leading option before concluding.*

---

### Sunk Cost Fallacy

**Bias name:** Sunk Cost Fallacy

**Trigger pattern:** The justification for continuing an option includes past
investment ("we've already built X", "we've already spent Y months on this").
Past investment is driving the decision rather than future expected value.

**Warning text:** ⚠️ *Sunk Cost Fallacy detected: Past investment is not a
reason to continue. Evaluate each option on its future value only. Ask: "If we
were starting today with no prior investment, which option would we choose?"*

---

### Availability Heuristic

**Bias name:** Availability Heuristic

**Trigger pattern:** The analysis overweights recent or memorable examples
(a recent outage, a high-profile failure, a colleague's recent experience)
rather than base-rate data or systematic evidence.

**Warning text:** ⚠️ *Availability Heuristic detected: Easily recalled examples
may be distorting the probability assessment. Check base rates and look for
systematic evidence rather than relying on vivid recent examples.*

---

### Status Quo Bias

**Bias name:** Status Quo Bias

**Trigger pattern:** The current approach is being defended not on its merits
but because it is the current approach. "Changing things" is treated as a cost
even when the alternative is clearly better. The default option is receiving
less scrutiny than alternatives.

**Warning text:** ⚠️ *Status Quo Bias detected: The current option may be
getting a free pass. Apply the same scrutiny to the status quo as to the
alternatives. Ask: "Would we choose the current approach if we were starting
fresh?"*

---

### Bandwagon Effect

**Bias name:** Bandwagon Effect

**Trigger pattern:** An option is being recommended primarily because others
(other teams, industry consensus, "everyone is using X") have adopted it, not
because it is the best fit for this specific context.

**Warning text:** ⚠️ *Bandwagon Effect detected: Popularity is not a
substitute for fitness-for-purpose. Evaluate the option against your specific
constraints and requirements, not against what others have chosen.*

---

### Dunning-Kruger Effect

**Bias name:** Dunning-Kruger Effect

**Trigger pattern:** High confidence is expressed about a domain where the
team or agent has limited experience. Risks and unknowns in an unfamiliar area
are being underestimated. Confidence exceeds demonstrated expertise.

**Warning text:** ⚠️ *Dunning-Kruger Effect detected: High confidence in an
unfamiliar domain may not be warranted. Identify what you don't know. Consider
consulting an expert or running a spike before committing.*

---

### IKEA Effect

**Bias name:** IKEA Effect

**Trigger pattern:** An internally-built solution is being overvalued relative
to an external alternative, primarily because the team built it. The in-house
option's flaws are minimised; the external option's benefits are underweighted.

**Warning text:** ⚠️ *IKEA Effect detected: We may be overvaluing the solution
we built. Evaluate the in-house option against the external option as if
someone else built both. Would we still choose ours?*

---

### Survivorship Bias

**Bias name:** Survivorship Bias

**Trigger pattern:** The analysis draws conclusions from successful examples
while ignoring failed examples. "Framework X worked for Company Y" without
considering the many companies for which it failed.

**Warning text:** ⚠️ *Survivorship Bias detected: Success stories are more
visible than failure stories. Seek out examples of this approach failing and
understand what conditions led to failure.*

---

### Recency Bias

**Bias name:** Recency Bias

**Trigger pattern:** The analysis places excessive weight on recent events,
trends, or data points relative to the longer-term historical record. A recent
incident, trend, or result is being treated as more representative than it is.

**Warning text:** ⚠️ *Recency Bias detected: Recent events may be
overrepresented in this analysis. Check whether recent data is genuinely
representative of the long-term pattern before treating it as decisive.*

---

### Authority Bias

**Bias name:** Authority Bias

**Trigger pattern:** A recommendation is being accepted primarily because it
comes from an authority figure (senior engineer, a well-known tech lead, a
famous blog post author) rather than because the evidence supports it.

**Warning text:** ⚠️ *Authority Bias detected: The source of a recommendation
does not determine its validity. Evaluate the argument on its merits
independently of who made it.*

---

### Scope Creep Bias

**Bias name:** Scope Creep Bias

**Trigger pattern:** Instead of choosing between options, the analysis is
expanding to accommodate all options simultaneously. The decision is being
avoided by broadening the scope to include everything.

**Warning text:** ⚠️ *Scope Creep Bias detected: Expanding scope to avoid
making a choice is not a decision — it is deferred decision-making with
compounded costs. Force a choice: which option best fits the current constraints?*

---

## Framework Auto-Selection

When a decision point is detected, use this table to select the appropriate
framework automatically. If the decision type does not match any row, use
**Pros-Cons-Fixes** as the catch-all default.

| Decision Type | Recommended Framework | Fallback |
|---|---|---|
| Binary choice (A or B) | Reversibility Filter → Pros-Cons-Fixes | Hypothesis-Driven Analysis |
| Multi-option comparison (A, B, C...) | Weighted Decision Matrix | RICE Scoring |
| Architectural tradeoff | Second-Order Thinking → Pre-Mortem | Hypothesis-Driven Analysis |
| Prioritisation (what to do first) | RICE Scoring or Eisenhower Matrix | Opportunity Cost Analysis |
| Risk assessment | Pre-Mortem | Regret Minimisation |
| Go/no-go decision | Reversibility Filter → Regret Minimisation | Pros-Cons-Fixes |

**Default fallback (unmatched decision type):** Pros-Cons-Fixes — it is the
most general framework and forces constructive evaluation over simple dismissal.

**User override:** If the user explicitly requests a specific framework ("use
pre-mortem", "run a weighted matrix"), honour that request and bypass
auto-selection.

---

## Brainstorm Integration Hooks

This section describes how `@aetos-brainstorm` should invoke the
decision-frameworks skill when a decision point is detected during design
exploration.

### When `@aetos-brainstorm` Should Activate Decision Frameworks

The skill is loaded at startup alongside `brainstorm` and `gotcha`. It activates
during **Phase 3 (Propose)** when the conversation reaches a point where a
structured decision is needed — typically when comparing approaches or choosing
between options.

**Decision-point detection triggers** (natural language patterns that indicate
a decision point):
- "should we use X or Y?"
- "compare A vs B" / "compare A versus B"
- "what's the best approach for..."
- "which option", "choose between"
- "tradeoff between", "trade-off between"
- "pros and cons of"

### Activation Sequence

When `@aetos-brainstorm` detects a decision point during Phase 3:

1. **Classify the decision type** using the auto-selection table
   (binary, multi-option, architectural, prioritisation, risk, go/no-go)
2. **Select a framework** from the auto-selection table for the classified type
3. **Apply the framework's process steps** to the options under consideration
4. **Run bias detectors** against the current analysis — check for patterns that
   match any of the 12 bias triggers
5. **Surface bias warnings** naturally in the conversation (at most 3, sorted by
   confidence; note others detected if more than 3 trigger)
6. **Produce a structured analysis** using the framework's output format

### Design Brief Integration

When a decision framework is applied during brainstorming, the design brief
output MUST include a `## Decision Analysis` section documenting:

- **Framework used**: which framework was selected and why
- **Analysis results**: the framework's output format populated with this
  decision's data
- **Bias warnings**: any bias detectors that triggered, with their warning text
- **Recommendation**: the framework's recommended option

This section is appended to the design brief's "Approaches Considered" section
or added as a standalone section after it.

> **[GLEIPNIR] The Decision Analysis is input to convergence, not the decision.**
> The `## Decision Analysis` (framework + bias warnings + recommendation) is
> presented to the **operator** at the brainstorm skill's Phase-4 convergence
> gate. The operator decides; the recommendation is advisory. The design brief
> records the operator's *converged* choice, with the analysis as its
> justification. An agent that treats its own recommendation as the decision has
> skipped the precept-10 gate — the exact failure this whole mechanism closes.

### Edge Cases

- **No decision point detected**: The skill is loaded but never activated.
  The brainstorming workflow completes normally with no overhead.
- **Decision type not in auto-selection table**: Apply Pros-Cons-Fixes as the
  catch-all default.
- **Multiple decision points in one session**: Apply a separate framework for
  each decision point, each with its own `## Decision Analysis` subsection.
- **User explicitly requests a framework**: Override auto-selection and apply
  the user's requested framework.
- **Brainstorming is bypassed** ("skip brainstorming"): Decision frameworks are
  NOT activated — they are coupled to the brainstorming workflow.
- **Skill fails to load**: `@aetos-brainstorm` falls back to its existing
  behaviour — present approaches with tradeoffs, but without structured framework
  analysis or bias detection. The brainstorming workflow MUST NOT fail because
  this skill fails to load.

---

## Anti-Patterns

**Anti-Pattern 1: Applying a heavyweight framework to a trivial decision**
Run the Reversibility Filter first. If the decision is a Two-Way Door, fast-track
it. Do not run a full Weighted Decision Matrix on a naming convention choice.

**Anti-Pattern 2: Presenting all 12 bias warnings simultaneously**
Surface at most 3 biases at a time. Overwhelming the user with 12 warnings
reduces the impact of each one. Prioritise the most confidently matched biases.

**Anti-Pattern 3: Using framework output as a substitute for judgment**
Frameworks structure analysis — they do not replace human judgment. A RICE score
of 1.2 vs 1.1 does not mandate a choice. Use frameworks to organise thinking, not
to abdicate responsibility.

**Anti-Pattern 4: Skipping bias detection**
Always run bias detectors after completing a framework analysis. The frameworks
structure the decision; the detectors guard against systematic distortions in the
inputs. **Exception:** At `quick` depth level, bias detection is skipped by
design (see Depth Level Integration).

---

## Edge Cases

See the decision-frameworks spec for the full edge-case table (E-1 through E-10).
Key cases:

- **E-2** (unmatched decision type): Pros-Cons-Fixes as default
- **E-4** (user requests specific framework): honour the request, bypass auto-selection
- **E-7** (all biases trigger): surface top 3, note others detected
- **E-8** (trivial reversible decision): Reversibility Filter fast-tracks it

---

## Depth Level Integration

Read `depth.level` from `.aetos/args/defaults.yaml` at the start of each
decision analysis. Apply the behaviour scaling below based on the active level.
If `depth.level` is missing or unrecognised, default to `standard` behaviour.

**quick (0.5× multiplier)**

- Apply at most **1 framework** (the auto-selected primary only — no fallbacks)
- **Skip bias detection** entirely (all 12 detectors are disabled)
- Produce **abbreviated output**: verdict only, no detailed tables or full framework
  output. One-paragraph summary sufficient.

**standard (1.0× multiplier)** — backward-compatible with pre-v3.10.0 behaviour,
identical to the existing default. No change from current operation.

- Apply the auto-selected framework plus fallback if needed (up to 3 frameworks)
- Run all 12 bias detectors, surface at most **3 warnings**
- Produce standard output format per each framework's Output Format section

**deep (1.7× multiplier)** — automatically generates a decision workspace
(`decision-plans/<project-slug>/`) at the repo root.

- Apply **all applicable frameworks** for the decision type (primary + fallback
  from the auto-selection table, and additional frameworks if relevant)
- Run **thorough bias analysis**: check all 12 detectors, surface **up to 5 warnings**
  (instead of the standard cap of 3)
- Produce **detailed** recommendations with full framework output tables, expanded
  evidence sections, and explicit rationale for each conclusion
- Workspace generation activates automatically at this depth level

**executive (2.5× multiplier)** — automatically generates a decision workspace
(`decision-plans/<project-slug>/`) at the repo root.

- Apply **all applicable frameworks** (same as deep)
- Run **comprehensive bias analysis**: check all 12 detectors, surface **all
  triggered warnings — no cap**
- Produce **stakeholder-ready** formatting:
  - Executive summary paragraph at the top
  - Visual recommendation callout block
  - Explicit confidence levels for every recommendation
  - Risk assessment table with likelihood/impact/mitigation for top risks
- Workspace generation activates automatically at this depth level

---

## Workspace Generation

When workspace generation is active, write each file to
`decision-plans/<project-slug>/` at the repo root as the corresponding analysis
step completes. This directory serves as a persistent, human-readable record of
the full decision analysis.

### Activation Triggers

Workspace generation activates in two ways:

**Explicit directive (any depth):** The user says one of the following
(case-insensitive):
- `"save step-by-step"`
- `"save the decision"`
- `"persist analysis"`
- `"document this decision"`
- `"save decision workspace"`
- `"save workspace"`

**Automatic (depth-based):** Workspace generation activates automatically at
`deep` and `executive` depth levels. It does NOT activate at `quick` or
`standard` depth without an explicit directive. At `quick` depth, workspace
generation is skipped unless the user explicitly requests it. At `standard`
depth, workspace generation is also skipped unless an explicit directive is
issued.

### Directory Structure

Create the workspace at repo root:

```
decision-plans/<project-slug>/
  00-OVERVIEW.md
  01-DECISION-TYPE.md
  02-FRAMEWORK.md
  03-CRITERIA.md
  04-ANALYSIS.md
  05-OPTIONS.md
  06-DECISION.md
  BIAS-WARNINGS.md
  DECISION-LOG.md
```

### Project Slug Derivation

Derive the `<project-slug>` from the decision title as follows:

1. Convert to **lowercase**
2. Replace spaces and special characters with **hyphens**
3. Remove consecutive hyphens (collapse `--` → `-`)
4. Truncate to a maximum of **50 chars**

Example: "Choose Database for Auth Service" → `choose-database-for-auth-service`

### Collision Handling

If the directory `decision-plans/<project-slug>/` already exists, append a
numeric suffix: `-2`, `-3`, etc., until a unique name is found.

Example: if `choose-database-for-auth-service` already exists, use
`choose-database-for-auth-service-2`.

### File Templates

Write each file as its corresponding analysis step completes (see Incremental
Writing Protocol below).

**`00-OVERVIEW.md`**
- Decision title
- Date
- Context description (what problem or opportunity triggered this decision)
- Stakeholders affected
- Urgency classification (Low / Medium / High / Critical)

**`01-DECISION-TYPE.md`**
- Classified decision type (binary, multi-option, architectural, prioritisation,
  risk assessment, go/no-go)
- Auto-selection table match: which row triggered framework selection
- Framework selected
- Framework selection rationale

**`02-FRAMEWORK.md`**
- Framework name (full name)
- Applied steps (the process steps applied for this specific decision)
- Output format (framework's output format populated with this decision's data)

**`03-CRITERIA.md`**
- For weighted-criteria frameworks (Weighted Decision Matrix, RICE Scoring):
  document evaluation criteria, weights / importance assigned to each criterion,
  and how criteria were determined (stakeholder input, technical constraints,
  or business goals)
- For qualitative frameworks (Pre-Mortem, Reversibility Filter, Regret
  Minimisation, Pros-Cons-Fixes, Second-Order Thinking): document evaluation
  dimensions and qualitative considerations used instead of numeric weights
- Note: adapt to the framework used — use criteria/weights for quantitative
  frameworks, evaluation dimensions for qualitative frameworks

**`04-ANALYSIS.md`**
- Option-by-option analysis against the criteria
- Evidence for and against each option
- Confidence ratings where applicable

**`05-OPTIONS.md`**
- Comparison matrix with all options scored against criteria
- Summary row with totals/rankings

**`06-DECISION.md`**
- Final recommendation
- Rationale for the recommendation
- Dissenting considerations (reasons one might choose an alternative)
- Confidence level (Low / Medium / High / Very High)

**`BIAS-WARNINGS.md`**
- All detected biases — uncapped (no 3-warning limit applies in workspace files)
- For each bias: trigger pattern identified, warning text, suggested mitigation
- If no biases detected: write "No biases detected" as the sole content

**`DECISION-LOG.md`**
- Journal entry with timestamp and the following fields:
  - Timestamp (date and time of the analysis)
  - Decision title
  - Framework used
  - Recommendation
  - One-sentence rationale

### Incremental Writing Protocol

Write each file as its corresponding step completes — do NOT wait until the
end of the analysis to write all files at once. The incremental approach ensures
partial workspace data is preserved even if the session ends before the analysis
is complete. After each step completes, immediately write (or update) the
corresponding workspace file.

### Edge Cases

**E-1 — No decision point detected but directive issued:**
If the user issues a workspace directive (e.g., "save step-by-step") but no
decision point has been detected yet, acknowledge the request and defer workspace
creation until the decision analysis begins. Do not create an empty workspace
directory.

**E-2 — Multiple decisions in a single session:**
If multiple decision points occur in one session, each decision gets its own
workspace directory. Apply the project slug derivation and collision handling
independently for each decision. Multiple decisions each receive separate,
complete workspace directories.

**E-3 — Abandoned analysis:**
If the analysis is abandoned or interrupted mid-session, preserve all partial
workspace files written so far. Write a note in `DECISION-LOG.md` indicating
"Analysis incomplete" along with the last completed step. If `DECISION-LOG.md`
has not yet been created when the session is abandoned, create it now with
"Analysis incomplete" and the last completed step name.
