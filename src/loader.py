import re
import tempfile
from pathlib import Path

import requests


def load_source(source: str) -> Path:
    """Return a local path to the XLSX file, downloading from Google Drive if needed."""
    if "drive.google.com" in source:
        return _download_google_drive(source)
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {source}")
    return path


def _extract_file_id(url: str) -> str:
    # Handles /file/d/<id>/view and ?id=<id> formats
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Cannot extract file ID from URL: {url}")


def _download_google_drive(url: str) -> Path:
    file_id = _extract_file_id(url)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(download_url, timeout=30)
    response.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.write(response.content)
    tmp.close()
    return Path(tmp.name)
