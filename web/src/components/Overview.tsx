import { MONTHLY_QUOTA_RUB } from "../config";
import {
  quotaForPeriod,
  selectTransactionsByPeriod,
  selectTotalExpense,
  type ExpensePeriod,
  type ExpenseSelectorOptions,
} from "../lib/expenses";
import { pluralRu } from "../lib/pluralRu";
import type { Transaction } from "../types/transaction";
import { QuotaBar } from "./QuotaBar";

interface OverviewProps extends ExpenseSelectorOptions {
  period: ExpensePeriod;
  referenceTransactions: Transaction[];
  transactions: Transaction[];
  quotaRub?: number;
}

function formatRub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatQuotaRub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
  }).format(value);
}

function quotaPeriodLabel(period: ExpensePeriod): string {
  switch (period) {
    case "month":
      return "за месяц";
    case "30d":
      return "за 30 дней";
    case "7d":
      return "за 7 дней";
    case "today":
      return "за день";
    case "all":
      return "";
  }
}

export function Overview({
  period,
  referenceTransactions,
  transactions,
  now,
  quotaRub = MONTHLY_QUOTA_RUB,
  timeZone,
}: OverviewProps) {
  const resolvedNow = now ?? new Date();
  const resolvedTimeZone =
    timeZone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const selectorOptions = { now: resolvedNow, timeZone: resolvedTimeZone };
  const todayTransactions = selectTransactionsByPeriod(
    referenceTransactions,
    "today",
    selectorOptions,
  );
  const monthTransactions = selectTransactionsByPeriod(
    referenceTransactions,
    "month",
    selectorOptions,
  );

  const quotaForThisPeriod = quotaForPeriod(
    period,
    quotaRub,
    resolvedNow,
    resolvedTimeZone,
  );
  const spentInPeriod = selectTotalExpense(transactions);
  const spentToday = selectTotalExpense(todayTransactions);
  const spentThisMonth = selectTotalExpense(monthTransactions);
  const todayExpenseCount = todayTransactions.length;
  const monthExpenseCount = monthTransactions.length;
  const remaining =
    quotaForThisPeriod === null ? null : quotaForThisPeriod - spentInPeriod;
  const spentPercentage =
    quotaForThisPeriod && quotaForThisPeriod > 0
      ? (spentInPeriod / quotaForThisPeriod) * 100
      : 0;
  const remainingPercentage =
    quotaForThisPeriod && quotaForThisPeriod > 0 && remaining !== null
      ? (remaining / quotaForThisPeriod) * 100
      : 0;
  const isQuotaExceeded =
    quotaForThisPeriod !== null &&
    quotaForThisPeriod > 0 &&
    spentInPeriod > quotaForThisPeriod;

  return (
    <section className="overview" aria-label="Обзор">
      <header className="overview__header">
        <p className="overview__eyebrow">Lethal Expenses</p>
        <h1 className="overview__title panel-title glow">ОБЗОР</h1>
      </header>

      <div className="overview__cards">
        <article className="overview-card frame">
          <p className="overview-card__label panel-title">ПОТРАЧЕНО</p>
          <p
            className="overview-card__value glow"
            data-testid="overview-spent-value"
          >
            {formatRub(spentInPeriod)} ₽
          </p>
          {quotaForThisPeriod === null ? null : (
            <p className="overview-card__meta">
              / {formatQuotaRub(quotaForThisPeriod)} ₽{" "}
              {quotaPeriodLabel(period)}
            </p>
          )}
          {isQuotaExceeded ? (
            <p className="overview-card__alarm glow">QUOTA EXCEEDED</p>
          ) : null}
          {quotaForThisPeriod === null ? null : (
            <QuotaBar percentage={spentPercentage} />
          )}
        </article>

        {quotaForThisPeriod === null || remaining === null ? null : (
          <article className="overview-card frame">
            <p className="overview-card__label panel-title">ОСТАЛОСЬ</p>
            <p className="overview-card__value glow">
              {formatRub(remaining)} ₽
            </p>
            <p className="overview-card__meta">
              {formatPercent(remainingPercentage)}% квоты
            </p>
          </article>
        )}

        <article className="overview-card frame">
          <p className="overview-card__label panel-title">СЕГОДНЯ</p>
          <p className="overview-card__value glow">{formatRub(spentToday)} ₽</p>
          <p className="overview-card__meta">
            {todayExpenseCount}{" "}
            {pluralRu(todayExpenseCount, ["трата", "траты", "трат"])}
          </p>
        </article>

        <article className="overview-card frame">
          <p className="overview-card__label panel-title">В ЭТОМ МЕСЯЦЕ</p>
          <p className="overview-card__value glow">
            {formatRub(spentThisMonth)} ₽
          </p>
          <p className="overview-card__meta">
            {monthExpenseCount}{" "}
            {pluralRu(monthExpenseCount, ["трата", "траты", "трат"])}
          </p>
        </article>
      </div>
    </section>
  );
}
