"""Export the GapMap OpenAPI document deterministically."""

import json
from pathlib import Path

from gapmap.apps.api.main import create_app


OUTPUT = Path("gapmap/shared/contracts/openapi.json")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
