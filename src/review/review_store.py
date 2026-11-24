import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class ReviewStore:
    def __init__(self, review_dir: Path | None = None) -> None:
        self.review_dir = review_dir or Path("review") / "drafts"
        self.review_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, draft_id: str) -> Path:
        return self.review_dir / f"{draft_id}.json"

    def create_draft(
        self,
        *,
        etl_spec_draft: dict[str, Any],
        requirement_summary: dict[str, Any],
        mapping_rows: list[dict[str, Any]],
        source_files: dict[str, str],
        missing_information: list[str] | None = None,
        assumptions: list[str] | None = None,
        mapping_analysis: dict[str, Any] | None = None,
        canonical_mappings: list[dict[str, Any]] | None = None,
        entity_logic: list[dict[str, Any]] | None = None,
        stm_entities: list[dict[str, Any]] | None = None,
        llm_mapping_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        draft_id = str(uuid4())
        payload = {
            "draft_id": draft_id,
            "status": "pending_review",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "requirement_summary": requirement_summary,
            "mapping_rows": mapping_rows,
            "mapping_analysis": mapping_analysis or {},
            "canonical_mappings": canonical_mappings or [],
            "entity_logic": entity_logic or [],
            "stm_entities": stm_entities or [],
            "llm_mapping_output": llm_mapping_output or {},
            "etl_spec_draft": etl_spec_draft,
            "missing_information": missing_information or [],
            "assumptions": assumptions or [],
            "source_files": source_files,
        }
        self._path(draft_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        path = self._path(draft_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_drafts(self, *, status: str | None = "pending_review") -> list[dict[str, Any]]:
        drafts: list[dict[str, Any]] = []
        for path in sorted(self.review_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if status is None or payload.get("status") == status:
                drafts.append(payload)
        return drafts

    def update_draft_spec(self, draft_id: str, etl_spec_draft: dict[str, Any]) -> dict[str, Any]:
        draft = self.get_draft(draft_id)
        if not draft:
            raise FileNotFoundError(f"Draft not found: {draft_id}")
        draft["etl_spec_draft"] = etl_spec_draft
        draft["updated_at"] = datetime.now(UTC).isoformat()
        self._path(draft_id).write_text(json.dumps(draft, indent=2), encoding="utf-8")
        return draft

    def approve_draft(self, draft_id: str) -> dict[str, Any]:
        draft = self.get_draft(draft_id)
        if not draft:
            raise FileNotFoundError(f"Draft not found: {draft_id}")
        draft["status"] = "approved"
        draft["approved_at"] = datetime.now(UTC).isoformat()
        draft["updated_at"] = draft["approved_at"]
        self._path(draft_id).write_text(json.dumps(draft, indent=2), encoding="utf-8")
        return draft

    def delete_draft(self, draft_id: str) -> None:
        path = self._path(draft_id)
        if not path.exists():
            raise FileNotFoundError(f"Draft not found: {draft_id}")
        path.unlink()

    def update_draft(self, draft_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        draft = self.get_draft(draft_id)
        if not draft:
            raise FileNotFoundError(f"Draft not found: {draft_id}")
        draft.update(updates)
        draft["updated_at"] = datetime.now(UTC).isoformat()
        self._path(draft_id).write_text(json.dumps(draft, indent=2), encoding="utf-8")
        return draft
