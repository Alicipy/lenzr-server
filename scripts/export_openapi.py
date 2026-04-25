"""Export the OpenAPI schema from the FastAPI app."""

import argparse
import json
from pathlib import Path

from lenzr_server.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("openapi.json"),
        help="File to write the schema to (default: openapi.json).",
    )
    args = parser.parse_args()

    schema = json.dumps(app.openapi(), indent=2, sort_keys=True)
    args.output.write_text(schema + "\n")


if __name__ == "__main__":
    main()
