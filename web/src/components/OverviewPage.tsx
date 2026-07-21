import type { ExpenseState } from "../hooks/useExpenses";
import { ByDayBars } from "./ByDayBars";
import { CategoryBars } from "./CategoryBars";
import { Filters } from "./Filters";
import { Overview } from "./Overview";
import { RecentTransactions } from "./RecentTransactions";

interface OverviewPageProps {
  expenseState: ExpenseState;
}

export function OverviewPage({ expenseState }: OverviewPageProps) {
  return (
    <div className="dashboard-stack">
      <Overview
        transactions={expenseState.filteredTransactions}
        referenceTransactions={expenseState.periodReferenceTransactions}
        period={expenseState.period}
      />
      <Filters />
      <RecentTransactions transactions={expenseState.filteredTransactions} />
      <div className="dashboard-bottom">
        <CategoryBars transactions={expenseState.filteredTransactions} />
        <ByDayBars transactions={expenseState.filteredTransactions} />
      </div>
    </div>
  );
}
