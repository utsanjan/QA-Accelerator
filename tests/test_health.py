import httpx
import pytest

from src import health


def _response(status: int, json_body: dict | None = None, url: str = "https://example.test/") -> httpx.Response:
    return httpx.Response(status, json=json_body or {}, request=httpx.Request("GET", url))


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(health, "STATUS_FILE", tmp_path / "connection_status.json")
    for name in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_DEVOPS_ORG",
        "AZURE_DEVOPS_PROJECT",
        "AZURE_DEVOPS_PAT",
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    health._cache.update(fingerprint=None, checked_at=0.0, data=None)


def _configure_openai(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://real-resource.cognitiveservices.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "a-real-looking-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.1")


def test_openai_missing_when_not_configured():
    result = health.check_azure_openai()
    assert result["status"] == "missing"
    assert result["badge"] == "Not configured"


def test_openai_ready_on_200(monkeypatch):
    _configure_openai(monkeypatch)
    monkeypatch.setattr(health.httpx, "get", lambda *a, **k: _response(200))
    result = health.check_azure_openai()
    assert result["status"] == "ready"
    assert result["detail"] == "gpt-5.1"


def test_openai_expired_key_is_not_reported_ready(monkeypatch):
    _configure_openai(monkeypatch)
    monkeypatch.setattr(health.httpx, "get", lambda *a, **k: _response(401))
    result = health.check_azure_openai()
    assert result["status"] == "error"
    assert result["badge"] == "Auth failed"
    assert "401" in result["detail"]


def test_openai_timeout_is_unreachable(monkeypatch):
    _configure_openai(monkeypatch)

    def _boom(*a, **k):
        raise httpx.ConnectTimeout("slow")

    monkeypatch.setattr(health.httpx, "get", _boom)
    result = health.check_azure_openai()
    assert result["status"] == "error"
    assert result["badge"] == "Unreachable"


def test_databricks_missing_when_not_configured():
    assert health.check_databricks()["status"] == "missing"


def _configure_databricks(monkeypatch):
    monkeypatch.setenv("DATABRICKS_SERVER_HOSTNAME", "adb-123.4.azuredatabricks.net")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc123")
    monkeypatch.setenv("DATABRICKS_ACCESS_TOKEN", "dapi-real-token")


def test_databricks_ready_reports_stopped_warehouse_without_starting_it(monkeypatch):
    _configure_databricks(monkeypatch)
    calls = []

    def _get(url, **kwargs):
        calls.append(url)
        if url.endswith("/scim/v2/Me"):
            return _response(200)
        return _response(200, {"state": "STOPPED"})

    monkeypatch.setattr(health.httpx, "get", _get)
    result = health.check_databricks()
    assert result["status"] == "ready"
    assert "Warehouse stopped" in result["detail"]
    assert all(call.startswith("https://") for call in calls)


def test_databricks_expired_token(monkeypatch):
    _configure_databricks(monkeypatch)
    monkeypatch.setattr(health.httpx, "get", lambda *a, **k: _response(401))
    result = health.check_databricks()
    assert result["status"] == "error"
    assert result["badge"] == "Auth failed"


def test_databricks_unknown_warehouse(monkeypatch):
    _configure_databricks(monkeypatch)

    def _get(url, **kwargs):
        return _response(200) if url.endswith("/scim/v2/Me") else _response(404)

    monkeypatch.setattr(health.httpx, "get", _get)
    result = health.check_databricks()
    assert result["status"] == "error"
    assert result["badge"] == "Warehouse not found"


def test_run_live_checks_survives_a_crashing_probe(monkeypatch):
    def _crash():
        raise ValueError("boom")

    monkeypatch.setitem(health._CHECKS, "azure_openai", _crash)
    results = health.run_live_checks()
    assert results["azure_openai"]["status"] == "error"
    assert set(results) == {"azure_openai", "azure_devops", "databricks"}


def _fake_checks(monkeypatch):
    calls = {"n": 0}

    def _fake_run():
        calls["n"] += 1
        return {"azure_openai": health._result("Azure OpenAI", "ready", "Ready", "x")}

    monkeypatch.setattr(health, "run_live_checks", _fake_run)
    return calls


def test_no_probe_without_refresh(monkeypatch):
    calls = _fake_checks(monkeypatch)
    assert health.get_last_live_status() is None
    assert health.get_last_live_status() is None
    assert calls["n"] == 0


def test_pending_status_does_not_probe(monkeypatch):
    calls = _fake_checks(monkeypatch)
    _configure_openai(monkeypatch)
    pending = health.pending_status()
    assert calls["n"] == 0
    assert pending["azure_openai"]["status"] == "unknown"
    assert pending["azure_openai"]["badge"] == "Not checked"
    assert pending["azure_devops"]["status"] == "missing"


def test_last_result_is_reused_until_refresh(monkeypatch):
    calls = _fake_checks(monkeypatch)
    refreshed = health.refresh_live_status()
    first = health.get_last_live_status()
    second = health.get_last_live_status()
    assert calls["n"] == 1
    assert first["checked_at"] == second["checked_at"] == refreshed["checked_at"]
    assert first["config_changed"] is False

    health.refresh_live_status()
    assert calls["n"] == 2


def test_last_result_survives_restart(monkeypatch):
    _fake_checks(monkeypatch)
    refreshed = health.refresh_live_status()
    health._cache.update(fingerprint=None, checked_at=0.0, data=None)  # simulate a new server process
    restored = health.get_last_live_status()
    assert restored["checked_at"] == refreshed["checked_at"]
    assert restored["data"]["azure_openai"]["badge"] == "Ready"


def test_config_change_is_flagged_but_not_rechecked(monkeypatch):
    calls = _fake_checks(monkeypatch)
    health.refresh_live_status()
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "rotated-key")
    last = health.get_last_live_status()
    assert last["config_changed"] is True
    assert last["data"]["azure_openai"]["badge"] == "Ready"
    assert calls["n"] == 1
