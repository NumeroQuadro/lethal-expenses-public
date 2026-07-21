import {
  selectExpenseHistogram,
  type ExpenseSelectorOptions,
} from '../lib/expenses'
import type { Transaction } from '../types/transaction'

interface ByDayBarsProps extends ExpenseSelectorOptions {
  transactions: Transaction[]
}

function formatRub(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value)
}

export function ByDayBars({ transactions, now, timeZone }: ByDayBarsProps) {
  const entries = selectExpenseHistogram(transactions, { now, timeZone })

  return (
    <section className="by-day-bars frame" aria-label="Траты по дням">
      <div className="by-day-bars__header">
        <div>
          <p className="by-day-bars__eyebrow">Daily Expense Rhythm</p>
          <h2 className="by-day-bars__title panel-title glow">ПО ДНЯМ</h2>
        </div>
      </div>

      <div className="by-day-bars__chart" role="img" aria-label="30-day expense histogram">
        {entries.map((entry) => (
          <div
            key={entry.day}
            className={`by-day-bars__column${entry.isToday ? ' is-today' : ''}`}
            title={`${entry.day}: ${formatRub(entry.totalExpense)} ₽`}
          >
            <div
              className="by-day-bars__fill"
              style={{ height: `${entry.heightPercentage}%` }}
            />
          </div>
        ))}
      </div>
    </section>
  )
}
