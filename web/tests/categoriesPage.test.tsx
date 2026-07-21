import { fireEvent, render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { CategoriesPage } from "../src/components/CategoriesPage";
import { ExpenseDashboardProvider } from "../src/context/expenseDashboard";
import { useExpenses } from "../src/hooks/useExpenses";
import type { Transaction } from "../src/types/transaction";
import {
  CATEGORY_PAGE_NOW,
  CATEGORY_PAGE_TIME_ZONE,
  CATEGORY_PAGE_TRANSACTIONS,
} from "./fixtures/categoriesTransactions";

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

function buildTransferTransaction(
  overrides: Partial<Transaction> = {},
): Transaction {
  return {
    id: overrides.id ?? "transfer-page-fixture",
    date: overrides.date ?? "2026-04-26T12:00:00+03:00",
    amount: overrides.amount ?? "-100.00",
    currency: overrides.currency ?? "RUB",
    merchant_raw: overrides.merchant_raw ?? "",
    description: overrides.description ?? "",
    bank: overrides.bank ?? "sberbank",
    account: overrides.account ?? "****1111",
    precision: overrides.precision ?? "minute",
    category: overrides.category ?? "Переводы",
    is_transfer: overrides.is_transfer ?? false,
    is_external_account: overrides.is_external_account ?? false,
    transfer_pair_id: overrides.transfer_pair_id ?? null,
    raw: overrides.raw ?? {},
  };
}

const CATEGORY_PAGE_TRANSFER_TRANSACTIONS: Transaction[] = [
  buildTransferTransaction({
    id: "page-transfer-1",
    amount: "-1500.00",
    merchant_raw: "SBOL.",
    description:
      "Перевод AD10001AAAAAAA1111 через СБП. Получатель: PLAYMAG – FZ.",
    is_transfer: true,
  }),
  buildTransferTransaction({
    id: "page-transfer-2",
    date: "2026-04-25T12:00:00+03:00",
    amount: "-500.00",
    merchant_raw: "BD100042LUK6C6G18OD9K5OKL252VNPG",
    description:
      "Перевод BD100042LUK6C6G18OD9K5OKL252VNPG через СБП. Получатель: PLAYMAG.",
    is_transfer: true,
  }),
  buildTransferTransaction({
    id: "page-transfer-3",
    date: "2026-04-24T12:00:00+03:00",
    amount: "-35343.00",
    merchant_raw: "BD100043LUK6C6G18OD9K5OKL252VNPH",
    description:
      'Перевод BD100043LUK6C6G18OD9K5OKL252VNPH через СБП. Получатель: ООО "ТЕХНОПАРК ЦЕНТР".',
    is_transfer: true,
  }),
  buildTransferTransaction({
    id: "page-transfer-4",
    date: "2026-04-23T12:00:00+03:00",
    amount: "-1999.00",
    merchant_raw: "",
    description: "NOMOREFARM.RU",
    is_transfer: true,
  }),
  buildTransferTransaction({
    id: "page-transfer-5",
    date: "2026-04-22T12:00:00+03:00",
    amount: "-999.00",
    merchant_raw: "Без названия",
    description: "PLAYMAG FZ SERVICE",
    is_transfer: true,
  }),
  buildTransferTransaction({
    id: "page-food-1",
    date: "2026-04-21T10:00:00+03:00",
    amount: "-300.00",
    merchant_raw: "Пятёрочка",
    description: "Покупка продуктов",
    category: "Еда",
    is_transfer: false,
  }),
];

interface CategoriesPageHarnessProps {
  showTransfers?: boolean;
  transactions?: Transaction[];
}

function CategoriesPageHarness({
  transactions = CATEGORY_PAGE_TRANSACTIONS,
  showTransfers = false,
}: CategoriesPageHarnessProps) {
  const expenseState = useExpenses(transactions, {
    now: CATEGORY_PAGE_NOW,
    timeZone: CATEGORY_PAGE_TIME_ZONE,
  });
  const { filters, setHideTransfers } = expenseState;

  useEffect(() => {
    const desiredHideTransfers = !showTransfers;
    if (filters.hideTransfers !== desiredHideTransfers) {
      setHideTransfers(desiredHideTransfers);
    }
  }, [filters.hideTransfers, setHideTransfers, showTransfers]);

  return (
    <ExpenseDashboardProvider value={expenseState}>
      <CategoriesPage />
    </ExpenseDashboardProvider>
  );
}

describe("CategoriesPage", () => {
  it("renders the month view snapshot", () => {
    const { container } = render(<CategoriesPageHarness />);

    expect(container.firstChild).toMatchSnapshot();
  });

  it("renders cleaned transfer merchants when transfers are visible", async () => {
    const { container } = render(
      <CategoriesPageHarness
        transactions={CATEGORY_PAGE_TRANSFER_TRANSACTIONS}
        showTransfers
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: /Переводы/i }));

    const merchantList = container.querySelector(
      ".categories-page__merchant-list",
    );

    expect(merchantList).toHaveTextContent("PLAYMAG");
    expect(merchantList).toHaveTextContent("3 траты");
    expect(merchantList).toHaveTextContent("ООО ТЕХНОПАРК ЦЕНТР");
    expect(merchantList).toHaveTextContent("NOMOREFARM.RU");
    expect(merchantList).not.toHaveTextContent(
      "BD100042LUK6C6G18OD9K5OKL252VNPG",
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("updates cleanly across all period chips", () => {
    render(<CategoriesPageHarness />);

    for (const periodLabel of ["СЕГОДНЯ", "7Д", "30Д", "МЕСЯЦ", "ВСЁ ВРЕМЯ"]) {
      fireEvent.click(screen.getByRole("button", { name: periodLabel }));
      expect(
        screen.getByRole("heading", { name: "КАТЕГОРИИ" }),
      ).toBeInTheDocument();
    }
  });

  it("uses dedicated categories drilldown column classes instead of analytics helpers", () => {
    const { container } = render(<CategoriesPageHarness />);

    fireEvent.click(screen.getByRole("button", { name: /Еда/i }));

    expect(container.querySelectorAll(".categories-page__column")).toHaveLength(
      2,
    );
    expect(
      container.querySelectorAll(".categories-page__column-title"),
    ).toHaveLength(2);
    expect(container.querySelector(".monthly-bars__detail-panel")).toBeNull();
    expect(container.querySelector(".monthly-bars__detail-list")).toBeNull();
  });

  it("opens and closes drilldowns inline and lets the Прочее hero card jump to that category", () => {
    render(<CategoriesPageHarness />);

    const foodButton = screen.getByRole("button", { name: /Еда/i });
    fireEvent.click(foodButton);

    expect(foodButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByLabelText("Детали категории Еда")).toBeInTheDocument();

    fireEvent.click(foodButton);

    expect(foodButton).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.queryByLabelText("Детали категории Еда"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /ПРОЧЕЕ/i })[0]);

    expect(
      screen.getByLabelText("Детали категории Прочее"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Чтобы убрать из Прочего: добавь regex в parser/categories_overrides.yaml и перезапусти build.",
      ),
    ).toBeInTheDocument();
  });
});
