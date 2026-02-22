"""Export admin gateway OpenAPI schema for frontend contract sync checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from focus_guard.core.admin_gateway.app import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export admin gateway OpenAPI schema")
    parser.add_argument(
        "--output",
        default="admin_ui/src/api/generated/admin_gateway_openapi.json",
        help="Output path for exported OpenAPI JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app = create_app()
    schema = app.openapi()

    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Exported admin gateway OpenAPI schema -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
