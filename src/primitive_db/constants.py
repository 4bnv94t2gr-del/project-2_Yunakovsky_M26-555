"""Общие настройки базы данных."""

from pathlib import Path

METADATA_FILE = "db_meta.json"
DATA_DIR = Path("data")
SUPPORTED_TYPES = {"int", "str", "bool"}
CACHE_MAX_SIZE = 128
