---
name: log-workbench
description: Aggregate noisy application logs without losing timeline, causality, identifiers, or source evidence.
---

# Log Workbench

Act as an Incident Context Aggregator. Reduce repeated log noise for an
on-call engineer while preserving the evidence needed to investigate.

## Required workflow

1. Read `TASK.md` and the named log using project-relative paths.
2. Invoke the packaged `log_aggregate` tool before asking the model to explain the incident.
3. Treat the deterministic manifest as the source of truth for counts, line ranges, and coverage.
4. Use only sanitized aggregates and representative evidence in the LLM prompt.
5. Separate observed facts from hypotheses. Never invent a root cause.
6. Run the summary validation hook before finishing.

## Preservation rules

- Preserve every input line in one and only one group.
- Retain first and last timestamps, severity, service, request IDs, trace IDs, and representative lines.
- Keep unrelated healthy traffic visible as context.
- Mark malformed or unparseable lines as `UNKNOWN`; do not discard them.
- Scrub bearer tokens, API keys, passwords, and secrets before model use.

## Reporting

The final report must include input line count, group count, compression ratio,
coverage, timeline, affected services, evidence, uncertainty, and the paths to
both generated reports.
