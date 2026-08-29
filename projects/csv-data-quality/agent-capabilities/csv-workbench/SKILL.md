---
name: csv-workbench
description: Inspect, repair, validate, and summarize project-local CSV files with deterministic evidence. Use for CSV profiling, schema checks, duplicate or null cleanup, numeric constraints, quarantine decisions, and data-quality review.
---

# CSV Workbench

Use this skill when a task involves CSV data. Your job is to combine judgment
about the requested transformation with evidence from the packaged
`csv_quality_check` tool.

## Workflow

1. Read the policy named by the task and the CSVs it points at, using
   project-relative paths. Do not assume `/mnt/data` or access files outside
   the project.
2. Invoke the `csv_quality_check` MCP tool before editing. Treat its output as
   deterministic observations, not a replacement for reading the rows and
   understanding the task.
3. Inspect the schema and representative rows with `head` or Python's
   `csv.DictReader`. Read [playbook.md](playbook.md) for profiling, row
   accounting, and aggregate templates.
4. Repair only what the available evidence supports, and quarantine the rest.
   Do not weaken the policy, delete the hook, or suppress a finding.
5. Invoke `csv_quality_check` again. Do not claim completion until its `status`
   is `pass` and its counts agree with your own inspection.
6. Summarize what you released, what you quarantined and why, every assumption,
   and the final report path.

## Repair or quarantine

Repair a row only when the correct value follows from the data itself:
normalizing the case of a known code, trimming surrounding whitespace, or
dropping a row that duplicates another in every field.

Quarantine a row when the correct value is a business fact you do not have. A
missing customer, an unparseable amount, a currency you have no rate for, and
two rows that disagree on the same key are all facts to record, not gaps to
fill. Quarantining is not deleting: write the row to the quarantine file named
by the policy with its source row number and a specific reason, so every source
row stays accounted for.

## Constraints

- Prefer Python stdlib for portability. Use `Decimal`, not `float`, for money.
- Use only project-relative paths. Reject a task that requires path traversal
  or an absolute path outside the project.
- Never invent a missing business value. There is no credit for a row that
  passes because you guessed at it.
- Never edit the immutable source extract; it is the evidence the check
  reconciles against.
- Do not reduce validation just to make a gate pass.
- Keep numeric summaries concrete and include units when available.
- If rows remain unresolved, say exactly which ones and why, and do not call
  the task complete.
