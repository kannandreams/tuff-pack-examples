# Task: repair the orders extract

Prepare `data/orders.csv` for a downstream revenue load. Keep the existing header and row order.

The source-system owner supplied these authoritative corrections:

- order 1002 belongs to customer `c-2`;
- the second row labelled 1002 is actually order `1003`;
- order 1003's amount should be positive `5.00`;
- order 1004's amount is `25.00`.

Use the installed CSV workbench capability and deterministic checker. Do not weaken `.tuff-example/data-quality-policy.json` or disable the before-finish hook. Report the final row count, total amount in GBP, corrections made, and report path.
