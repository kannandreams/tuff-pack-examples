"""One safe solution for the intentionally unsafe teaching fixture."""

import operator
import os
import subprocess
from decimal import Decimal

API_KEY = os.environ["EXAMPLE_API_KEY"]
OPERATORS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}


def calculate(expression: str) -> Decimal:
    left, symbol, right = expression.split()
    if symbol not in OPERATORS:
        raise ValueError("unsupported operator")
    return OPERATORS[symbol](Decimal(left), Decimal(right))


def run_helper(arguments: list[str]):
    return subprocess.run(arguments, shell=False, capture_output=True, text=True, check=True)


def load_user(cursor, user_id: str):
    return cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
