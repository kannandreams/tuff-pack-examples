# Upstream provenance

This skill was acquired with `DISABLE_TELEMETRY=1 npx --yes skills add https://github.com/openai/openai-agents-python/tree/main/examples/tools/skills/csv-workbench --agent claude-code --copy --yes` and then adapted for this example.

- Repository: `https://github.com/openai/openai-agents-python`
- Upstream revision at acquisition: `6268f43e3aaf3d9ba193bff267345a8dc62f4223`
- `skills-lock.json` computed hash before adaptation: `fd6dfca600c5aa764526916150fb2751a2bdb16abb9c91f701dfd2cce7fa4a64`
- License: MIT

Adaptations replace the upstream `/mnt/data` assumption with safe project-relative paths and require the packaged `csv_quality_check` tool before and after a repair. Upstream code is never downloaded during pack build, installation, or runtime.
