"""Repo-relative locations. ROOT is derived from this file, never from the cwd."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
SCRAPED = DATA / "scraped"
INTERIM = DATA / "interim"
LOCK = DATA / "sources.lock.json"
REFERENCE = DATA / "reference"
OVERRIDES = DATA / "overrides"
APP_DATA = ROOT / "app" / "public" / "data"
