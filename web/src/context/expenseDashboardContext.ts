import { createContext, useContext } from 'react'

import type { ExpenseState } from '../hooks/useExpenses'

export const ExpenseDashboardContext = createContext<ExpenseState | null>(null)

export function useExpenseDashboard(): ExpenseState {
  const value = useContext(ExpenseDashboardContext)

  if (!value) {
    throw new Error('useExpenseDashboard must be used within ExpenseDashboardProvider')
  }

  return value
}
