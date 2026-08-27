# Task: review and repair the demo service

Perform a security review of `app/service.py`. Start with the installed deterministic baseline, then validate every signal in context using the security-review skill.

The code is intentionally unsafe and all credential-like values are fake and nonfunctional. Refactor it so:

- credentials are read from the environment rather than embedded in source;
- calculations accept only `number operator number` with `+`, `-`, `*`, or `/`;
- the command helper accepts an argument list and never invokes a shell;
- the database lookup uses a parameterized query.

Do not weaken `.tuff-example/security-policy.json` or disable the Stop hook. Propose and inspect the changes, apply them for this exercise, rerun the baseline, and explain why a clean baseline is not proof of complete security.
