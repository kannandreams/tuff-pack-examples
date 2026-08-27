# Security-review pack

This pack demonstrates how a reusable security-review capability layer can remain separate from application code and deployment images. It combines broad reasoning instructions with a deliberately limited deterministic baseline.

| Member | Why it exists |
| --- | --- |
| `security-review` skill | Teaches contextual review, source-to-sink reasoning, self-verification, severity, and human approval. |
| `security-baseline-scan` tool | Reproducibly reports a small set of high-value pattern signals without executing source code. |
| `require-security-review` hook | Reruns the baseline when Claude tries to stop so obvious signals cannot be silently skipped. |
| `secure-release-review` workflow | Makes the skill, tool, and hook an install-time dependency contract. |

The baseline is not a security guarantee. Pattern matching can produce false positives and miss real vulnerabilities. The skill is responsible for contextual validation, and a human remains responsible for reviewing proposed fixes and release decisions.

## Build it manually

```sh
tuff pack check packs/security-review
tuff pack build packs/security-review \
  --output .work/artifacts/security-review-1.0.0.tuffpack
tuff pack verify .work/artifacts/security-review-1.0.0.tuffpack
tuff pack inspect .work/artifacts/security-review-1.0.0.tuffpack
```

The pack source stays in this directory. Tuff reads the declared capability members and writes one portable artifact; it does not need a helper script or a second copied pack directory.

## Run it with Claude

For a disposable consumer project, use the repository helper:

```sh
./scripts/prepare-demo.sh security-review
cd .work/security-review
claude
```

Ask Claude to complete `TASK.md`. The starting service contains fake, nonfunctional credential text and intentionally unsafe Python patterns. Never use any fixture value as a real secret.

Run only the baseline with:

```sh
cd demos/security-review
python3 ../../packs/security-review/capabilities/security-baseline-scan/server.py check
```

An exit status of 1 is expected for the intentionally insecure starting fixture.
