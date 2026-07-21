from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha1
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from lethal_expenses.categories import apply_categories
from lethal_expenses.normalize import TransferDedupeStats, dedupe_self_transfers
from lethal_expenses.parsers.base import extract_pdf_text
from lethal_expenses.registry import get_parser_for_text
from lethal_expenses.schema import ACCOUNT_MASK_RE, BankName, Transaction

click = cast(Any, import_module("click"))

PARSER_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDFS_DIR = PARSER_ROOT / "pdfs"
DEFAULT_OUTPUT_PATH = PARSER_ROOT / "data" / "transactions.json"
DEFAULT_EXTERNAL_ACCOUNTS_PATH = PARSER_ROOT / "external_accounts.yaml"
TRANSACTION_LIST_ADAPTER = TypeAdapter(list[Transaction])
ARCHIVE_DIR_PREFIX = "_"
OVERLAP_MAX_DELTA = timedelta(seconds=60)

LOGGER = logging.getLogger(__name__)


class ExternalAccountEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank: BankName
    account: str
    reason: str | None = None

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        if ACCOUNT_MASK_RE.fullmatch(value) is None:
            raise ValueError('external account must match the masked format "****1234"')
        return value


class ExternalAccountsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounts: list[ExternalAccountEntry] = Field(
        default_factory=lambda: list[ExternalAccountEntry]()
    )


@dataclass(frozen=True, slots=True)
class SuspiciousOverlap:
    bank: BankName
    account: str
    amount: Decimal
    first_date: datetime
    second_date: datetime
    first_id: str
    second_id: str
    first_source: str
    second_source: str


class SuspiciousOverlapError(Exception):
    def __init__(self, overlaps: Sequence[SuspiciousOverlap]):
        self.overlaps = list(overlaps)
        super().__init__(
            "Detected "
            f"{len(self.overlaps)} suspicious overlapping row pair(s) across PDFs "
            "with differing ids. See OVERLAP WARN lines above and investigate "
            "before trusting totals."
        )


def discover_pdf_paths(pdfs_dir: Path) -> list[Path]:
    if not pdfs_dir.exists():
        return []

    return sorted(
        path
        for path in pdfs_dir.rglob("*.pdf")
        if path.is_file()
        and not any(
            part.startswith(ARCHIVE_DIR_PREFIX) for part in path.relative_to(pdfs_dir).parts[:-1]
        )
    )


def _transaction_dedup_key(transaction: Transaction) -> tuple[str, ...]:
    return (
        transaction.id,
        transaction.bank,
        transaction.account,
        transaction.date.isoformat(),
        str(transaction.amount),
        transaction.currency,
        transaction.merchant_raw,
        transaction.precision,
    )


def _prefer_duplicate_transaction(existing: Transaction, candidate: Transaction) -> Transaction:
    if len(candidate.description) < len(existing.description):
        return candidate
    if len(candidate.description) > len(existing.description):
        return existing
    if len(candidate.merchant_raw) < len(existing.merchant_raw):
        return candidate
    return existing


def _transaction_sources(transaction: Transaction) -> list[str]:
    sources: list[str] = []
    raw_sources = transaction.raw.get("sources")
    if isinstance(raw_sources, list):
        for source in cast(list[object], raw_sources):
            if isinstance(source, str) and source not in sources:
                sources.append(source)

    source_name = transaction.raw.get("source_name")
    if isinstance(source_name, str) and source_name not in sources:
        sources.append(source_name)
    return sources


def _with_sources(transaction: Transaction, sources: list[str]) -> Transaction:
    if not sources:
        return transaction
    raw = dict(transaction.raw)
    raw["sources"] = sources
    return transaction.model_copy(update={"raw": raw}, deep=True)


def _account_digits(account: str) -> str:
    return "".join(character for character in account if character.isdigit())[-4:]


def detect_suspicious_overlaps(
    transactions: Sequence[Transaction],
    source_path_by_object_id: Mapping[int, str],
) -> list[SuspiciousOverlap]:
    grouped: dict[tuple[BankName, str, Decimal], list[Transaction]] = {}

    for transaction in transactions:
        grouped.setdefault(
            (
                transaction.bank,
                _account_digits(transaction.account),
                abs(transaction.amount),
            ),
            [],
        ).append(transaction)

    overlaps: list[SuspiciousOverlap] = []
    for group in grouped.values():
        ordered_group = sorted(
            group,
            key=lambda transaction: (
                transaction.date,
                transaction.id,
                source_path_by_object_id.get(id(transaction), "<unknown>"),
            ),
        )
        for index, first in enumerate(ordered_group):
            first_source = source_path_by_object_id.get(id(first), "<unknown>")
            for second in ordered_group[index + 1 :]:
                delta = second.date - first.date
                if delta > OVERLAP_MAX_DELTA:
                    break

                second_source = source_path_by_object_id.get(id(second), "<unknown>")
                if first.id == second.id or first_source == second_source:
                    continue

                overlaps.append(
                    SuspiciousOverlap(
                        bank=first.bank,
                        account=first.account,
                        amount=abs(first.amount),
                        first_date=first.date,
                        second_date=second.date,
                        first_id=first.id,
                        second_id=second.id,
                        first_source=first_source,
                        second_source=second_source,
                    )
                )

    return overlaps


def raise_for_suspicious_overlaps(
    transactions: Sequence[Transaction],
    source_path_by_object_id: Mapping[int, str],
) -> None:
    overlaps = detect_suspicious_overlaps(transactions, source_path_by_object_id)
    if not overlaps:
        return

    for overlap in overlaps:
        LOGGER.warning(
            "OVERLAP WARN bank=%s account=%s amount=%s ts_a=%s id_a=%s source_a=%s "
            "ts_b=%s id_b=%s source_b=%s",
            overlap.bank,
            overlap.account,
            overlap.amount,
            overlap.first_date.isoformat(),
            overlap.first_id,
            overlap.first_source,
            overlap.second_date.isoformat(),
            overlap.second_id,
            overlap.second_source,
        )

    raise SuspiciousOverlapError(overlaps)


def load_external_accounts(
    path: Path = DEFAULT_EXTERNAL_ACCOUNTS_PATH,
) -> set[tuple[BankName, str]]:
    if not path.exists():
        return set()

    payload = cast(object, yaml.safe_load(path.read_text(encoding="utf-8")))
    loaded: object = {} if payload is None else payload
    config = ExternalAccountsConfig.model_validate(loaded)
    return {(entry.bank, entry.account) for entry in config.accounts}


def mark_external_accounts(
    transactions: Sequence[Transaction],
    external_accounts: set[tuple[BankName, str]],
) -> list[Transaction]:
    if not external_accounts:
        return list(transactions)

    marked: list[Transaction] = []
    for transaction in transactions:
        if (transaction.bank, transaction.account) in external_accounts:
            marked.append(transaction.model_copy(update={"is_external_account": True}, deep=True))
            continue
        marked.append(transaction)

    return marked


def collapse_duplicate_transactions(transactions: Sequence[Transaction]) -> list[Transaction]:
    """Collapse identical logical rows before transfer matching and categorization."""
    deduped: dict[tuple[str, ...], Transaction] = {}

    for transaction in transactions:
        transaction_with_sources = _with_sources(transaction, _transaction_sources(transaction))
        key = _transaction_dedup_key(transaction_with_sources)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = transaction_with_sources
            continue

        merged_sources = _transaction_sources(existing)
        for source in _transaction_sources(transaction_with_sources):
            if source not in merged_sources:
                merged_sources.append(source)

        preferred = _prefer_duplicate_transaction(existing, transaction_with_sources)
        deduped[key] = _with_sources(preferred, merged_sources)

    return list(deduped.values())


def _transaction_id_disambiguation_key(transaction: Transaction) -> str:
    payload = {
        "merchant_raw": transaction.merchant_raw,
        "description": transaction.description,
        "raw": transaction.raw,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def disambiguate_duplicate_transaction_ids(
    transactions: Sequence[Transaction],
) -> list[Transaction]:
    grouped: dict[str, list[Transaction]] = {}
    order: list[str] = []

    for transaction in transactions:
        if transaction.id not in grouped:
            grouped[transaction.id] = []
            order.append(transaction.id)
        grouped[transaction.id].append(transaction)

    disambiguated: list[Transaction] = []
    for transaction_id in order:
        group = grouped[transaction_id]
        if len(group) == 1:
            disambiguated.append(group[0])
            continue

        per_key_counts: dict[str, int] = {}
        for transaction in sorted(group, key=_transaction_id_disambiguation_key):
            key = _transaction_id_disambiguation_key(transaction)
            per_key_counts[key] = per_key_counts.get(key, 0) + 1
            digest = sha1(key.encode("utf-8")).hexdigest()[:8]
            suffix = f"{digest}-{per_key_counts[key]:02d}"
            disambiguated.append(
                transaction.model_copy(update={"id": f"{transaction.id}-x{suffix}"}, deep=True)
            )

    return disambiguated


def build_transactions_from_pdfs(
    pdf_paths: Sequence[Path],
    *,
    external_accounts_path: Path = DEFAULT_EXTERNAL_ACCOUNTS_PATH,
    transfer_stats: TransferDedupeStats | None = None,
    verbose: bool = False,
) -> list[Transaction]:
    parsed_transactions: list[Transaction] = []
    source_path_by_object_id: dict[int, str] = {}

    for pdf_path in pdf_paths:
        page1_text = extract_pdf_text(pdf_path, max_pages=1)
        parser = get_parser_for_text(page1_text)
        statement_text = extract_pdf_text(pdf_path)
        transactions = list(parser.parse_text(statement_text, source_name=pdf_path.name))
        parsed_transactions.extend(transactions)
        source_path = pdf_path.as_posix()
        for transaction in transactions:
            source_path_by_object_id[id(transaction)] = source_path

        if verbose:
            click.echo(f"{pdf_path.name}: {parser.__class__.__name__} -> {len(transactions)} rows")

    raise_for_suspicious_overlaps(parsed_transactions, source_path_by_object_id)

    external_accounts = load_external_accounts(external_accounts_path)
    marked_transactions = mark_external_accounts(parsed_transactions, external_accounts)
    deduped_transactions = collapse_duplicate_transactions(marked_transactions)
    unique_id_transactions = disambiguate_duplicate_transaction_ids(deduped_transactions)
    normalized = dedupe_self_transfers(unique_id_transactions, stats=transfer_stats)
    categorized = apply_categories(normalized)
    categorized.sort(key=lambda transaction: (transaction.date, transaction.id), reverse=True)
    return categorized


def dump_transactions_json(transactions: Sequence[Transaction]) -> str:
    payload = TRANSACTION_LIST_ADAPTER.dump_python(list(transactions), mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"


def load_transactions_json(path: Path) -> list[Transaction]:
    return TRANSACTION_LIST_ADAPTER.validate_json(path.read_text(encoding="utf-8"))


def format_rub(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


@click.group()
def app() -> None:
    """Build and inspect the offline Lethal Expenses dataset."""


@app.command("build")
@click.option(
    "--pdfs",
    "pdfs_dir",
    default=DEFAULT_PDFS_DIR,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
)
@click.option(
    "--out",
    "out_file",
    default=DEFAULT_OUTPUT_PATH,
    type=click.Path(path_type=Path, dir_okay=False),
)
@click.option("--verbose", is_flag=True, help="Print per-file parsing details.")
def build_command(pdfs_dir: Path, out_file: Path, verbose: bool) -> None:
    """Discover statement PDFs, normalize them, and write transactions JSON."""
    pdf_paths = discover_pdf_paths(pdfs_dir)
    if not pdf_paths:
        raise click.ClickException(f"No PDF statements found under {pdfs_dir}")

    transfer_stats = TransferDedupeStats() if verbose else None
    try:
        transactions = build_transactions_from_pdfs(
            pdf_paths,
            transfer_stats=transfer_stats,
            verbose=verbose,
        )
    except SuspiciousOverlapError as exc:
        raise click.ClickException(str(exc)) from exc
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(dump_transactions_json(transactions), encoding="utf-8")

    if verbose:
        assert transfer_stats is not None
        transfer_pair_ids = {
            transaction.transfer_pair_id
            for transaction in transactions
            if transaction.transfer_pair_id is not None
        }
        transfer_pairs = len(transfer_pair_ids)
        single_sided_transfers = sum(
            transaction.is_transfer and transaction.transfer_pair_id is None
            for transaction in transactions
        )
        click.echo(f"Detected {transfer_pairs} transfer pairs")
        click.echo(f"Pass A: paired {transfer_stats.pass_a_pairs} transfer pairs")
        click.echo(f"Pass B: paired {transfer_stats.pass_b_pairs} transfer pairs")
        click.echo(f"Pass C: tagged {single_sided_transfers} rows single-sided")
        click.echo(f"Pass D: paired {transfer_stats.pass_d_pairs} reversal pairs")

    click.echo(f"Wrote {len(transactions)} transactions to {out_file}")


@app.command("inspect")
@click.argument("file", type=click.Path(exists=True, path_type=Path, dir_okay=False))
def inspect_command(file: Path) -> None:
    """Print high-level stats for a normalized transactions JSON file."""
    transactions = load_transactions_json(file)
    expense_transactions = [
        transaction
        for transaction in transactions
        if transaction.amount < 0
        and not transaction.is_transfer
        and not transaction.is_external_account
    ]
    total_expense = sum((-transaction.amount for transaction in expense_transactions), Decimal("0"))

    per_bank_totals: dict[str, Decimal] = {}
    per_bank_counts: dict[str, int] = {}
    uncategorized_totals: dict[str, Decimal] = {}
    uncategorized_counts: dict[str, int] = {}

    for transaction in expense_transactions:
        per_bank_totals[transaction.bank] = per_bank_totals.get(transaction.bank, Decimal("0")) + (
            -transaction.amount
        )
        per_bank_counts[transaction.bank] = per_bank_counts.get(transaction.bank, 0) + 1

        if transaction.category != "Прочее":
            continue
        uncategorized_totals[transaction.merchant_raw] = uncategorized_totals.get(
            transaction.merchant_raw,
            Decimal("0"),
        ) + (-transaction.amount)
        uncategorized_counts[transaction.merchant_raw] = (
            uncategorized_counts.get(
                transaction.merchant_raw,
                0,
            )
            + 1
        )

    click.echo(f"Transactions: {len(transactions)}")
    click.echo(
        f"Expense rows (excluding transfers and external accounts): {len(expense_transactions)}"
    )
    click.echo(
        "Expense total (excluding transfers and external accounts): "
        f"{format_rub(total_expense)} RUB"
    )
    click.echo("Per-bank expense totals:")

    if per_bank_totals:
        for bank in sorted(per_bank_totals):
            click.echo(
                "- "
                f"{bank}: {format_rub(per_bank_totals[bank])} RUB "
                f"across {per_bank_counts[bank]} rows"
            )
    else:
        click.echo("- none")

    click.echo("Top 20 uncategorized merchants:")
    if not uncategorized_totals:
        click.echo("- none")
        return

    ranked_uncategorized = sorted(
        uncategorized_totals,
        key=lambda merchant: (
            uncategorized_totals[merchant],
            uncategorized_counts[merchant],
            merchant,
        ),
        reverse=True,
    )
    for merchant in ranked_uncategorized[:20]:
        click.echo(
            "- "
            f"{merchant}: {format_rub(uncategorized_totals[merchant])} RUB "
            f"across {uncategorized_counts[merchant]} rows"
        )
