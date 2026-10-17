from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_key: str
    base_url: str
    model: str
    timeout: float
    max_output_tokens: int = 4096
    reasoning_effort: str = "none"

    @classmethod
    def load(cls):
        return cls(
            Path(os.getenv("DATA_DIR", str(ROOT / "data"))),
            os.getenv("OPENROUTER_API_KEY", ""),
            os.getenv("MODEL_BASE_URL") or "https://openrouter.ai/api/v1",
            os.getenv("MODEL_NAME") or "deepseek/deepseek-v4.1-flash",
            float(os.getenv("MODEL_TIMEOUT_SECONDS", "60")),
            int(os.getenv("MODEL_MAX_TOKENS", "4096")),
            os.getenv("MODEL_REASONING_EFFORT", "none"),
        )
