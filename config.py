"""
config.py
Feature toggles and configuration. Edit this file to change app behaviour
without touching any other code.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Security ─────────────────────-────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "")           # set in .env to enable auth
REQUIRE_AUTH = bool(API_KEY)

# ── Privacy ──────────────────────────────────────────────────────────────────
STRIP_PII = os.getenv("STRIP_PII", "false").lower() == "true"   # redact merchant names

# ── Queue ────────────────────────────────────────────────────────────────────
USE_QUEUE = os.getenv("USE_QUEUE", "false").lower() == "true"   # enable in-memory queue

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "transactions.db")
