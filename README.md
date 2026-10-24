# USDA official recall data snapshots

This repository fetches publicly available data from the [USDA FSIS Recall API](https://www.fsis.usda.gov/science-data/developer-resources/recall-api). It is independently maintained and is not a government website.

GitHub Actions is scheduled hourly at minute 17 (UTC), and can also be run manually. GitHub scheduled jobs can be delayed; this is not a real-time notification feed.

## Published files

- `snapshot/manifest.json`: official source URL, actual upstream fetch time, latest source record date, English record count, and SHA-256 hashes.
- `snapshot/usda.json.gz`: deterministic gzip-compressed JSON list of complete English official API records. Spanish copies are omitted. Full official HTML summaries and original notice URLs are retained.

The downloader validates record IDs, source hosts, complete text fields, and dates. A drop of more than 10% in the record count fails the job and retains the last published copy. Both files are committed together only after validation. Consumers should verify hashes and fetch time, reject stale snapshots, and keep the last good copy on failure.

This repository contains no FDA API credentials, food-package searches, user accounts, website source, or private data. The data refresh script is in `automation/usda_snapshot.py`; the installed workflow is `.github/workflows/usda-refresh.yml`.
