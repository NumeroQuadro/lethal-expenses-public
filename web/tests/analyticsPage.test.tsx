import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalyticsPage } from "../src/components/AnalyticsPage";
import {
  selectAnalyticsExpenses,
  defaultExpenseFilters,
} from "../src/lib/expenses";
import { ANALYTICS_TRANSACTIONS } from "./fixtures/analyticsTransactions";

const NOW = new Date("2026-04-30T12:00:00+03:00");
const OPTIONS = {
  now: NOW,
  timeZone: "Europe/Moscow",
};

describe("AnalyticsPage", () => {
  it("renders the all-time analytics layout", () => {
    const transactions = selectAnalyticsExpenses(
      ANALYTICS_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    const { container } = render(
      <AnalyticsPage
        transactions={transactions}
        now={NOW}
        timeZone="Europe/Moscow"
      />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("updates the drill-down when a category is selected", () => {
    const transactions = selectAnalyticsExpenses(
      ANALYTICS_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    render(
      <AnalyticsPage
        transactions={transactions}
        now={NOW}
        timeZone="Europe/Moscow"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Еда" }));

    expect(screen.getByRole("button", { name: "Еда" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    const drilldown = screen.getByLabelText("Категории по месяцам");
    expect(within(drilldown).getByText("ФЕВРАЛЬ 2026")).toBeInTheDocument();
    expect(within(drilldown).getByText("ЯНВАРЬ 2026")).toBeInTheDocument();
  });

  it("expands and collapses a month row with inline category and merchant breakdowns", () => {
    const transactions = selectAnalyticsExpenses(
      ANALYTICS_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    render(
      <AnalyticsPage
        transactions={transactions}
        now={NOW}
        timeZone="Europe/Moscow"
      />,
    );

    const aprilButton = screen.getByRole("button", { name: /АПРЕЛЬ 2026/i });
    fireEvent.click(aprilButton);

    expect(aprilButton).toHaveAttribute("aria-expanded", "true");

    const monthCategories = screen.getByLabelText("Категории АПРЕЛЬ 2026");
    const monthMerchants = screen.getByLabelText("Мерчанты АПРЕЛЬ 2026");

    expect(within(monthCategories).getByText("Покупки")).toBeInTheDocument();
    expect(within(monthMerchants).getByText("OZON")).toBeInTheDocument();

    fireEvent.click(aprilButton);

    expect(aprilButton).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.queryByLabelText("Категории АПРЕЛЬ 2026"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Мерчанты АПРЕЛЬ 2026"),
    ).not.toBeInTheDocument();
  });
});
