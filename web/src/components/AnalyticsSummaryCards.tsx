import type { AnalyticsSummary } from "../lib/expenses";

interface AnalyticsSummaryCardsProps {
  summary: AnalyticsSummary;
}

function formatRub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
  }).format(value);
}

export function AnalyticsSummaryCards({ summary }: AnalyticsSummaryCardsProps) {
  return (
    <div className="analytics-summary" data-testid="analytics-summary">
      <article className="analytics-card frame">
        <p className="analytics-card__label panel-title">ВСЕГО</p>
        <p className="analytics-card__value glow">
          {formatRub(summary.totalExpense)} ₽
        </p>
        <p className="analytics-card__meta">all-time расход</p>
      </article>

      <article className="analytics-card frame">
        <p className="analytics-card__label panel-title">СРЕДН/МЕС</p>
        <p className="analytics-card__value glow">
          {formatRub(summary.monthlyAverageExpense)} ₽
        </p>
        <p className="analytics-card__meta">по месяцам с тратами</p>
      </article>

      <article className="analytics-card frame">
        <p className="analytics-card__label panel-title">ТОП КАТ-Я</p>
        <p className="analytics-card__value glow analytics-card__value--compact">
          {summary.topCategoryName}
        </p>
        <p className="analytics-card__meta">
          {formatPercent(summary.topCategorySharePercentage)}% без переводов
        </p>
      </article>

      <article className="analytics-card frame">
        <p className="analytics-card__label panel-title">МАКС МЕСЯЦ</p>
        <p className="analytics-card__value glow analytics-card__value--compact">
          {summary.peakMonthLabel}
        </p>
        <p className="analytics-card__meta">
          {formatRub(summary.peakMonthTotalExpense)} ₽
        </p>
      </article>
    </div>
  );
}
