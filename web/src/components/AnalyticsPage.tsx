import {
  selectAnalyticsSummary,
  selectExpensesByMonth,
  type ExpenseSelectorOptions,
} from "../lib/expenses";
import type { Transaction } from "../types/transaction";
import { AnalyticsSummaryCards } from "./AnalyticsSummaryCards";
import { CategoryBars } from "./CategoryBars";
import { CategoryDrilldown } from "./CategoryDrilldown";
import { MonthlyBars } from "./MonthlyBars";
import { TopMerchants } from "./TopMerchants";

interface AnalyticsPageProps extends ExpenseSelectorOptions {
  transactions: Transaction[];
}

export function AnalyticsPage({
  transactions,
  now,
  timeZone,
}: AnalyticsPageProps) {
  const selectorOptions = { now, timeZone };
  const summary = selectAnalyticsSummary(transactions, selectorOptions);
  const monthlyEntries = selectExpensesByMonth(transactions, selectorOptions);

  return (
    <section className="analytics-page" aria-label="Аналитика">
      <header className="analytics-page__header">
        <p className="analytics-page__eyebrow">Lethal Expenses</p>
        <h1 className="analytics-page__title panel-title glow">АНАЛИТИКА</h1>
        <p className="analytics-page__copy">
          All-time retrospective view. Периодные чипы сюда не вмешиваются, но
          скрытие переводов и внешних счетов остаётся в силе.
        </p>
      </header>

      <AnalyticsSummaryCards summary={summary} />
      <MonthlyBars
        entries={monthlyEntries}
        transactions={transactions}
        now={now}
        timeZone={timeZone}
      />

      <div className="analytics-page__grid">
        <CategoryBars transactions={transactions} />
        <TopMerchants transactions={transactions} />
      </div>

      <CategoryDrilldown
        transactions={transactions}
        now={now}
        timeZone={timeZone}
      />
    </section>
  );
}
