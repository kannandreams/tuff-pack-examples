# Data-quality Stop gate

Claude invokes this hook when it is about to stop. The hook reruns the installed CSV checker against the current files. Exit 0 permits stopping; exit 2 sends actionable feedback to Claude and asks it to continue.

The hook does not trust an existing report, and it exits successfully when Claude sends `stop_hook_active: true` to prevent recursive Stop-hook loops. Operational errors fail closed with instructions to inspect the policy and tool.
