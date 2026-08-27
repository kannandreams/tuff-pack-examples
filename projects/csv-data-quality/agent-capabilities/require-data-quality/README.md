# Data-quality Stop gate

An Open Agents-compatible harness invokes this hook before finishing. The hook reruns the installed CSV checker against the current files. Exit 0 permits finishing; exit 2 returns actionable feedback and asks the agent to continue.

The hook does not trust an existing report. Operational errors fail closed with instructions to inspect the policy and tool.
