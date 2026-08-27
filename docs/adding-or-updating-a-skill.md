# Adding or updating an external skill

This repository used the `skills` CLI to discover and acquire real Agent Skills, then reviewed and adapted them into each project’s `agent-capabilities/` source. Builds and agent sessions never fetch skill content from the network.

The CSV skill was acquired with:

```sh
DISABLE_TELEMETRY=1 npx --yes skills add https://github.com/openai/openai-agents-python/tree/main/examples/tools/skills/csv-workbench --agent claude-code --copy --yes
```

The security skill was acquired with:

```sh
DISABLE_TELEMETRY=1 npx --yes skills add github/awesome-copilot --skill security-review --agent claude-code --copy --yes
```

`npx` runs code from the npm ecosystem and the selected skill is third-party content. Review the package, repository, revision, skill files, and license before running or redistributing them. For stronger supply-chain controls, pin the `skills` CLI version instead of relying on `--yes skills`, acquire in a controlled environment, and require review of the resulting diff.

After acquisition, this repository:

1. placed the selected skill under `projects/<project>/agent-capabilities/<skill>`;
2. added a Tuff `tuff.toml` listing every shipped file;
3. retained the upstream MIT license;
4. recorded the repository revision, retrieval command, and pre-adaptation content hash in `UPSTREAM.md`;
5. adapted the instructions to project-relative paths and the pack's deterministic MCP tool;
6. installed and tracked the skill for the project’s selected agent with `tuff add skill`;
7. added the skill as a requirement of the project workflow;
8. built and verified the complete project-backed pack twice to check deterministic output.

To update a skill, acquire the new revision in a temporary directory, inspect the upstream diff, reapply local adaptations deliberately, update provenance, and bump the capability and pack versions. Do not overwrite the committed skill blindly: local tool names, safety constraints, and workflow instructions are part of the reviewed behavior.

The recorded content hash is provenance evidence, not a signature. It helps identify the originally acquired content but does not establish publisher identity. Production policy may additionally require signed commits, release attestations, or another trust mechanism.
