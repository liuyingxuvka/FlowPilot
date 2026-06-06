"""Generate and check the FlowGuard project topology map.

The topology is an orientation artifact for mature FlowGuard projects. It
summarizes model runners, tests, code surfaces, result evidence, and known-bad
signals so agents can form project background before non-trivial work. It is
not validation evidence by itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowguard_project_topology_lib.collectors import build_report
from flowguard_project_topology_lib.common import (
    DEFAULT_JSON_PATH,
    DEFAULT_MARKDOWN_PATH,
    ROOT,
    _rel,
)
from flowguard_project_topology_lib.render import check_topology, render_markdown, write_topology


def _path_arg(value: str, root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        return root / path
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="write topology artifacts")
    build_parser.add_argument("--json-out", default=str(DEFAULT_JSON_PATH))
    build_parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_PATH))
    build_parser.add_argument("--json", action="store_true", help="print the generated report")

    check_parser = subparsers.add_parser("check", help="check topology artifacts")
    check_parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    check_parser.add_argument("--markdown-path", default=str(DEFAULT_MARKDOWN_PATH))
    check_parser.add_argument("--json", action="store_true", help="print the check report")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "build":
        report = write_topology(
            root,
            json_path=_path_arg(args.json_out, root),
            markdown_path=_path_arg(args.markdown_out, root),
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "json_path": _rel(_path_arg(args.json_out, root), root),
                        "markdown_path": _rel(_path_arg(args.markdown_out, root), root),
                        "layer_counts": report["layer_counts"],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        return 0
    if args.command == "check":
        result = check_topology(
            root,
            json_path=_path_arg(args.json_path, root),
            markdown_path=_path_arg(args.markdown_path, root),
        )
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
