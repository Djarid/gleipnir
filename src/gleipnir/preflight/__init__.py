"""Gleipnir S-2/G-1 closure — first slice: the behavioural boundary preflight.

See `.gleipnir/plans/s2-g1-closure-first-slice.md` (the authority for this
package's contracts) and `boundary.py` for the pure decision core + thin
probe edge.

This package is OUT-OF-FRAMEWORK: it is invoked by the operator's launch
wrapper (`bin/gleipnir-preflight`), never by an in-framework agent. No agent
permission map grants it (see `.gleipnir/agents/*.md`, unedited by this
slice).
"""

from __future__ import annotations
