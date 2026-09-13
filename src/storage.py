"""投稿候補一覧をファイルに保存する部分。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def save_candidates(candidates: list[dict[str, Any]], output_dir: Path) -> Path:
    """投稿候補一覧を日付入りのJSONファイルとして保存し、保存先パスを返す。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"candidates_{timestamp}.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    return output_path
