"""Intentionally unsafe teaching fixture. No values are real credentials."""

import subprocess

API_KEY = "demo_not_a_real_key_123456"


def calculate(expression: str):
    return eval(expression)


def run_helper(command: str):
    return subprocess.run(command, shell=True, capture_output=True, text=True)


def load_user(cursor, user_id: str):
    return cursor.execute(f"SELECT id, email FROM users WHERE id = '{user_id}'").fetchone()
