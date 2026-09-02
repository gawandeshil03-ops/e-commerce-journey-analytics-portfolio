from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecommerce_journey.validation import validate_project  # noqa: E402


if __name__ == "__main__":
    for result in validate_project():
        print(result)
