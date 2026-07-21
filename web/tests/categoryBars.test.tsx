import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CategoryBars } from '../src/components/CategoryBars'
import { defaultExpenseFilters, selectFilteredExpenses } from '../src/lib/expenses'
import {
  DASHBOARD_NOW,
  DASHBOARD_TIME_ZONE,
  DASHBOARD_TRANSACTIONS,
} from './fixtures/dashboardTransactions'

describe('CategoryBars', () => {
  it('renders sorted category totals for the active filtered set', () => {
    const filteredTransactions = selectFilteredExpenses(
      DASHBOARD_TRANSACTIONS,
      defaultExpenseFilters,
      {
        now: DASHBOARD_NOW,
        timeZone: DASHBOARD_TIME_ZONE,
      },
    )

    const { container } = render(
      <CategoryBars transactions={filteredTransactions} />,
    )

    const rows = [...container.querySelectorAll('.category-bars__row')]
    expect(rows).toHaveLength(4)
    expect(rows.map((row) => row.querySelector('.category-bars__name')?.textContent)).toEqual([
      'Еда',
      'Покупки',
      'Кафе',
      'Транспорт',
    ])
    expect(rows[0]?.textContent ?? '').toMatch(/1.?200,00 ₽/)
    expect(rows[1]?.textContent ?? '').toMatch(/870,00 ₽/)
  })

  it('renders an explicit empty state when no expenses are available', () => {
    render(<CategoryBars transactions={[]} />)

    expect(screen.getByText('Нет трат для выбранных фильтров.')).toBeInTheDocument()
  })
})
