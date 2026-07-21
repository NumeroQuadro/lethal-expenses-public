import type { ReactNode } from 'react'

import type { ExpenseState } from '../hooks/useExpenses'
import { ExpenseDashboardContext } from './expenseDashboardContext'

interface ExpenseDashboardProviderProps {
  children: ReactNode
  value: ExpenseState
}

export function ExpenseDashboardProvider({
  children,
  value,
}: ExpenseDashboardProviderProps) {
  return (
    <ExpenseDashboardContext.Provider value={value}>
      {children}
    </ExpenseDashboardContext.Provider>
  )
}
