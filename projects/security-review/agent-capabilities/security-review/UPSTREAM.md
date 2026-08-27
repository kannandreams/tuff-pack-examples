# Upstream provenance

This skill was acquired with `DISABLE_TELEMETRY=1 npx --yes skills add github/awesome-copilot --skill security-review --agent claude-code --copy --yes` and then adapted for this example.

- Repository: `https://github.com/github/awesome-copilot`
- Upstream revision at acquisition: `4742f265959bf025882314564b364d9d7af6e2d5`
- `skills-lock.json` computed hash before adaptation: `9b1791054c648b84ca424fc1342dede2e04759dc73436bb91d21675d5a4c13ea`
- License: MIT

Adaptations require the packaged `security_baseline_scan` tool as a reproducible first and final pass and explicitly distinguish machine-detected signals from validated vulnerabilities. Upstream code is never downloaded during pack build, installation, or runtime.
