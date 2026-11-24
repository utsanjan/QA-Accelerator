import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.models.etl_spec import ETLSpecModel


class MetadataStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path("metadata") / "qa_accelerator.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS etl_specs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(name, version)
                );

                CREATE TABLE IF NOT EXISTS schema_registry (
                    id TEXT PRIMARY KEY,
                    table_fqn TEXT NOT NULL UNIQUE,
                    columns_json TEXT NOT NULL,
                    discovered_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS validation_runs (
                    id TEXT PRIMARY KEY,
                    spec_id TEXT NOT NULL,
                    run_at TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    report_path TEXT,
                    FOREIGN KEY(spec_id) REFERENCES etl_specs(id)
                );
                """
            )

    def save_spec(self, spec: ETLSpecModel, *, name: str | None = None) -> dict[str, Any]:
        spec_name = name or f"{spec.source_table}_to_{spec.target_table}".replace(".", "_")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS max_version FROM etl_specs WHERE name = ?",
                (spec_name,),
            ).fetchone()
            version = int(row["max_version"]) + 1
            now = datetime.now(UTC).isoformat()
            spec_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO etl_specs (id, name, version, content_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (spec_id, spec_name, version, json.dumps(spec.to_agent_dict()), now, now),
            )
        return {"id": spec_id, "name": spec_name, "version": version}

    def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM etl_specs WHERE id = ?", (spec_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "version": row["version"],
            "content": json.loads(row["content_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_latest_spec_by_name(self, name: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM etl_specs
                WHERE name = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (name,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "version": row["version"],
            "content": json.loads(row["content_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_specs(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, MAX(version) AS version, MAX(updated_at) AS updated_at
                FROM etl_specs
                GROUP BY name
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_schema(self, table_fqn: str, columns: list[dict[str, Any]]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO schema_registry (id, table_fqn, columns_json, discovered_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(table_fqn) DO UPDATE SET
                    columns_json = excluded.columns_json,
                    discovered_at = excluded.discovered_at
                """,
                (str(uuid4()), table_fqn, json.dumps(columns), now),
            )

    def get_schema(self, table_fqn: str) -> list[dict[str, Any]] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT columns_json FROM schema_registry WHERE table_fqn = ?",
                (table_fqn,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["columns_json"])

    def record_run(self, *, run_id: str, spec_id: str, summary: dict[str, Any], report_path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO validation_runs (id, spec_id, run_at, summary_json, report_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    spec_id,
                    datetime.now(UTC).isoformat(),
                    json.dumps(summary),
                    report_path,
                ),
            )
