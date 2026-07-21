from __future__ import annotations

from pathlib import Path
from typing import Any

from lethal_expenses.scripts import smoke_sber

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sberbank_statement.txt"


def load_fixture() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def fixture_text(_: object, __: object) -> str:
    return load_fixture()


def fixture_text_without_footer(_: object, __: object) -> str:
    return load_fixture().replace("ВСЕГО СПИСАНИЙ 9 060,17", "")


def test_parse_russian_amount() -> None:
    assert smoke_sber.parse_russian_amount("9 060,17") == smoke_sber.Decimal("9060.17")


def test_smoke_sber_usage_message(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(smoke_sber.sys, "argv", ["smoke_sber"])

    assert smoke_sber.main() == 1
    assert (
        "usage: python -m lethal_expenses.scripts.smoke_sber <statement.pdf>"
        in capsys.readouterr().out
    )


def test_smoke_sber_main_outputs_footer_comparison(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(smoke_sber.sys, "argv", ["smoke_sber", "/tmp/sber.pdf"])
    monkeypatch.setattr(smoke_sber.SberbankParser, "extract_text", fixture_text)

    assert smoke_sber.main() == 0
    output = capsys.readouterr().out
    assert '"id": "sber-1000-20260301-08:15-AUTH01-neg15400"' in output
    assert "parsed_debit_total=-9060.17" in output
    assert "footer_debit_total=-9060.17" in output
    assert "difference_percent=0.00" in output


def test_smoke_sber_main_reports_missing_footer(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(smoke_sber.sys, "argv", ["smoke_sber", "/tmp/sber.pdf"])
    monkeypatch.setattr(
        smoke_sber.SberbankParser,
        "extract_text",
        fixture_text_without_footer,
    )

    assert smoke_sber.main() == 0
    assert "Footer total not found in statement text." in capsys.readouterr().out
