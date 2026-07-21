import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DASHBOARD_TRANSACTIONS } from './fixtures/dashboardTransactions'

vi.mock('../src/data/transactions', () => ({
  transactions: DASHBOARD_TRANSACTIONS,
}))

import App from '../src/App'

describe('App navigation', () => {
  it('switches views from the sidebar', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'ОБЗОР' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Аналитика' }))
    expect(screen.getByRole('heading', { name: 'АНАЛИТИКА' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Настройки' }))
    expect(screen.getByRole('heading', { name: 'НАСТРОЙКИ' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Траты' }))
    expect(screen.getByRole('heading', { name: 'ТРАТЫ' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Категории' }))
    expect(screen.getByRole('heading', { name: 'КАТЕГОРИИ' })).toBeInTheDocument()
  })
})
