import { useState } from "react";

import { AnalyticsPage } from "./components/AnalyticsPage";
import { CategoriesPage } from "./components/CategoriesPage";
import { OverviewPage } from "./components/OverviewPage";
import { PlaceholderView } from "./components/PlaceholderView";
import { SettingsPage } from "./components/SettingsPage";
import { Sidebar, type DashboardView } from "./components/Sidebar";
import { ExpenseDashboardProvider } from "./context/expenseDashboard";
import { transactions } from "./data/transactions";
import { useExpenses } from "./hooks/useExpenses";
import "./styles/app.css";

const TRANSACTIONS_PLACEHOLDER_COPY =
  "Full transactions surface will branch out from the same static data flow, but this batch keeps the work focused on analytics.";

function App() {
  const [currentView, setCurrentView] = useState<DashboardView>("overview");
  const expenseState = useExpenses(transactions);

  let content;

  switch (currentView) {
    case "overview":
      content = <OverviewPage expenseState={expenseState} />;
      break;
    case "analytics":
      content = (
        <AnalyticsPage transactions={expenseState.analyticsTransactions} />
      );
      break;
    case "categories":
      content = <CategoriesPage />;
      break;
    case "settings":
      content = <SettingsPage />;
      break;
    case "transactions":
      content = (
        <PlaceholderView title="ТРАТЫ" copy={TRANSACTIONS_PLACEHOLDER_COPY} />
      );
      break;
  }

  return (
    <ExpenseDashboardProvider value={expenseState}>
      <div className="app-shell">
        <Sidebar currentView={currentView} onSelectView={setCurrentView} />

        <main className="app-outlet">{content}</main>
      </div>
    </ExpenseDashboardProvider>
  );
}

export default App;
