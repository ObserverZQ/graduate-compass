# Matching Agent Architecture: Initial Scope

**Status:** Frozen for the first implementation milestone  
**Scope:** One orchestrator, five bounded tools, and the existing SSE stream

Graduate Compass will use one agent/orchestrator to coordinate program discovery and recommendation. The orchestrator owns workflow state and invokes tools through validated inputs and outputs. It does not replace deterministic application logic.

## Initial tool boundary

| Tool | Responsibility |
| --- | --- |
| `search_programs` | Apply only explicit hard constraints and retrieve a bounded set of semantically relevant programs. Soft preferences never exclude a program. |
| `get_program_details` | Load the program fields and source evidence needed for comparison and explanation. |
| `assess_requirements` | Compare an applicant with published requirements and return strengths, gaps, and unknowns without predicting admission. |
| `calculate_preference_fit` | Compare expressed user preferences with available program data and return a deterministic, evidence-backed preference score without filtering candidates. |
| `rank_programs` | Combine deterministic requirement, preference, and relevance components, apply stable tie-breaking, and return at most eight ranked programs. |

Filtering, constraint checks, preference calculation, scoring, ranking, and tie-breaking remain deterministic and testable. The numeric result is a **fit score**, not an admission probability. The LLM will be introduced later for bounded planning and grounded explanation; it may summarize tool evidence but must not silently change deterministic scores or ranking.

## Preference matching policy

Preferences influence ranking, not eligibility. Location, budget, climate, duration, career direction, research interests, rankings, cohort size, and living experience are soft signals unless the user explicitly marks a supported field as a hard constraint.

Each expressed preference produces a component with its importance, earned and available points, match status, supporting evidence, and data confidence. The preference score uses only expressed preferences with usable program data:

```text
preference fit = earned points / available points
```

An omitted preference or an explicit "no preference" is excluded from the denominator and does not affect ordering. Missing program data creates an uncertainty and lowers evidence coverage; it does not reward, penalize, or exclude the program. A conflict with a soft preference lowers preference fit but keeps the program in consideration.

The final deterministic fit score combines requirement assessment, preference alignment, and academic/research/career relevance using fixed, documented, and versioned weights. Results expose both the preference score and its evidence coverage so users can distinguish poor alignment from insufficient data.

The existing `POST /match/stream` SSE endpoint is the user-visible execution trace. Preference calculation is a visible pipeline stage alongside retrieval, requirement assessment, and ranking. The stream will emit typed progress, warning, result, and terminal events so the interface can explain what the system is doing without exposing private résumé content, prompts, or hidden model reasoning.

## Explicitly deferred

The first milestone does not include:

- multiple agents;
- MCP integration;
- persistent or cross-session memory;
- one LLM call per program;
- LLM-owned filtering, scoring, or ranking.

These capabilities may be reconsidered only after the single-orchestrator flow is working end to end and evaluation demonstrates a concrete need.

The initial design used parallel per-candidate reasoning and an LLM ranking pass. It was simplified after considering latency, cost, consistency, and failure isolation: deterministic logic owns ranking, while the LLM owns grounded explanation.
