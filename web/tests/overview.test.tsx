import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Overview } from "../src/components/Overview";
import {
  defaultExpenseFilters,
  selectFilteredExpenses,
} from "../src/lib/expenses";
import { pluralRu } from "../src/lib/pluralRu";
import {
  DASHBOARD_NOW,
  DASHBOARD_QUOTA,
  DASHBOARD_TIME_ZONE,
  DASHBOARD_TRANSACTIONS,
} from "./fixtures/dashboardTransactions";

describe("pluralRu", () => {
  it("picks the correct russian plural form", () => {
    expect(pluralRu(1, ["трата", "траты", "трат"])).toBe("трата");
    expect(pluralRu(2, ["трата", "траты", "трат"])).toBe("траты");
    expect(pluralRu(5, ["трата", "траты", "трат"])).toBe("трат");
    expect(pluralRu(11, ["трата", "траты", "трат"])).toBe("трат");
    expect(pluralRu(21, ["трата", "траты", "трат"])).toBe("трата");
    expect(pluralRu(24, ["трата", "траты", "трат"])).toBe("траты");
    expect(pluralRu(112, ["трата", "траты", "трат"])).toBe("трат");
  });
});

describe("Overview", () => {
  it("renders the top overview cards from the active filtered transaction set", () => {
    const referenceTransactions = selectFilteredExpenses(
      DASHBOARD_TRANSACTIONS,
      {
        ...defaultExpenseFilters,
        period: "all",
      },
      {
        now: DASHBOARD_NOW,
        timeZone: DASHBOARD_TIME_ZONE,
      },
    );
    const filteredTransactions = selectFilteredExpenses(
      DASHBOARD_TRANSACTIONS,
      defaultExpenseFilters,
      {
        now: DASHBOARD_NOW,
        timeZone: DASHBOARD_TIME_ZONE,
      },
    );

    const { container } = render(
      <Overview
        period="month"
        referenceTransactions={referenceTransactions}
        transactions={filteredTransactions}
        now={DASHBOARD_NOW}
        quotaRub={DASHBOARD_QUOTA}
        timeZone={DASHBOARD_TIME_ZONE}
      />,
    );

    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders zeroed cards when no filtered transactions are available", () => {
    render(
      <Overview
        period="month"
        referenceTransactions={[]}
        transactions={[]}
        now={DASHBOARD_NOW}
        quotaRub={DASHBOARD_QUOTA}
        timeZone={DASHBOARD_TIME_ZONE}
      />,
    );

    expect(screen.getByTestId("overview-spent-value")).toHaveTextContent("0");
    expect(screen.getAllByText("0 трат")).toHaveLength(2);
  });

  it("hides quota-only affordances for the all-time period", () => {
    const filteredTransactions = selectFilteredExpenses(
      DASHBOARD_TRANSACTIONS,
      {
        ...defaultExpenseFilters,
        period: "all",
      },
      {
        now: DASHBOARD_NOW,
        timeZone: DASHBOARD_TIME_ZONE,
      },
    );

    const { container } = render(
      <Overview
        period="all"
        referenceTransactions={filteredTransactions}
        transactions={filteredTransactions}
        now={DASHBOARD_NOW}
        quotaRub={DASHBOARD_QUOTA}
        timeZone={DASHBOARD_TIME_ZONE}
      />,
    );

    expect(screen.queryByText("ОСТАЛОСЬ")).not.toBeInTheDocument();
    expect(screen.queryByText("QUOTA EXCEEDED")).not.toBeInTheDocument();
    expect(container.querySelector(".quota-bar")).toBeNull();
    expect(
      screen.queryByText(/за месяц|за 30 дней|за 7 дней|за день/),
    ).not.toBeInTheDocument();
  });
});
