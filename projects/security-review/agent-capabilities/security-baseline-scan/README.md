# Security baseline scanner

This Python-standard-library tool reports a deliberately small set of deterministic **signals**: hardcoded credential-like assignments, dynamic evaluation, shell-enabled subprocesses, and SQL query interpolation. Signals require contextual review and are not automatically vulnerabilities. A passing baseline cannot prove that a codebase is secure.

```sh
python3 server.py check --policy .tuff-example/security-policy.json --output .tuff-reports/security-review.json
```

Exit status 0 means no baseline signals, 1 means signals were found, and 2 means an operational or policy error occurred. With no arguments, the program serves the `security_baseline_scan` MCP tool on stdin/stdout.

Paths are constrained to the working project. The scanner ignores symlinks and configured directories, limits file size, and scans only configured extensions. It never executes the code it inspects.
