import { selectExpensesByMerchant } from '../lib/expenses'
import { pluralRu } from '../lib/pluralRu'
import type { Transaction } from '../types/transaction'

interface TopMerchantsProps {
  transactions: Transaction[]
  limit?: number
}

function formatRub(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value)
}

export function TopMerchants({ transactions, limit = 20 }: TopMerchantsProps) {
  const entries = selectExpensesByMerchant(transactions, limit)

  return (
    <section className="top-merchants frame" aria-label="Топ мерчантов">
      <div className="top-merchants__header">
        <div>
          <p className="top-merchants__eyebrow">Merchant Leaders</p>
          <h2 className="top-merchants__title panel-title glow">ТОП МЕРЧАНТОВ</h2>
        </div>
      </div>

      {entries.length > 0 ? (
        <ol className="top-merchants__list">
          {entries.map((entry, index) => (
            <li key={entry.merchant} className="top-merchants__row">
              <span className="top-merchants__rank">{index + 1}.</span>
              <span className="top-merchants__merchant">{entry.merchant}</span>
              <span className="top-merchants__count">
                {entry.transactionCount}{' '}
                {pluralRu(entry.transactionCount, ['трата', 'траты', 'трат'])}
              </span>
              <span className="top-merchants__total">{formatRub(entry.totalExpense)} ₽</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="top-merchants__empty">Нет мерчантов для отображения.</p>
      )}
    </section>
  )
}
