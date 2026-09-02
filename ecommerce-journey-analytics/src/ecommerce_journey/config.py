from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RAW_EVENTS_PATH = RAW_DATA_DIR / "events.csv"
DATABASE_PATH = PROCESSED_DATA_DIR / "retailrocket.duckdb"

SQL_DIR = PROJECT_ROOT / "sql"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "01_ecommerce_journey_analysis.ipynb"

SESSION_GAP_MINUTES = 30
RECOVERY_HORIZONS_DAYS = (1, 7, 14, 30)

SOURCE_ARCHIVE_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    "retailrocket/ecommerce-dataset?datasetVersionNumber=4"
)
SOURCE_ARCHIVE_SHA256 = (
    "25120ba8d75524abe1fdc479704ae09d8b7e1999a9c86ae7c2dbf22861ab5eae"
)
RAW_EVENTS_SHA256 = (
    "3745aa83238b1e6d44d8fda209807899f420084398f94ddf745f3cbcfecbf9e7"
)


def ensure_directories() -> None:
    for path in (
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        TABLE_DIR,
        FIGURE_DIR,
        NOTEBOOK_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
