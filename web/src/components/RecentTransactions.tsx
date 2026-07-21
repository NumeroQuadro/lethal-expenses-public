import { useState } from 'react'

import { DASHBOARD_TIME_ZONE } from '../config'
import { selectRecentExpenses } from '../lib/expenses'
import type { Transaction } from '../types/transaction'

interface RecentTransactionsProps {
  timeZone?: string
  transactions: Transaction[]
}

const COLLAPSED_ROW_COUNT = 5
const PAGE_SIZE = 50

function formatAmount(amount: string): string {
  const value = Math.abs(Number(amount))

  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value)
}

function formatDate(value: string, timeZone = DASHBOARD_TIME_ZONE): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: '2-digit',
    timeZone,
    year: 'numeric',
  }).format(new Date(value))
}

export function RecentTransactions({
  timeZone = DASHBOARD_TIME_ZONE,
  transactions,
}: RecentTransactionsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [page, setPage] = useState(0)

  const sortedTransactions = selectRecentExpenses(transactions, transactions.length)
  const totalPages = Math.max(1, Math.ceil(sortedTransactions.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages - 1)
  const paginatedTransactions = sortedTransactions.slice(
    currentPage * PAGE_SIZE,
    currentPage * PAGE_SIZE + PAGE_SIZE,
  )
  const visibleTransactions = isExpanded
    ? paginatedTransactions
    : sortedTransactions.slice(0, COLLAPSED_ROW_COUNT)

  return (
    <section className="recent-transactions frame" aria-label="Последние траты">
      <div className="recent-transactions__header">
        <div>
          <p className="recent-transactions__eyebrow">Latest Expense Rows</p>
          <h2 className="recent-transactions__title panel-title glow">ПОСЛЕДНИЕ ТРАТЫ</h2>
        </div>

        {sortedTransactions.length > COLLAPSED_ROW_COUNT ? (
          <button
            type="button"
            className="recent-transactions__toggle"
            onClick={() => setIsExpanded((current) => !current)}
          >
            {isExpanded ? 'ПОКАЗАТЬ МЕНЬШЕ' : 'ПОКАЗАТЬ ВСЕ ТРАТЫ'}
          </button>
        ) : null}
      </div>

      {visibleTransactions.length > 0 ? (
        <div className="recent-transactions__table-wrap">
          <table className="recent-table">
            <thead>
              <tr>
                <th scope="col">ДАТА</th>
                <th scope="col">ОПИСАНИЕ</th>
                <th scope="col">КАТЕГОРИЯ</th>
                <th scope="col">СУММА</th>
              </tr>
            </thead>

            <tbody>
              {visibleTransactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td>{formatDate(transaction.date, timeZone)}</td>
                  <td>
                    <div className="recent-table__description">
                      <span className="recent-table__merchant">{transaction.merchant_raw}</span>
                      <span className="recent-table__details">{transaction.description}</span>
                    </div>
                  </td>
                  <td>{transaction.category}</td>
                  <td className="recent-table__amount">-{formatAmount(transaction.amount)} ₽</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="recent-transactions__empty">Нет трат для выбранных фильтров.</p>
      )}

      {isExpanded && totalPages > 1 ? (
        <div className="recent-transactions__pagination">
          <button
            type="button"
            className="recent-transactions__page-button"
            disabled={currentPage === 0}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
          >
            НАЗАД
          </button>

          <span className="recent-transactions__page-indicator">
            СТРАНИЦА {currentPage + 1} / {totalPages}
          </span>

          <button
            type="button"
            className="recent-transactions__page-button"
            disabled={currentPage >= totalPages - 1}
            onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}
          >
            ДАЛЬШЕ
          </button>
        </div>
      ) : null}
    </section>
  )
}
