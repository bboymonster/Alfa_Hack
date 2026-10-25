import json
from typing import Any

import pytest

from ai_service import cli


def test_cli_insight_offline(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], settings: Any
) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    code = cli.main(["insight", "--sample", "key-rate", "--company", "U_1595", "--role", "CFO"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "offline"
    assert payload["card"]["why_it_matters"]
    assert "CL_PRODUCT_LOA_MARK=1" in payload["card"]["traceability"]["matched_company_features"]


def test_cli_unknown_company(monkeypatch: pytest.MonkeyPatch, settings: Any) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    assert cli.main(["insight", "--company", "NOPE"]) == 2
