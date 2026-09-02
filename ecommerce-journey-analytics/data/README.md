# Data

The raw RetailRocket dataset is intentionally excluded from Git.

Run:

```powershell
python scripts\download_data.py
```

The script downloads the fixed Kaggle archive, verifies its SHA-256 checksum,
and extracts only:

```text
data/
  raw/
    events.csv
```

If automatic download is unavailable, download dataset version 4 manually and
pass the archive path:

```powershell
python scripts\download_data.py --archive "C:\path\to\archive.zip"
```

The analytical database is generated under `data/processed/` and is also
excluded from Git. See [DATA_LICENSE.md](../DATA_LICENSE.md) for attribution
and licensing.
