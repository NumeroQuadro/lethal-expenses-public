import {
  selectCategoryBreakdown,
  type CategoryBreakdownEntry,
} from '../lib/expenses'
import type { Transaction } from '../types/transaction'

interface CategoryBarsProps {
  transactions: Transaction[]
}

function formatRub(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
  }).format(value)
}

function renderRow(entry: CategoryBreakdownEntry) {
  return (
    <div key={entry.category} className="category-bars__row">
      <p className="category-bars__name">{entry.category}</p>

      <div className="category-bars__bar" aria-hidden="true">
        <div
          className="category-bars__fill"
          style={{ width: `${entry.widthPercentage}%` }}
        />
      </div>

      <p className="category-bars__value">
        {formatRub(entry.totalExpense)} ₽ ({formatPercent(entry.sharePercentage)}%)
      </p>
    </div>
  )
}

export function CategoryBars({ transactions }: CategoryBarsProps) {
  const entries = selectCategoryBreakdown(transactions)

  return (
    <section className="category-bars frame" aria-label="Траты по категориям">
      <div className="category-bars__header">
        <div>
          <p className="category-bars__eyebrow">Expense Breakdown</p>
          <h2 className="category-bars__title panel-title glow">ТРАТЫ ПО КАТЕГОРИЯМ</h2>
        </div>
      </div>

      {entries.length > 0 ? (
        <div className="category-bars__list">{entries.map(renderRow)}</div>
      ) : (
        <p className="category-bars__empty">Нет трат для выбранных фильтров.</p>
      )}
    </section>
  )
}
