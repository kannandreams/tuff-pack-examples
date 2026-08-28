# Log aggregation tool

Run the deterministic engine with:

```sh
python3 server.py aggregate --input data/api.log --json-output reports/aggregation.json --markdown-output reports/aggregation.md
```

The output preserves every source line through group ranges and includes
sanitized representative evidence. Exit status 0 means complete coverage.
