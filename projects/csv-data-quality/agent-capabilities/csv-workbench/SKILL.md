---
name: csv-workbench
description: Inspect, repair, validate, and summarize project-local CSV files with deterministic evidence. Use for CSV profiling, schema checks, duplicate or null cleanup, numeric constraints, and data-quality review.
---

# CSV Workbench

Use this skill when a task involves CSV data. Your job is to combine judgment about the requested transformation with evidence from the packaged `csv_quality_check` tool.

## Workflow

1. Read `.tuff-example/data-quality-policy.json` and the named CSV using project-relative paths. Do not assume `/mnt/data` or access files outside the project.
2. Invoke the `csv_quality_check` MCP tool before editing. Treat its output as deterministic observations, not a replacement for inspecting the rows and understanding the task.
3. Inspect the schema and representative rows with `head` or Python's `csv.DictReader`. Read [playbook.md](playbook.md) when the task needs profiling or aggregate analysis.
4. Repair the requested file without weakening the policy, deleting the hook, or suppressing a finding. Preserve a copy of source data when the project asks for one.
5. Invoke `csv_quality_check` again. Do not claim completion until its `status` is `pass` and its reported counts agree with your own inspection.
6. Summarize what changed, the number of input and output records, every assumption, and the final report path.

## Constraints

- Prefer Python stdlib for portability.
- Use only project-relative paths. Reject a task that requires path traversal or an absolute path outside the project.
- Never invent missing business values silently. Ask for guidance or record a clear assumption.
- Do not reduce validation just to make a gate pass.
- Keep numeric summaries concrete and include units when available.
- If data remains malformed, explain the exact unresolved rows and do not call the task complete.
