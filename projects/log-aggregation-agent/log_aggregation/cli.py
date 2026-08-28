from __future__ import annotations

import argparse

from .engine import aggregate_log, write_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate noisy application logs without losing evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--input", required=True)
    aggregate.add_argument("--json-output", required=True)
    aggregate.add_argument("--markdown-output", required=True)
    args = parser.parse_args()
    manifest = aggregate_log(args.input)
    write_reports(manifest, args.json_output, args.markdown_output)
    print(f"aggregated {manifest['input_line_count']} lines into {manifest['group_count']} groups")
    print(f"coverage: {manifest['covered_line_count']}/{manifest['input_line_count']}")
    return 0 if manifest["uncovered_line_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
