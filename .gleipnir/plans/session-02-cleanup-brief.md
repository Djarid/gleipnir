# ATLAS Brief — Session 02: goals population + plans lifecycle

Transient session artifact. Governed by the lifecycle policy this session
introduces (`plans/README.md`): disposable once its work is merged.

## A — Architect

**Problem (one sentence).** The scaffold left `goals/` empty and untracked and
piled durable and transient planning docs into one flat `plans/` dir with no
lifecycle, creating documentation technical debt.

**User.** The builder and the future G-5 engine (which reads goals as config),
plus anyone reading the repo who needs to tell reference material from
throwaway working notes.

**Success (measurable).**
1. `goals/` contains only *legitimate goals-content for the current stage*
   (plan-format, methodology workflow) plus a `manifest.md` index and a README
   explaining what may/may not go here under G-5. It is git-tracked.
2. Durable decision records live in `decisions/`, separate from transient
   session notes.
3. `plans/` holds only transient session artifacts and carries a written
   lifecycle policy (disposable after merge/promotion).
4. `AGENTS.md` layout and see-also references match the new structure.
5. No sequencing goals are authored (G-5 forbids goals owning sequencing;
   the engine doesn't exist yet).

**Constraints.**
- Do not invent goals the G-5 engine should own; goals = judgment-content +
  documentation only, per spec K-1.
- Keep the honest "authored, not yet closed" posture.
- No functional code change; this is knowledge-layer organisation.

## T — Trace

| Move | From | To | Kind |
|---|---|---|---|
| substrate decisions | `plans/substrate-design-pass.md` | `decisions/substrate-design-pass.md` | durable |
| session 01 brief/validation | `plans/session-01-*` | stay in `plans/` (transient) | disposable |
| step-0 scaffold record | `plans/step-0-scaffold.md` | stay in `plans/` (transient) | disposable |
| new goals content | — | `goals/{manifest,plan-format,methodology,README}.md` | goals-content |

**Edge cases.**
- Empty dirs aren't tracked by git → each kept dir needs real content.
- A goal that describes sequencing → forbidden now; README must say so.
- Cross-file refs to moved files → must be updated (AGENTS.md, any pointers).

## L — Link
- git mv preserves history for the moved decision record.
- grep for references to moved paths before/after.

## A — Assemble
1. Write this brief (done).  2. `git mv` substrate doc to `decisions/`.
3. Author goals content + manifest + README.  4. Write `plans/README.md`
lifecycle policy.  5. Update AGENTS.md.  6. Validate + commit.

## S — Stress-test (checks)
- `goals/manifest.md` lists every goal file and each exists.
- `decisions/` has the substrate record; `git log --follow` shows history.
- `plans/README.md` states the disposal policy.
- No sequencing goal authored.
- grep finds no stale `plans/substrate-design-pass.md` references.

## S — Result (validated)

All five checks PASS. One stale reference was found and fixed during
validation: `session-01-atlas-brief.md` still pointed at the pre-move
`plans/substrate-design-pass.md`; corrected to `decisions/`. Tests remain green
(20/20; unrelated to this knowledge-layer change but checked as a regression
guard). No sequencing goal was authored, per the G-5 rule.
