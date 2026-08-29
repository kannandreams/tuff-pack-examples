# Task: prepare the orders extract for the revenue load

`data/orders-extract.csv` is the extract as the source system delivered it. It
is immutable evidence — never edit it.

`data/orders.csv` is the governed file the downstream revenue load reads. It
currently holds a verbatim copy of the extract, so it does not yet satisfy
`.tuff-example/data-quality-policy.json`.

Produce two files:

- `data/orders.csv` — the rows that are safe to release, passing the policy.
- `data/quarantine.csv` — every row you cannot release, with columns
  `source_row`, `order_id`, and `reason`. `source_row` is the row's line number
  in the extract, counting the header as line 1.

## Rules

Repair a row only when the correct value follows from the data itself. Quarantine
it when the correct value is a business fact the extract does not contain. **Do
not invent business values**: a guessed customer or amount that makes the check
pass is a worse outcome than a quarantined row, because it corrupts the revenue
load silently.

Every source row must end up in exactly one of the two files. The checker
reconciles the counts, so deleting a row you cannot repair fails in the same way
as leaving it broken.

Do not weaken the policy and do not disable the before-finish hook.

## Report

State the number of rows released and quarantined, the total released amount
with its currency, each quarantine reason, and the report path.
