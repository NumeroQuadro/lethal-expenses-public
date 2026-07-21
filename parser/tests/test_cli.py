from __future__ import annotations

import shutil
from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import TypeAdapter

import lethal_expenses.cli as cli_module
from lethal_expenses.cli import (
    SuspiciousOverlapError,
    app,
    collapse_duplicate_transactions,
    disambiguate_duplicate_transaction_ids,
    discover_pdf_paths,
    dump_transactions_json,
    load_external_accounts,
    load_transactions_json,
    mark_external_accounts,
    raise_for_suspicious_overlaps,
)
from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import Transaction

CliRunner = cast(Any, import_module("click.testing")).CliRunner
SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "all_transactions.snapshot.json"


def build_sample_transaction() -> Transaction:
    occurred_at = BaseParser.parse_date_ru("25.12.2025", "22:40")
    return Transaction(
        id=BaseParser.build_id("sber", "****7000", occurred_at, "903866"),
        date=occurred_at,
        amount=Decimal("-1234.56"),
        merchant_raw="Яндекс Такси",
        description="SBSCR_Яндекс Такси Операция по карте ****7000",
        bank="sberbank",
        account="****7000",
        raw={"auth_code": "903866", "category_label": "Транспорт"},
    )


def copy_fixture_pdfs(destination: Path, synthetic_pdf_paths: dict[str, Path]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for fixture_path in synthetic_pdf_paths.values():
        shutil.copy2(fixture_path, destination / fixture_path.name)


def test_discover_pdf_paths_returns_empty_for_missing_directory(tmp_path: Path) -> None:
    assert discover_pdf_paths(tmp_path / "missing") == []


def test_discover_pdf_paths_skips_archived_subdirectories(tmp_path: Path) -> None:
    active_pdf = tmp_path / "active.pdf"
    archived_pdf = tmp_path / "_archived" / "old.pdf"
    archived_pdf.parent.mkdir()
    active_pdf.write_text("active", encoding="utf-8")
    archived_pdf.write_text("archived", encoding="utf-8")

    assert discover_pdf_paths(tmp_path) == [active_pdf]


def test_collapse_duplicate_transactions_drops_exact_duplicates_and_keeps_cleaner_text() -> None:
    base = build_sample_transaction()
    noisy = base.model_copy(
        update={
            "description": base.description + " ДАТА ОПЕРАЦИИ",
            "raw": {"source_name": "snapshot-b.pdf"},
        }
    )
    clean = base.model_copy(update={"raw": {"source_name": "snapshot-a.pdf"}})

    collapsed = collapse_duplicate_transactions([noisy, clean])

    assert len(collapsed) == 1
    assert collapsed[0].description == clean.description


def test_collapse_duplicate_transactions_keeps_same_id_rows_when_amounts_differ() -> None:
    base = build_sample_transaction()
    collision = base.model_copy(
        update={
            "amount": Decimal("-10.00"),
            "merchant_raw": "Комиссия за операцию",
            "description": "Комиссия за операцию. Операция по карте ****7000",
        }
    )

    collapsed = collapse_duplicate_transactions([base, collision])

    assert len(collapsed) == 2


def test_disambiguate_duplicate_transaction_ids_suffixes_collisions_deterministically() -> None:
    first = build_sample_transaction().model_copy(
        update={
            "id": "sber-4000-20240718-13:25-290874-pos55355",
            "account": "****4000",
            "amount": Decimal("553.55"),
            "merchant_raw": "И. Иван Иванович.",
            "description": "Перевод от И. Иван Иванович. Операция по карте ****5000",
            "raw": {"auth_code": "290874", "source_name": "sberbank-card-synthetic.pdf"},
        }
    )
    second = first.model_copy(
        update={
            "merchant_raw": "И. Иванов .",
            "description": "Перевод от И. Иванов . Операция по карте ****5000",
        }
    )

    disambiguated = disambiguate_duplicate_transaction_ids([first, second])

    assert len({transaction.id for transaction in disambiguated}) == 2
    assert all(
        transaction.id.startswith("sber-4000-20240718-13:25-290874-pos55355-x")
        for transaction in disambiguated
    )
    assert disambiguate_duplicate_transaction_ids([first, second]) == disambiguated


def test_load_external_accounts_reads_masked_account_config(tmp_path: Path) -> None:
    config_path = tmp_path / "external_accounts.yaml"
    config_path.write_text(
        (
            "accounts:\n"
            "  - bank: sberbank\n"
            '    account: "****4000"\n'
            '    reason: "External relay account"\n'
        ),
        encoding="utf-8",
    )

    assert load_external_accounts(config_path) == {("sberbank", "****4000")}


def test_mark_external_accounts_flags_matching_rows_only() -> None:
    primary = build_sample_transaction()
    external = primary.model_copy(
        update={
            "id": "sber-4000-20251225-22:40-903866",
            "account": "****4000",
        }
    )

    marked = mark_external_accounts([primary, external], {("sberbank", "****4000")})

    assert marked[0].is_external_account is False
    assert marked[1].is_external_account is True


def test_raise_for_suspicious_overlaps_logs_and_raises(caplog: pytest.LogCaptureFixture) -> None:
    first = build_sample_transaction()
    second = first.model_copy(
        update={
            "id": "sber-7000-20251225-22:40-400000",
            "date": first.date + timedelta(seconds=30),
        }
    )

    with caplog.at_level("WARNING"):
        with pytest.raises(SuspiciousOverlapError, match="suspicious overlapping row pair"):
            raise_for_suspicious_overlaps(
                [first, second],
                {
                    id(first): "parser/pdfs/statement-a.pdf",
                    id(second): "parser/pdfs/statement-b.pdf",
                },
            )

    assert "OVERLAP WARN bank=sberbank" in caplog.text
    assert "id_a=sber-7000-20251225-22:40-903866" in caplog.text
    assert "id_b=sber-7000-20251225-22:40-400000" in caplog.text
    assert "source_a=parser/pdfs/statement-a.pdf" in caplog.text
    assert "source_b=parser/pdfs/statement-b.pdf" in caplog.text


def test_build_command_writes_schema_valid_json(
    tmp_path: Path,
    synthetic_pdf_paths: dict[str, Path],
) -> None:
    pdf_dir = tmp_path / "pdfs"
    out_file = tmp_path / "transactions.json"
    copy_fixture_pdfs(pdf_dir, synthetic_pdf_paths)

    runner = CliRunner()
    result = runner.invoke(app, ["build", "--pdfs", str(pdf_dir), "--out", str(out_file)])

    assert result.exit_code == 0, result.output
    assert out_file.exists()
    assert "Wrote 21 transactions" in result.output

    transactions = TypeAdapter(list[Transaction]).validate_json(
        out_file.read_text(encoding="utf-8")
    )

    assert len(transactions) == 21
    assert transactions == sorted(
        transactions,
        key=lambda transaction: (transaction.date, transaction.id),
        reverse=True,
    )
    assert any(transaction.category == "Еда" for transaction in transactions)
    assert any(transaction.category == "Переводы" for transaction in transactions)


def test_build_command_reuses_shared_page_text_dispatch(
    tmp_path: Path,
    synthetic_pdf_paths: dict[str, Path],
    monkeypatch: Any,
) -> None:
    pdf_dir = tmp_path / "pdfs"
    out_file = tmp_path / "transactions.json"
    copy_fixture_pdfs(pdf_dir, synthetic_pdf_paths)

    observed_page1_calls: list[str] = []
    observed_full_calls: list[str] = []
    original_extract_pdf_text = cli_module.extract_pdf_text

    def counting_extract_pdf_text(path: str | Path, *, max_pages: int | None = None) -> str:
        name = Path(path).name
        if max_pages == 1:
            observed_page1_calls.append(name)
        else:
            observed_full_calls.append(name)
        return original_extract_pdf_text(path, max_pages=max_pages)

    monkeypatch.setattr(cli_module, "extract_pdf_text", counting_extract_pdf_text)

    runner = CliRunner()
    result = runner.invoke(app, ["build", "--pdfs", str(pdf_dir), "--out", str(out_file)])

    assert result.exit_code == 0, result.output
    expected_files = sorted(path.name for path in pdf_dir.glob("*.pdf"))
    assert sorted(observed_page1_calls) == expected_files
    assert sorted(observed_full_calls) == expected_files


def test_dedup_idempotency(tmp_path: Path, synthetic_pdf_paths: dict[str, Path]) -> None:
    single_dir, double_dir = tmp_path / "single", tmp_path / "double"
    single_dir.mkdir()
    double_dir.mkdir()
    source_pdf = synthetic_pdf_paths["yandex"]
    shutil.copy2(source_pdf, single_dir / source_pdf.name)
    shutil.copy2(source_pdf, double_dir / source_pdf.name)
    shutil.copy2(source_pdf, double_dir / "copy.pdf")
    runner = CliRunner()
    single_out, double_out = tmp_path / "single.json", tmp_path / "double.json"
    assert (
        runner.invoke(app, ["build", "--pdfs", str(single_dir), "--out", str(single_out)]).exit_code
        == 0
        and runner.invoke(
            app, ["build", "--pdfs", str(double_dir), "--out", str(double_out)]
        ).exit_code
        == 0
    )
    single_rows, double_rows = (
        load_transactions_json(single_out),
        load_transactions_json(double_out),
    )
    assert [row.model_dump(mode="json", exclude={"raw"}) for row in single_rows] == [
        row.model_dump(mode="json", exclude={"raw"}) for row in double_rows
    ]
    assert {len(row.raw["sources"]) for row in single_rows} == {1} and {
        len(row.raw["sources"]) for row in double_rows
    } == {2}


def test_build_command_verbose_reports_transfer_pairs(
    tmp_path: Path,
    synthetic_pdf_paths: dict[str, Path],
) -> None:
    pdf_dir = tmp_path / "pdfs"
    out_file = tmp_path / "transactions.json"
    copy_fixture_pdfs(pdf_dir, synthetic_pdf_paths)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["build", "--pdfs", str(pdf_dir), "--out", str(out_file), "--verbose"],
    )

    assert result.exit_code == 0, result.output
    assert "sberbank_minimal.pdf: SberbankCardParser -> 5 rows" in result.output
    assert "yandex_minimal.pdf: YandexCardParser -> 7 rows" in result.output
    assert "ozon_minimal.pdf: OzonSavingsParser -> 4 rows" in result.output
    assert "spb_minimal.pdf: SpbParser -> 5 rows" in result.output
    assert "Detected 1 transfer pairs" in result.output


def test_build_command_fails_when_no_pdfs_are_found(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["build", "--pdfs", str(tmp_path / "missing"), "--out", str(tmp_path / "out.json")],
    )

    assert result.exit_code != 0
    assert "No PDF statements found under" in result.output


def test_build_command_snapshot_for_all_synthetic_fixtures(
    tmp_path: Path,
    synthetic_all_pdf_dir: Path,
) -> None:
    out_file = tmp_path / "transactions.json"
    assert synthetic_all_pdf_dir.samefile(Path(__file__).parent / "fixtures" / "all")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["build", "--pdfs", str(synthetic_all_pdf_dir), "--out", str(out_file)],
    )

    assert result.exit_code == 0, result.output
    assert out_file.read_text(encoding="utf-8") == SNAPSHOT_PATH.read_text(encoding="utf-8")


def test_build_command_is_byte_identical_across_repeated_runs(
    tmp_path: Path,
    synthetic_all_pdf_dir: Path,
) -> None:
    first_out = tmp_path / "first.json"
    second_out = tmp_path / "second.json"
    runner = CliRunner()

    first = runner.invoke(
        app,
        ["build", "--pdfs", str(synthetic_all_pdf_dir), "--out", str(first_out)],
    )
    second = runner.invoke(
        app,
        ["build", "--pdfs", str(synthetic_all_pdf_dir), "--out", str(second_out)],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert first_out.read_text(encoding="utf-8") == second_out.read_text(encoding="utf-8")


def test_dump_and_load_transactions_json_round_trip(tmp_path: Path) -> None:
    transaction = build_sample_transaction()
    path = tmp_path / "transactions.json"
    path.write_text(dump_transactions_json([transaction]), encoding="utf-8")

    assert load_transactions_json(path) == [transaction]


def test_inspect_command_reports_summary_stats(
    tmp_path: Path,
    synthetic_pdf_paths: dict[str, Path],
) -> None:
    pdf_dir = tmp_path / "pdfs"
    out_file = tmp_path / "transactions.json"
    copy_fixture_pdfs(pdf_dir, synthetic_pdf_paths)

    runner = CliRunner()
    build_result = runner.invoke(app, ["build", "--pdfs", str(pdf_dir), "--out", str(out_file)])
    assert build_result.exit_code == 0, build_result.output

    inspect_result = runner.invoke(app, ["inspect", str(out_file)])

    assert inspect_result.exit_code == 0, inspect_result.output
    assert "Transactions: 21" in inspect_result.output
    assert "Expense total (excluding transfers and external accounts):" in inspect_result.output
    assert "Per-bank expense totals:" in inspect_result.output
    assert "Top 20 uncategorized merchants:" in inspect_result.output
    assert "- ozon:" in inspect_result.output


def test_inspect_command_handles_no_expenses_or_uncategorized_rows(tmp_path: Path) -> None:
    base = build_sample_transaction()
    transactions = [
        base.model_copy(update={"amount": Decimal("50.00"), "is_transfer": False}),
        base.model_copy(update={"amount": Decimal("-10.00"), "is_transfer": True}),
    ]
    out_file = tmp_path / "transactions.json"
    out_file.write_text(dump_transactions_json(transactions), encoding="utf-8")

    runner = CliRunner()
    inspect_result = runner.invoke(app, ["inspect", str(out_file)])

    assert inspect_result.exit_code == 0, inspect_result.output
    assert "Expense rows (excluding transfers and external accounts): 0" in inspect_result.output
    assert inspect_result.output.count("- none") == 2


def test_inspect_command_excludes_external_account_rows_from_expense_totals(tmp_path: Path) -> None:
    base = build_sample_transaction()
    external = base.model_copy(
        update={
            "id": "sber-4000-20251226-10:10-auth07",
            "date": BaseParser.parse_date_ru("26.12.2025", "10:10"),
            "amount": Decimal("-200.00"),
            "account": "****4000",
            "is_external_account": True,
        }
    )
    out_file = tmp_path / "transactions.json"
    out_file.write_text(
        dump_transactions_json(
            [
                base.model_copy(update={"amount": Decimal("-100.00")}),
                external,
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    inspect_result = runner.invoke(app, ["inspect", str(out_file)])

    assert inspect_result.exit_code == 0, inspect_result.output
    assert "Expense rows (excluding transfers and external accounts): 1" in inspect_result.output
    assert (
        "Expense total (excluding transfers and external accounts): 100.00 RUB"
        in inspect_result.output
    )
    assert "- sberbank: 100.00 RUB across 1 rows" in inspect_result.output
    assert "- Яндекс Такси: 100.00 RUB across 1 rows" in inspect_result.output
