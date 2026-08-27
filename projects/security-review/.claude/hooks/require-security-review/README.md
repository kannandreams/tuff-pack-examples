# Security-review Stop gate

Claude invokes this hook when it is about to stop. The hook reruns the installed baseline scanner instead of trusting a stale report. Baseline signals block stopping so they cannot be accidentally omitted, but they still require contextual validation by the security-review skill.

The hook honors `stop_hook_active: true` to prevent recursive loops. This teaching policy requires every baseline signal to be fixed; production teams may design a reviewed exception mechanism rather than weakening or deleting the gate.
