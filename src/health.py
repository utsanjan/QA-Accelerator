"""Live connectivity checks for the services the QA Accelerator depends on.

``src.config.get_connection_status`` only reports whether ``.env`` values are
present. The functions here actually talk to each service, using calls that are
cheap and side-effect free:

* Azure OpenAI   - ``GET /openai/models`` with the API key (no tokens consumed).
* Azure DevOps   - ``GET _apis/projects`` and confirm the configured project exists.
* Databricks     - SCIM ``Me`` to validate host + token, and a read-only warehouse
                   lookup for its state. The warehouse is never started.

Results use the same shape as ``get_connection_status`` plus a ``badge`` label and
use ``status`` of ``ready``, ``missing`` (not configured), ``error`` (configured
but the live check failed) or ``unknown`` (configured but never checked).

The services are probed only on demand (``refresh_live_status``). Every other page
load just reads the last stored result via ``get_last_live_status``.
"""

from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import httpx

from src.config import (
    _env_present,
    get_azure_devops_settings,
    get_connection_status,
    get_databricks_settings,
)

PROBE_TIMEOUT_SECONDS = 8.0

# The last check is stored here so it survives page loads and server restarts.
# Probes only ever run when ``refresh_live_status`` is called (the refresh button).
STATUS_FILE = Path(__file__).resolve().parents[1] / "metadata" / "connection_status.json"

ServiceStatus = dict[str, str]

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {"fingerprint": None, "checked_at": 0.0, "data": None}


def _result(label: str, status: str, badge: str, detail: str, info: str = "") -> ServiceStatus:
    """``detail`` is the one-line card text; ``info`` is the full text shown on hover."""
    return {"label": label, "status": status, "badge": badge, "detail": detail, "info": info}


def _http_failure(label: str, exc: Exception, *, auth_hint: str) -> ServiceStatus:
    """Translate an exception from a probe into a status entry."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return _result(label, "error", "Auth failed", f"{code} - {auth_hint}")
        return _result(label, "error", "Error", f"HTTP {code} from service")
    if isinstance(exc, httpx.TimeoutException):
        return _result(label, "error", "Unreachable", "Timed out - check network, VPN or endpoint")
    if isinstance(exc, httpx.RequestError):
        return _result(label, "error", "Unreachable", f"Could not connect ({exc.__class__.__name__})")
    return _result(label, "error", "Error", str(exc) or exc.__class__.__name__)


def check_azure_openai(timeout: float = PROBE_TIMEOUT_SECONDS) -> ServiceStatus:
    label = "Azure OpenAI"
    if not (_env_present("AZURE_OPENAI_ENDPOINT") and _env_present("AZURE_OPENAI_API_KEY")):
        return _result(label, "missing", "Not configured", "Set endpoint and API key in .env")

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.1").strip()
    try:
        response = httpx.get(
            f"{endpoint}/openai/models",
            params={"api-version": "2024-10-21"},
            headers={"api-key": api_key},
            timeout=timeout,
        )
        response.raise_for_status()
    except Exception as exc:
        return _http_failure(label, exc, auth_hint="API key rejected or wrong endpoint")
    return _result(label, "ready", "Ready", deployment, f"Endpoint: {endpoint}\nDeployment: {deployment}")


def check_azure_devops(timeout: float = PROBE_TIMEOUT_SECONDS) -> ServiceStatus:
    label = "Azure DevOps"
    if not (
        _env_present("AZURE_DEVOPS_ORG")
        and _env_present("AZURE_DEVOPS_PROJECT")
        and _env_present("AZURE_DEVOPS_PAT")
    ):
        return _result(label, "missing", "Not configured", "Set org, project, and PAT in .env")

    from src.integrations.azure_devops_client import AzureDevOpsClient

    try:
        settings = get_azure_devops_settings()
        client = AzureDevOpsClient(replace(settings, timeout_seconds=int(timeout)))
        result = client.test_connection()
    except RuntimeError as exc:
        message = str(exc)
        if "401" in message or "rejected the PAT" in message:
            return _result(label, "error", "Auth failed", "401 - PAT rejected or expired")
        return _result(label, "error", "Error", message[:160])
    except ValueError:
        # Azure DevOps answers a bad PAT with an HTML sign-in page instead of JSON.
        return _result(label, "error", "Auth failed", "PAT rejected or expired")
    except Exception as exc:
        return _http_failure(label, exc, auth_hint="PAT rejected or expired")
    org_project = f"{result['organization']}/{result['project']}"
    return _result(label, "ready", "Ready", org_project, f"Organization / project: {org_project}")


def check_databricks(timeout: float = PROBE_TIMEOUT_SECONDS) -> ServiceStatus:
    label = "Azure Databricks"
    settings = get_databricks_settings()
    if settings.is_dummy:
        return _result(label, "missing", "Not configured", "Set hostname, HTTP path, and token in .env")

    host = settings.server_hostname.rstrip("/")
    base = host if host.startswith("http") else f"https://{host}"
    headers = {"Authorization": f"Bearer {settings.access_token}"}
    try:
        response = httpx.get(f"{base}/api/2.0/preview/scim/v2/Me", headers=headers, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        return _http_failure(label, exc, auth_hint="access token rejected or expired")

    detail = "Connected"
    info = f"Host: {settings.server_hostname}"
    warehouse_id = settings.http_path.rstrip("/").split("/")[-1]
    try:
        wh = httpx.get(f"{base}/api/2.0/sql/warehouses/{warehouse_id}", headers=headers, timeout=timeout)
        if wh.status_code == 200:
            state = str(wh.json().get("state", "")).lower()
            if state:
                suffix = " - starts on first query" if state == "stopped" else ""
                detail = f"Warehouse {state}{suffix}"
                info = f"Host: {settings.server_hostname}\nWarehouse: {warehouse_id} ({state}{suffix})"
        elif wh.status_code == 404:
            return _result(
                label,
                "error",
                "Warehouse not found",
                f"Token is valid but warehouse '{warehouse_id}' does not exist - check DATABRICKS_HTTP_PATH",
            )
    except Exception:
        pass  # Warehouse state is a bonus; the token check above is what decides readiness.
    return _result(label, "ready", "Ready", detail, info)


_CHECKS: dict[str, Callable[[], ServiceStatus]] = {
    "azure_openai": check_azure_openai,
    "azure_devops": check_azure_devops,
    "databricks": check_databricks,
}


def _fingerprint() -> str:
    """Identify the current configuration without keeping any secret in memory twice."""
    import hashlib

    names = (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_DEVOPS_ORG",
        "AZURE_DEVOPS_PROJECT",
        "AZURE_DEVOPS_PAT",
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_ACCESS_TOKEN",
    )
    raw = "\x1f".join(os.getenv(name, "") for name in names)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_live_checks() -> dict[str, ServiceStatus]:
    """Probe every service in parallel. Never raises."""
    results: dict[str, ServiceStatus] = {}
    with ThreadPoolExecutor(max_workers=len(_CHECKS), thread_name_prefix="health") as pool:
        futures = {key: pool.submit(check) for key, check in _CHECKS.items()}
        for key, future in futures.items():
            try:
                results[key] = future.result()
            except Exception as exc:  # defensive: a probe bug must not break the page
                results[key] = _result(key, "error", "Error", str(exc) or exc.__class__.__name__)
    return results


def _save_to_disk(fingerprint: str, checked_at: float, data: dict[str, ServiceStatus]) -> None:
    """Best-effort persistence; a read-only disk must never break the page."""
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"fingerprint": fingerprint, "checked_at": checked_at, "data": data}
        STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def _load_from_disk() -> dict[str, Any] | None:
    try:
        payload = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        data = payload["data"]
        if isinstance(data, dict) and data:
            return {
                "fingerprint": str(payload.get("fingerprint", "")),
                "checked_at": float(payload["checked_at"]),
                "data": data,
            }
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def get_last_live_status() -> dict[str, Any] | None:
    """Return the stored result of the last check without contacting any service.

    The result is ``{"data", "checked_at", "config_changed"}`` or ``None`` if no check
    has ever been run. ``config_changed`` is ``True`` when ``.env`` values differ from
    the ones that were in effect when the check ran.
    """
    with _cache_lock:
        if _cache["data"] is None:
            stored = _load_from_disk()
            if stored is not None:
                _cache.update(stored)
        if _cache["data"] is None:
            return None
        return {
            "data": _cache["data"],
            "checked_at": _cache["checked_at"],
            "config_changed": _cache["fingerprint"] != _fingerprint(),
        }


def pending_status() -> dict[str, ServiceStatus]:
    """Placeholder cards for before the first check. Reads ``.env`` only, no network."""
    pending: dict[str, ServiceStatus] = {}
    for key, item in get_connection_status().items():
        if item["status"] == "ready":
            pending[key] = _result(item["label"], "unknown", "Not checked", "Use the refresh button to verify")
        else:
            pending[key] = _result(item["label"], "missing", "Not configured", item["detail"])
    return pending


def refresh_live_status() -> dict[str, Any]:
    """Run the live checks now and store the result. This is the only place that probes."""
    data = run_live_checks()
    checked_at = time.time()
    fingerprint = _fingerprint()
    with _cache_lock:
        _cache.update(fingerprint=fingerprint, checked_at=checked_at, data=data)
    _save_to_disk(fingerprint, checked_at, data)
    return {"data": data, "checked_at": checked_at, "config_changed": False}
