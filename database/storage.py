from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteStorage:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    recommendation TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_run(self, run_date: str, payload: dict[str, Any], markdown: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO reports (run_date, content) VALUES (?, ?)", (run_date, markdown))
            for item in payload.get("indices", []) + payload.get("stocks", []):
                conn.execute(
                    """
                    INSERT INTO scores
                    (run_date, asset_type, name, symbol, score, recommendation, risk_level, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_date,
                        item.get("type", "unknown"),
                        item.get("name", ""),
                        item.get("symbol", ""),
                        int(item.get("score", 0)),
                        item.get("recommendation", ""),
                        item.get("risk_level", ""),
                        json.dumps(item, ensure_ascii=False, default=str),
                    ),
                )
