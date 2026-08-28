# Task: summarize the API outage

Act as the Incident Context Aggregator. Summarize `data/api.log` for an
on-call engineer investigating elevated checkout failures.

Preserve the timeline, affected services, request and trace IDs, representative
evidence, and source line ranges. Separate observed facts from hypotheses. Do
not claim a root cause that is not supported by the log evidence.

The final report must include the number of input lines, number of groups,
compression ratio, and the paths to the JSON manifest and Markdown summary.
