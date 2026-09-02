from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecommerce_journey.database import build_database  # noqa: E402
from ecommerce_journey.notebook import execute_notebook  # noqa: E402
from ecommerce_journey.outputs import (  # noqa: E402
    build_summary,
    export_tables,
    write_summary,
)
from ecommerce_journey.plots import generate_figures  # noqa: E402
from ecommerce_journey.validation import validate_project  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the complete SQL and Python product analytics pipeline."
    )
    parser.add_argument(
        "--skip-notebook",
        action="store_true",
        help="Skip notebook execution during development.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip final reproducibility checks during development.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started_at = time.perf_counter()

    print("1/5 Building DuckDB analytical model...")
    connection = build_database()

    print("2/5 Exporting reviewed tables and summary metrics...")
    tables = export_tables(connection)
    summary = build_summary(tables)
    write_summary(summary)

    print("3/5 Rendering figures...")
    generate_figures(tables)
    connection.close()

    if args.skip_notebook:
        print("4/5 Notebook execution skipped.")
    else:
        print("4/5 Executing notebook top to bottom...")
        execute_notebook()

    if args.skip_validation:
        print("5/5 Validation skipped.")
    else:
        print("5/5 Running consistency checks...")
        checks = validate_project()
        for check in checks:
            print(f"  {check}")

    elapsed = time.perf_counter() - started_at
    print(f"Pipeline finished in {elapsed:.1f} seconds.")


if __name__ == "__main__":
    main()
