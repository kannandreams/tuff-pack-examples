# CSV Playbook

Every example uses project-relative paths. Do not read or write outside the
project, and do not edit the immutable extract.

## Quick checks

Preview the governed file:

```bash
head -n 10 data/orders.csv
```

Count released rows:

```bash
python3 - <<'PY'
import csv
from pathlib import Path

with Path("data/orders.csv").open(newline="", encoding="utf-8") as handle:
    print(sum(1 for _ in csv.DictReader(handle)))
PY
```

## Account for every source row

A row you cannot repair belongs in the quarantine file with a reason, not in
the bin. The checker compares the counts, so a deleted row fails the same way
an unrepaired one does.

```bash
python3 - <<'PY'
import csv
from pathlib import Path

def rows(name):
    with Path(name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

source = rows("data/orders-extract.csv")
released = rows("data/orders.csv")
quarantined = rows("data/quarantine.csv")
print(f"source {len(source)} = released {len(released)} + quarantined {len(quarantined)}")
print("balanced" if len(source) == len(released) + len(quarantined) else "UNBALANCED")
PY
```

## Grouped totals template

```bash
python3 - <<'PY'
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

totals = defaultdict(Decimal)
with Path("data/orders.csv").open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        totals[row["currency"]] += Decimal(row["amount"].strip())

for currency in sorted(totals):
    print(currency, totals[currency])
PY
```

`Decimal` rather than `float`: these are monetary amounts, and the task asks
you to report a total.
