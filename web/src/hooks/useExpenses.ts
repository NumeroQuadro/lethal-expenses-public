import { useReducer } from "react";

import {
  defaultExpenseFilters,
  selectAnalyticsExpenses,
  selectAvailableCategories,
  selectExpensesByCategory,
  selectExpensesByDay,
  selectFilteredExpenses,
  selectRecentExpenses,
  selectTotalExpense,
  type CategoryExpense,
  type DayExpense,
  type ExpenseFilters,
  type ExpensePeriod,
  type ExpenseSelectorOptions,
} from "../lib/expenses";
import type { Transaction } from "../types/transaction";

type ExpenseAction =
  | { type: "set-period"; period: ExpensePeriod }
  | { type: "set-hide-transfers"; hideTransfers: boolean }
  | { type: "set-show-external-accounts"; showExternalAccounts: boolean }
  | { type: "set-category-filter"; categoryFilter: string[] }
  | { type: "toggle-category"; category: string }
  | { type: "clear-category-filter" };

export interface ExpenseState {
  filters: ExpenseFilters;
  period: ExpensePeriod;
  selectorOptions: ExpenseSelectorOptions;
  filteredTransactions: Transaction[];
  periodScopedTransactions: Transaction[];
  periodReferenceTransactions: Transaction[];
  analyticsTransactions: Transaction[];
  availableCategories: string[];
  totalExpense: number;
  expensesByCategory: CategoryExpense[];
  expensesByDay: DayExpense[];
  recent: (count: number) => Transaction[];
  setPeriod: (period: ExpensePeriod) => void;
  setHideTransfers: (hideTransfers: boolean) => void;
  setShowExternalAccounts: (showExternalAccounts: boolean) => void;
  setCategoryFilter: (categoryFilter: string[]) => void;
  toggleCategory: (category: string) => void;
  clearCategoryFilter: () => void;
}

function normalizeCategoryFilter(categoryFilter: string[]): string[] {
  return [
    ...new Set(
      categoryFilter.filter((category) => category && category !== "ВСЕ"),
    ),
  ];
}

function expenseFiltersReducer(
  state: ExpenseFilters,
  action: ExpenseAction,
): ExpenseFilters {
  switch (action.type) {
    case "set-period":
      return { ...state, period: action.period };
    case "set-hide-transfers":
      return { ...state, hideTransfers: action.hideTransfers };
    case "set-show-external-accounts":
      return { ...state, showExternalAccounts: action.showExternalAccounts };
    case "set-category-filter":
      return {
        ...state,
        categoryFilter: normalizeCategoryFilter(action.categoryFilter),
      };
    case "toggle-category": {
      const nextCategories = state.categoryFilter.includes(action.category)
        ? state.categoryFilter.filter(
            (category) => category !== action.category,
          )
        : [...state.categoryFilter, action.category];

      return {
        ...state,
        categoryFilter: normalizeCategoryFilter(nextCategories),
      };
    }
    case "clear-category-filter":
      return { ...state, categoryFilter: [] };
    default:
      return state;
  }
}

export function useExpenses(
  transactions: Transaction[],
  options?: ExpenseSelectorOptions,
): ExpenseState {
  const [filters, dispatch] = useReducer(
    expenseFiltersReducer,
    undefined,
    () => ({
      ...defaultExpenseFilters,
      categoryFilter: [],
    }),
  );

  const periodScopedTransactions = selectFilteredExpenses(
    transactions,
    {
      ...filters,
      categoryFilter: [],
    },
    options,
  );
  const periodReferenceTransactions = selectFilteredExpenses(
    transactions,
    {
      ...filters,
      period: "all",
    },
    options,
  );
  const analyticsTransactions = selectAnalyticsExpenses(
    transactions,
    filters,
    options,
  );
  const filteredTransactions = selectFilteredExpenses(
    transactions,
    filters,
    options,
  );

  return {
    filters,
    period: filters.period,
    selectorOptions: {
      now: options?.now,
      timeZone: options?.timeZone,
    },
    filteredTransactions,
    periodScopedTransactions,
    periodReferenceTransactions,
    analyticsTransactions,
    availableCategories: selectAvailableCategories(periodScopedTransactions),
    totalExpense: selectTotalExpense(filteredTransactions),
    expensesByCategory: selectExpensesByCategory(filteredTransactions),
    expensesByDay: selectExpensesByDay(filteredTransactions, options),
    recent: (count: number) =>
      selectRecentExpenses(filteredTransactions, count),
    setPeriod: (period: ExpensePeriod) =>
      dispatch({ type: "set-period", period }),
    setHideTransfers: (hideTransfers: boolean) =>
      dispatch({ type: "set-hide-transfers", hideTransfers }),
    setShowExternalAccounts: (showExternalAccounts: boolean) =>
      dispatch({ type: "set-show-external-accounts", showExternalAccounts }),
    setCategoryFilter: (categoryFilter: string[]) =>
      dispatch({ type: "set-category-filter", categoryFilter }),
    toggleCategory: (category: string) =>
      dispatch({ type: "toggle-category", category }),
    clearCategoryFilter: () => dispatch({ type: "clear-category-filter" }),
  };
}
