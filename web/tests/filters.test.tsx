import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Filters } from "../src/components/Filters";
import { Overview } from "../src/components/Overview";
import { ExpenseDashboardProvider } from "../src/context/expenseDashboard";
import { useExpenses } from "../src/hooks/useExpenses";
import type { Transaction } from "../src/types/transaction";
import {
  DASHBOARD_NOW,
  DASHBOARD_QUOTA,
  DASHBOARD_TIME_ZONE,
  DASHBOARD_TRANSACTIONS,
} from "./fixtures/dashboardTransactions";

const EXTERNAL_AUDIT_ROW: Transaction = {
  id: "smoke-external",
  date: "2026-04-26T16:45:00+03:00",
  amount: "-900.00",
  currency: "RUB",
  merchant_raw: "External relay expense",
  description: "Relay-only external account row",
  bank: "sberbank",
  account: "****4000",
  precision: "minute",
  category: "Прочее",
  is_transfer: false,
  is_external_account: true,
  transfer_pair_id: null,
  raw: {},
};

interface FiltersHarnessProps {
  transactions?: Transaction[];
}

function FiltersHarness({
  transactions = DASHBOARD_TRANSACTIONS,
}: FiltersHarnessProps) {
  const state = useExpenses(transactions, {
    now: DASHBOARD_NOW,
    timeZone: DASHBOARD_TIME_ZONE,
  });

  return (
    <ExpenseDashboardProvider value={state}>
      <Overview
        period={state.period}
        referenceTransactions={state.periodReferenceTransactions}
        transactions={state.filteredTransactions}
        now={DASHBOARD_NOW}
        quotaRub={DASHBOARD_QUOTA}
        timeZone={DASHBOARD_TIME_ZONE}
      />
      <Filters />
      <output data-testid="filtered-total">{state.totalExpense}</output>
      <output data-testid="filtered-ids">
        {state.filteredTransactions
          .map((transaction) => transaction.id)
          .join(",")}
      </output>
    </ExpenseDashboardProvider>
  );
}

describe("Filters", () => {
  it("updates overview totals and filtered rows through dashboard state", () => {
    render(<FiltersHarness />);

    expect(screen.getByTestId("filtered-total")).toHaveTextContent("2600");
    expect(screen.getByTestId("overview-spent-value")).toHaveTextContent("2");
    expect(
      screen.getByRole("switch", { name: "СКРЫТЬ ПЕРЕВОДЫ" }),
    ).toHaveAttribute("aria-checked", "true");

    fireEvent.click(screen.getByRole("switch", { name: "СКРЫТЬ ПЕРЕВОДЫ" }));
    expect(screen.getByTestId("filtered-total")).toHaveTextContent("7600");
    expect(
      screen.getByRole("switch", { name: "СКРЫТЬ ПЕРЕВОДЫ" }),
    ).toHaveAttribute("aria-checked", "false");

    fireEvent.click(screen.getByRole("button", { name: "СЕГОДНЯ" }));
    expect(screen.getByTestId("filtered-total")).toHaveTextContent("1550");
    expect(screen.getByTestId("filtered-ids")).toHaveTextContent(
      "smoke-2,smoke-1",
    );
    expect(screen.getByText(/за день/)).toBeInTheDocument();

    const monthCard = screen.getByText("В ЭТОМ МЕСЯЦЕ").closest("article");
    expect(monthCard).not.toBeNull();
    expect(monthCard).toHaveTextContent(/7\s600,00 ₽/);

    fireEvent.click(screen.getByRole("button", { name: "Еда" }));
    expect(screen.getByTestId("filtered-total")).toHaveTextContent("1200");
    expect(screen.getByTestId("filtered-ids")).toHaveTextContent("smoke-1");

    fireEvent.click(screen.getByRole("button", { name: "ВСЕ" }));
    expect(screen.getByTestId("filtered-total")).toHaveTextContent("1550");
  });

  it("renders a stable empty-state control surface", () => {
    render(<FiltersHarness transactions={[]} />);

    const categoryGroup = screen.getByRole("group", { name: "Категории" });
    expect(screen.getByTestId("filtered-total")).toHaveTextContent("0");
    expect(screen.getByRole("button", { name: "ВСЕ" })).toBeInTheDocument();
    expect(categoryGroup).toHaveTextContent("ВСЕ");
    expect(
      screen.queryByRole("button", { name: "Еда" }),
    ).not.toBeInTheDocument();
  });

  it("reveals external-account rows only when the audit toggle is enabled", () => {
    render(
      <FiltersHarness
        transactions={[...DASHBOARD_TRANSACTIONS, EXTERNAL_AUDIT_ROW]}
      />,
    );

    expect(screen.getByTestId("filtered-total")).toHaveTextContent("2600");
    expect(screen.getByTestId("filtered-ids")).not.toHaveTextContent(
      "smoke-external",
    );
    expect(
      screen.getByRole("switch", { name: "ПОКАЗАТЬ ВНЕШНИЕ СЧЕТА" }),
    ).toHaveAttribute("aria-checked", "false");

    fireEvent.click(
      screen.getByRole("switch", { name: "ПОКАЗАТЬ ВНЕШНИЕ СЧЕТА" }),
    );

    expect(screen.getByTestId("filtered-total")).toHaveTextContent("3500");
    expect(screen.getByTestId("filtered-ids")).toHaveTextContent(
      "smoke-external",
    );
    expect(
      screen.getByRole("switch", { name: "ПОКАЗАТЬ ВНЕШНИЕ СЧЕТА" }),
    ).toHaveAttribute("aria-checked", "true");
  });
});
