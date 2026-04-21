#!/usr/bin/env python3
"""Call the local deliberate debugger API and print the JSON response."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Call the local deliberate debugger API.",
    )
    parser.add_argument(
        "problem",
        help="Short description of the bug, error, or unexpected behaviour.",
    )
    code_group = parser.add_mutually_exclusive_group()
    code_group.add_argument(
        "--code",
        help="Inline code snippet or trace context to include in the request.",
    )
    code_group.add_argument(
        "--code-file",
        type=Path,
        help="Path to a file whose contents should be sent as the code snippet.",
    )
    parser.add_argument(
        "--attempted-fix",
        action="append",
        dest="attempted_fixes",
        default=[],
        help="A fix that has already been tried. Repeat for multiple failed fixes.",
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/debug",
        help="Debugger endpoint to call. Defaults to the local service.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds. Defaults to 60.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of pretty-printed JSON.",
    )
    return parser


def load_code(args: argparse.Namespace) -> str:
    if args.code_file is not None:
        return args.code_file.read_text(encoding="utf-8")
    return args.code or ""


def main() -> int:
    args = build_parser().parse_args()
    payload = {
        "problem": args.problem,
        "code": load_code(args),
        "attempted_fixes": args.attempted_fixes,
    }

    request = urllib.request.Request(
        args.endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(
            error_body or f"HTTP {exc.code} from {args.endpoint}",
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as exc:
        print(f"Failed to reach {args.endpoint}: {exc.reason}", file=sys.stderr)
        return 1

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        print(f"Server returned invalid JSON: {exc}", file=sys.stderr)
        return 1

    indent = None if args.compact else 2
    print(json.dumps(parsed, indent=indent, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
