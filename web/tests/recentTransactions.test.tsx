import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RecentTransactions } from '../src/components/RecentTransactions'
import type { Transaction } from '../src/types/transaction'

const RECENT_TRANSACTIONS_FIXTURE: Transaction[] = [
  {
    id: 'recent-1',
    date: '2026-04-24T20:15:00+03:00',
    amount: '-199.99',
    currency: 'RUB',
    merchant_raw: 'Кофейня',
    description: 'Вечерний кофе',
    bank: 'yandex',
    account: '****1111',
    precision: 'minute',
    category: 'Кафе',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: 'recent-2',
    date: '2026-04-24T09:30:00+03:00',
    amount: '-1240.00',
    currency: 'RUB',
    merchant_raw: 'Пятёрочка',
    description: 'Продукты на неделю',
    bank: 'sberbank',
    account: '****2222',
    precision: 'minute',
    category: 'Еда',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: 'recent-3',
    date: '2026-04-23T18:10:00+03:00',
    amount: '-89.50',
    currency: 'RUB',
    merchant_raw: 'Метро',
    description: 'Пополнение транспортной карты',
    bank: 'spb',
    account: '****3333',
    precision: 'minute',
    category: 'Транспорт',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: 'recent-4',
    date: '2026-04-20T12:00:00+03:00',
    amount: '-450.00',
    currency: 'RUB',
    merchant_raw: 'Сервисы Яндекса',
    description: 'Подписка',
    bank: 'ozon',
    account: '****4444',
    precision: 'minute',
    category: 'Подписки',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: 'recent-5',
    date: '2026-04-18T08:45:00+03:00',
    amount: '-3000.00',
    currency: 'RUB',
    merchant_raw: 'DNS',
    description: 'Покупка техники',
    bank: 'yandex',
    account: '****5555',
    precision: 'minute',
    category: 'Покупки',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: 'recent-6',
    date: '2026-04-17T11:05:00+03:00',
    amount: '-120.00',
    currency: 'RUB',
    merchant_raw: 'Аптека',
    description: 'Лекарства',
    bank: 'sberbank',
    account: '****6666',
    precision: 'minute',
    category: 'Здоровье',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
]

function buildPaginatedTransactions(count: number): Transaction[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `page-${index + 1}`,
    date: `2026-04-${String(30 - Math.min(index, 29)).padStart(2, '0')}T12:${String(index % 60).padStart(2, '0')}:00+03:00`,
    amount: `-${(index + 1).toFixed(2)}`,
    currency: 'RUB',
    merchant_raw: `Магазин ${index + 1}`,
    description: `Покупка ${index + 1}`,
    bank: 'sberbank',
    account: '****1111',
    precision: 'minute',
    category: 'Прочее',
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  }))
}

describe('RecentTransactions', () => {
  it('renders the default collapsed recent-expense table', () => {
    const { container } = render(
      <RecentTransactions transactions={RECENT_TRANSACTIONS_FIXTURE} />,
    )

    expect(container.firstChild).toMatchSnapshot()
  })

  it('renders an explicit empty state for empty filtered results', () => {
    render(<RecentTransactions transactions={[]} />)

    expect(screen.getByText('Нет трат для выбранных фильтров.')).toBeInTheDocument()
  })

  it('expands and paginates long transaction lists', () => {
    render(<RecentTransactions transactions={buildPaginatedTransactions(55)} />)

    fireEvent.click(screen.getByRole('button', { name: 'ПОКАЗАТЬ ВСЕ ТРАТЫ' }))
    expect(screen.getByText('СТРАНИЦА 1 / 2')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(51)

    fireEvent.click(screen.getByRole('button', { name: 'ДАЛЬШЕ' }))
    expect(screen.getByText('СТРАНИЦА 2 / 2')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(6)
  })
})
