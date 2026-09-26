from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("SRO_OTLP_ENDPOINT", "")
load_dotenv(Path(__file__).resolve().parents[2] / ".env.steel")
