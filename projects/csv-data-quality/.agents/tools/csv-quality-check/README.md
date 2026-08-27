# CSV quality checker

This is both a command-line program and a real stdio MCP server. It uses only Python's standard library and emits deterministically ordered JSON without timestamps or machine-specific absolute paths.

```sh
python3 server.py check --policy .tuff-example/data-quality-policy.json --output .tuff-reports/data-quality.json
```

Exit status 0 means the policy passed, 1 means quality findings exist, and 2 means the policy or input could not be processed. With no arguments, the process serves MCP on stdin/stdout. Never write diagnostics to stdout in MCP mode because stdout is the protocol transport.

The policy supports `input`, `required_columns`, `non_null`, `unique_key`, and numeric rules such as `"amount": {"min": 0}`. All paths must remain beneath the working project.
