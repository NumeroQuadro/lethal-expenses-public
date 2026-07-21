import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useExpenses } from "../src/hooks/useExpenses";
import {
  selectAnalyticsExpenses,
  selectAnalyticsSummary,
  defaultExpenseFilters,
  displayMerchant,
  quotaForPeriod,
  selectAvailableCategories,
  selectCategoryBreakdown,
  selectCategoryDrilldownData,
  selectCategoryHeroSummary,
  selectExpenseHistogram,
  selectExpensesByCategoryByMonth,
  selectExpensesByCategoryForMonth,
  selectExpensesByCategory,
  selectExpensesByDay,
  selectExpensesByMerchantForMonth,
  selectExpensesByMerchant,
  selectExpensesByMonth,
  selectFilteredExpenses,
  selectRecentExpenses,
  selectTransactionsByPeriod,
  selectTotalExpense,
  type ExpenseFilters,
} from "../src/lib/expenses";
import type { Transaction } from "../src/types/transaction";
import { ANALYTICS_TRANSACTIONS } from "./fixtures/analyticsTransactions";
import {
  CATEGORY_PAGE_NOW,
  CATEGORY_PAGE_TIME_ZONE,
  CATEGORY_PAGE_TRANSACTIONS,
} from "./fixtures/categoriesTransactions";

const NOW = new Date("2026-04-24T18:00:00+03:00");
const OPTIONS = {
  now: NOW,
  timeZone: "Europe/Moscow",
};

const FIXTURE_TRANSACTIONS: Transaction[] = [
  {
    id: "t-1",
    date: "2026-04-24T09:00:00+03:00",
    amount: "-100.00",
    currency: "RUB",
    merchant_raw: "Пятёрочка",
    description: "Покупка продуктов",
    bank: "sberbank",
    account: "****1111",
    precision: "minute",
    category: "Еда",
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: "t-2",
    date: "2026-04-24T10:00:00+03:00",
    amount: "-50.00",
    currency: "RUB",
    merchant_raw: "Яндекс",
    description: "Перевод СБП на свой счёт",
    bank: "yandex",
    account: "****2222",
    precision: "minute",
    category: "Переводы",
    is_transfer: true,
    is_external_account: false,
    transfer_pair_id: "pair-1",
    raw: {},
  },
  {
    id: "t-3",
    date: "2026-04-22T13:00:00+03:00",
    amount: "-200.00",
    currency: "RUB",
    merchant_raw: "Кофейня",
    description: "Ланч",
    bank: "ozon",
    account: "****3333",
    precision: "minute",
    category: "Кафе",
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: "t-4",
    date: "2026-04-21T08:00:00+03:00",
    amount: "400.00",
    currency: "RUB",
    merchant_raw: "Работа",
    description: "Зарплата",
    bank: "spb",
    account: "****4444",
    precision: "minute",
    category: "Прочее",
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: "t-5",
    date: "2026-04-01T11:30:00+03:00",
    amount: "-75.00",
    currency: "RUB",
    merchant_raw: "Метро",
    description: "Пополнение карты",
    bank: "spb",
    account: "****4444",
    precision: "minute",
    category: "Транспорт",
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
  {
    id: "t-6",
    date: "2026-03-15T16:15:00+03:00",
    amount: "-300.00",
    currency: "RUB",
    merchant_raw: "ВкусВилл",
    description: "Покупка продуктов",
    bank: "sberbank",
    account: "****1111",
    precision: "minute",
    category: "Еда",
    is_transfer: false,
    is_external_account: false,
    transfer_pair_id: null,
    raw: {},
  },
];

const EXTERNAL_ACCOUNT_TRANSACTION: Transaction = {
  id: "t-external",
  date: "2026-04-24T12:30:00+03:00",
  amount: "-400.00",
  currency: "RUB",
  merchant_raw: "Relay account expense",
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

function buildTransaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: overrides.id ?? "transfer-fixture",
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

const TRANSFER_DRILLDOWN_TRANSACTIONS: Transaction[] = [
  buildTransaction({
    id: "transfer-1",
    amount: "-1500.00",
    merchant_raw: "SBOL.",
    description:
      "Перевод AD10001AAAAAAA1111 через СБП. Получатель: PLAYMAG – FZ.",
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-2",
    date: "2026-04-25T12:00:00+03:00",
    amount: "-500.00",
    merchant_raw: "BD100042LUK6C6G18OD9K5OKL252VNPG",
    description:
      "Перевод BD100042LUK6C6G18OD9K5OKL252VNPG через СБП. Получатель: PLAYMAG.",
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-3",
    date: "2026-04-24T12:00:00+03:00",
    amount: "-35343.00",
    merchant_raw: "BD100043LUK6C6G18OD9K5OKL252VNPH",
    description:
      'Перевод BD100043LUK6C6G18OD9K5OKL252VNPH через СБП. Получатель: ООО "ТЕХНОПАРК ЦЕНТР".',
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-4",
    date: "2026-04-23T12:00:00+03:00",
    amount: "-1999.00",
    merchant_raw: "",
    description: "NOMOREFARM.RU",
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-5",
    date: "2026-04-22T12:00:00+03:00",
    amount: "-999.00",
    merchant_raw: "Без названия",
    description: "PLAYMAG FZ SERVICE",
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-6",
    date: "2026-04-21T12:00:00+03:00",
    amount: "-1200.00",
    merchant_raw: "",
    description:
      "Перевод A6091122445025040G10060011730902 через СБП. Получатель: Анна Сергеевна П. Без НДС",
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-7",
    date: "2026-04-20T12:00:00+03:00",
    amount: "-900.00",
    merchant_raw: "SBOL.",
    description:
      "Перевод A6091122445025040G10060011730903 через СБП. Получатель: Анна Сергеевна П.",
    is_transfer: true,
  }),
  buildTransaction({
    id: "transfer-8",
    date: "2026-04-19T12:00:00+03:00",
    amount: "-250.00",
    merchant_raw: "Без названия",
    description: "непонятный перевод без метки 123",
    is_transfer: true,
  }),
];

describe("expense selectors", () => {
  it("filters expense rows and excludes transfers by default", () => {
    const filtered = selectFilteredExpenses(
      FIXTURE_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    expect(filtered.map((transaction) => transaction.id)).toEqual([
      "t-1",
      "t-3",
      "t-5",
    ]);
    expect(selectTotalExpense(filtered)).toBe(375);
  });

  it("excludes external-account rows from expense views even when transfers are visible", () => {
    const withExternal = [
      ...FIXTURE_TRANSACTIONS,
      EXTERNAL_ACCOUNT_TRANSACTION,
    ];
    const filtered = selectFilteredExpenses(
      withExternal,
      { ...defaultExpenseFilters, hideTransfers: false, period: "all" },
      OPTIONS,
    );

    expect(filtered.map((transaction) => transaction.id)).not.toContain(
      "t-external",
    );
    expect(selectTotalExpense(filtered)).toBe(725);

    const { result } = renderHook(() => useExpenses(withExternal, OPTIONS));
    act(() => result.current.setPeriod("all"));
    act(() => result.current.setHideTransfers(false));

    expect(
      result.current.filteredTransactions.map((transaction) => transaction.id),
    ).not.toContain("t-external");
    expect(result.current.totalExpense).toBe(725);
  });

  it("includes external-account rows when explicitly requested for audit", () => {
    const withExternal = [
      ...FIXTURE_TRANSACTIONS,
      EXTERNAL_ACCOUNT_TRANSACTION,
    ];
    const filtered = selectFilteredExpenses(
      withExternal,
      { ...defaultExpenseFilters, period: "all", showExternalAccounts: true },
      OPTIONS,
    );

    expect(filtered.map((transaction) => transaction.id)).toContain(
      "t-external",
    );
    expect(selectTotalExpense(filtered)).toBe(1075);

    const { result } = renderHook(() => useExpenses(withExternal, OPTIONS));
    act(() => result.current.setPeriod("all"));
    act(() => result.current.setShowExternalAccounts(true));

    expect(
      result.current.filteredTransactions.map((transaction) => transaction.id),
    ).toContain("t-external");
    expect(result.current.totalExpense).toBe(1075);
  });

  it("builds category and day summaries from filtered expenses", () => {
    const filtered = selectFilteredExpenses(
      FIXTURE_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    expect(selectExpensesByCategory(filtered)).toEqual([
      { category: "Кафе", totalExpense: 200, transactionCount: 1 },
      { category: "Еда", totalExpense: 100, transactionCount: 1 },
      { category: "Транспорт", totalExpense: 75, transactionCount: 1 },
    ]);

    expect(selectExpensesByDay(filtered, OPTIONS)).toEqual([
      { day: "2026-04-24", totalExpense: 100, transactionCount: 1 },
      { day: "2026-04-22", totalExpense: 200, transactionCount: 1 },
      { day: "2026-04-01", totalExpense: 75, transactionCount: 1 },
    ]);
  });

  it("builds category breakdown rows that reconcile to the overview total", () => {
    const filtered = selectFilteredExpenses(
      FIXTURE_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );
    const breakdown = selectCategoryBreakdown(filtered);

    expect(breakdown.map((entry) => entry.category)).toEqual([
      "Кафе",
      "Еда",
      "Транспорт",
    ]);
    expect(breakdown[0]?.totalExpense).toBe(200);
    expect(breakdown[0]?.sharePercentage).toBeCloseTo(53.3333, 3);
    expect(breakdown[0]?.widthPercentage).toBe(100);
    expect(breakdown[1]?.totalExpense).toBe(100);
    expect(breakdown[1]?.sharePercentage).toBeCloseTo(26.6667, 3);
    expect(breakdown[1]?.widthPercentage).toBe(50);
    expect(breakdown[2]?.totalExpense).toBe(75);
    expect(breakdown[2]?.sharePercentage).toBeCloseTo(20, 3);
    expect(breakdown[2]?.widthPercentage).toBeCloseTo(37.5, 3);
    expect(breakdown.reduce((sum, entry) => sum + entry.totalExpense, 0)).toBe(
      selectTotalExpense(filtered),
    );
  });

  it("builds a zero-filled trailing histogram for the last 30 days", () => {
    const filtered = selectFilteredExpenses(
      FIXTURE_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );
    const histogram = selectExpenseHistogram(filtered, OPTIONS, 5);

    expect(histogram).toHaveLength(5);
    expect(histogram.map((entry) => entry.day)).toEqual([
      "2026-04-20",
      "2026-04-21",
      "2026-04-22",
      "2026-04-23",
      "2026-04-24",
    ]);
    expect(histogram.map((entry) => entry.totalExpense)).toEqual([
      0, 0, 200, 0, 100,
    ]);
    expect(histogram.map((entry) => entry.heightPercentage)).toEqual([
      0, 0, 100, 0, 50,
    ]);
    expect(histogram.map((entry) => entry.isToday)).toEqual([
      false,
      false,
      false,
      false,
      true,
    ]);
  });

  it("supports direct period selection helpers", () => {
    expect(
      selectTransactionsByPeriod(FIXTURE_TRANSACTIONS, "today", OPTIONS).map(
        (transaction) => transaction.id,
      ),
    ).toEqual(["t-2", "t-1"]);

    expect(
      selectTransactionsByPeriod(FIXTURE_TRANSACTIONS, "7d", OPTIONS).map(
        (transaction) => transaction.id,
      ),
    ).toEqual(["t-2", "t-1", "t-3", "t-4"]);

    const filtered = selectFilteredExpenses(
      FIXTURE_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    expect(selectAvailableCategories(filtered)).toEqual([
      "Кафе",
      "Еда",
      "Транспорт",
    ]);
  });

  it("scales quota by the selected period", () => {
    expect(quotaForPeriod("month", 40_000, NOW, OPTIONS.timeZone)).toBe(40_000);
    expect(quotaForPeriod("30d", 40_000, NOW, OPTIONS.timeZone)).toBe(40_000);
    expect(quotaForPeriod("7d", 40_000, NOW, OPTIONS.timeZone)).toBeCloseTo(
      9333.3333,
      4,
    );
    expect(quotaForPeriod("today", 40_000, NOW, OPTIONS.timeZone)).toBeCloseTo(
      1333.3333,
      4,
    );
    expect(quotaForPeriod("all", 40_000, NOW, OPTIONS.timeZone)).toBeNull();
  });

  it("uses real month length for the daily quota, including leap February", () => {
    const leapFebruaryNow = new Date("2024-02-12T12:00:00+03:00");

    expect(
      quotaForPeriod("today", 40_000, leapFebruaryNow, OPTIONS.timeZone),
    ).toBeCloseTo(40000 / 29, 6);
  });

  it("supports period, transfer, and category filters", () => {
    const todayFilters: ExpenseFilters = {
      ...defaultExpenseFilters,
      period: "today",
    };
    const sevenDayFilters: ExpenseFilters = {
      ...defaultExpenseFilters,
      period: "7d",
    };
    const thirtyDayFilters: ExpenseFilters = {
      ...defaultExpenseFilters,
      period: "30d",
    };
    const monthFilters: ExpenseFilters = {
      ...defaultExpenseFilters,
      period: "month",
    };
    const allTimeFilters: ExpenseFilters = {
      ...defaultExpenseFilters,
      period: "all",
    };
    const withTransfers: ExpenseFilters = {
      ...defaultExpenseFilters,
      hideTransfers: false,
    };
    const foodOnly: ExpenseFilters = {
      ...defaultExpenseFilters,
      categoryFilter: ["Еда"],
    };

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, todayFilters, OPTIONS),
      ),
    ).toBe(100);

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, sevenDayFilters, OPTIONS),
      ),
    ).toBe(300);

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, thirtyDayFilters, OPTIONS),
      ),
    ).toBe(375);

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, monthFilters, OPTIONS),
      ),
    ).toBe(375);

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, allTimeFilters, OPTIONS),
      ),
    ).toBe(675);

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, withTransfers, OPTIONS),
      ),
    ).toBe(425);

    expect(
      selectTotalExpense(
        selectFilteredExpenses(FIXTURE_TRANSACTIONS, foodOnly, OPTIONS),
      ),
    ).toBe(100);

    expect(
      selectTotalExpense(
        selectAnalyticsExpenses(FIXTURE_TRANSACTIONS, foodOnly, OPTIONS),
      ),
    ).toBe(675);
  });

  it("updates hook state across each dashboard filter control", () => {
    const { result } = renderHook(() =>
      useExpenses(FIXTURE_TRANSACTIONS, OPTIONS),
    );

    expect(result.current.filters).toEqual(defaultExpenseFilters);
    expect(result.current.period).toBe("month");
    expect(result.current.totalExpense).toBe(375);
    expect(result.current.periodReferenceTransactions).toHaveLength(4);

    act(() => result.current.setPeriod("today"));
    expect(result.current.period).toBe("today");
    expect(result.current.totalExpense).toBe(100);
    expect(result.current.periodReferenceTransactions).toHaveLength(4);

    act(() => result.current.setPeriod("7d"));
    expect(result.current.period).toBe("7d");
    expect(result.current.totalExpense).toBe(300);

    act(() => result.current.setPeriod("30d"));
    expect(result.current.period).toBe("30d");
    expect(result.current.totalExpense).toBe(375);

    act(() => result.current.setPeriod("month"));
    expect(result.current.period).toBe("month");
    expect(result.current.totalExpense).toBe(375);

    act(() => result.current.setPeriod("all"));
    expect(result.current.period).toBe("all");
    expect(result.current.totalExpense).toBe(675);
    expect(result.current.periodReferenceTransactions).toHaveLength(4);

    act(() => result.current.setHideTransfers(false));
    expect(result.current.totalExpense).toBe(725);

    act(() => result.current.setShowExternalAccounts(true));
    expect(result.current.totalExpense).toBe(725);

    act(() => result.current.toggleCategory("Еда"));
    expect(result.current.filters.categoryFilter).toEqual(["Еда"]);
    expect(result.current.totalExpense).toBe(400);

    act(() => result.current.toggleCategory("Кафе"));
    expect(result.current.filters.categoryFilter).toEqual(["Еда", "Кафе"]);
    expect(result.current.totalExpense).toBe(600);

    act(() => result.current.clearCategoryFilter());
    expect(result.current.filters.categoryFilter).toEqual([]);
    expect(result.current.totalExpense).toBe(725);
    expect(result.current.availableCategories).toEqual([
      "Еда",
      "Кафе",
      "Транспорт",
      "Переводы",
    ]);
  });

  it("returns recent expenses in descending date order", () => {
    const filtered = selectFilteredExpenses(
      FIXTURE_TRANSACTIONS,
      {
        ...defaultExpenseFilters,
        period: "all",
      },
      OPTIONS,
    );

    expect(
      selectRecentExpenses(filtered, 2).map((transaction) => transaction.id),
    ).toEqual(["t-1", "t-3"]);
  });

  it("builds analytics month, merchant, and category drill-down aggregates", () => {
    const analyticsTransactions = selectAnalyticsExpenses(
      ANALYTICS_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    expect(selectExpensesByMonth(analyticsTransactions, OPTIONS)).toEqual([
      {
        month: "2026-04",
        label: "АПРЕЛЬ 2026",
        totalExpense: 2700,
        transactionCount: 2,
      },
      {
        month: "2026-03",
        label: "МАРТ 2026",
        totalExpense: 3250,
        transactionCount: 2,
      },
      {
        month: "2026-02",
        label: "ФЕВРАЛЬ 2026",
        totalExpense: 2400,
        transactionCount: 3,
      },
      {
        month: "2026-01",
        label: "ЯНВАРЬ 2026",
        totalExpense: 4300,
        transactionCount: 3,
      },
    ]);

    expect(selectExpensesByMerchant(analyticsTransactions, 3)).toEqual([
      {
        merchant: "OZON",
        totalExpense: 5700,
        transactionCount: 3,
      },
      {
        merchant: "TECHNOPARK",
        totalExpense: 2500,
        transactionCount: 1,
      },
      {
        merchant: "PYATEROCHKA",
        totalExpense: 2100,
        transactionCount: 2,
      },
    ]);

    expect(
      selectExpensesByCategoryByMonth(
        analyticsTransactions,
        "Покупки",
        OPTIONS,
      ),
    ).toEqual([
      {
        month: "2026-04",
        label: "АПРЕЛЬ 2026",
        totalExpense: 2700,
        transactionCount: 2,
      },
      {
        month: "2026-03",
        label: "МАРТ 2026",
        totalExpense: 3000,
        transactionCount: 1,
      },
      {
        month: "2026-01",
        label: "ЯНВАРЬ 2026",
        totalExpense: 2500,
        transactionCount: 1,
      },
    ]);

    expect(
      selectExpensesByCategoryForMonth(
        analyticsTransactions,
        "2026-04",
        OPTIONS,
      ),
    ).toEqual([
      { category: "Покупки", totalExpense: 2700, transactionCount: 2 },
    ]);

    expect(
      selectExpensesByMerchantForMonth(
        analyticsTransactions,
        "2026-02",
        OPTIONS,
      ),
    ).toEqual([
      { merchant: "PYATEROCHKA", totalExpense: 900, transactionCount: 1 },
      { merchant: "MAGNIT", totalExpense: 800, transactionCount: 1 },
      { merchant: "KAFE GRUSHENKA", totalExpense: 700, transactionCount: 1 },
    ]);
  });

  describe("displayMerchant", () => {
    it("keeps the existing merchant label for non-transfer rows", () => {
      expect(
        displayMerchant(
          buildTransaction({
            category: "Еда",
            merchant_raw: "Пятёрочка",
            description: "Покупка продуктов",
          }),
        ),
      ).toBe("Пятёрочка");
    });

    it("keeps a clean transfer merchant unchanged", () => {
      expect(
        displayMerchant(
          buildTransaction({
            merchant_raw: "И. Иван Иванович.",
            description: "Перевод на карту",
          }),
        ),
      ).toBe("И. Иван Иванович.");
    });

    it("extracts the recipient from SBP token descriptions", () => {
      expect(
        displayMerchant(
          buildTransaction({
            merchant_raw: "BD100042LUK6C6G18OD9K5OKL252VNPG",
            description:
              'Перевод BD100042LUK6C6G18OD9K5OKL252VNPG через СБП. Получатель: ООО "ТЕХНОПАРК ЦЕНТР".',
          }),
        ),
      ).toBe("ООО ТЕХНОПАРК ЦЕНТР");
    });

    it("extracts the recipient when SBOL is the raw merchant", () => {
      expect(
        displayMerchant(
          buildTransaction({
            merchant_raw: "SBOL.",
            description: "Перевод через СБП. Получатель: PLAYMAG.",
          }),
        ),
      ).toBe("PLAYMAG");
    });

    it("extracts the recipient from composite transfer descriptions", () => {
      expect(
        displayMerchant(
          buildTransaction({
            merchant_raw: "",
            description:
              "Перевод A6091122445025040G10060011730902 через СБП. Получатель: Анна Сергеевна П. Без НДС",
          }),
        ),
      ).toBe("Анна Сергеевна П");
    });

    it("captures domain-like and uppercase brand descriptions", () => {
      expect(
        displayMerchant(
          buildTransaction({ merchant_raw: "", description: "NOMOREFARM.RU" }),
        ),
      ).toBe("NOMOREFARM.RU");
      expect(
        displayMerchant(
          buildTransaction({
            merchant_raw: "Без названия",
            description: "PLAYMAG FZ SERVICE",
          }),
        ),
      ).toBe("PLAYMAG");
    });

    it("falls back to a description snippet when nothing matches", () => {
      expect(
        displayMerchant(
          buildTransaction({
            merchant_raw: "Без названия",
            description: "непонятный перевод без метки 123",
          }),
        ),
      ).toBe("непонятный перевод без метки 123");
    });
  });

  it("re-groups transfer drilldown merchants by displayMerchant labels", () => {
    expect(
      selectCategoryDrilldownData(
        TRANSFER_DRILLDOWN_TRANSACTIONS,
        "Переводы",
        10,
        20,
        displayMerchant,
      ),
    ).toEqual({
      category: "Переводы",
      topMerchants: [
        {
          merchant: "ООО ТЕХНОПАРК ЦЕНТР",
          totalExpense: 35343,
          transactionCount: 1,
        },
        { merchant: "PLAYMAG", totalExpense: 2999, transactionCount: 3 },
        {
          merchant: "Анна Сергеевна П",
          totalExpense: 2100,
          transactionCount: 2,
        },
        {
          merchant: "NOMOREFARM.RU",
          totalExpense: 1999,
          transactionCount: 1,
        },
        {
          merchant: "непонятный перевод без метки 123",
          totalExpense: 250,
          transactionCount: 1,
        },
      ],
      recentTransactions: [
        expect.objectContaining({ id: "transfer-1" }),
        expect.objectContaining({ id: "transfer-2" }),
        expect.objectContaining({ id: "transfer-3" }),
        expect.objectContaining({ id: "transfer-4" }),
        expect.objectContaining({ id: "transfer-5" }),
        expect.objectContaining({ id: "transfer-6" }),
        expect.objectContaining({ id: "transfer-7" }),
        expect.objectContaining({ id: "transfer-8" }),
      ],
    });
  });

  it("builds category hero summaries from the unfiltered period slice", () => {
    const monthTransactions = selectFilteredExpenses(
      CATEGORY_PAGE_TRANSACTIONS,
      defaultExpenseFilters,
      {
        now: CATEGORY_PAGE_NOW,
        timeZone: CATEGORY_PAGE_TIME_ZONE,
      },
    );
    const allTransactions = selectAnalyticsExpenses(
      CATEGORY_PAGE_TRANSACTIONS,
      defaultExpenseFilters,
      {
        now: CATEGORY_PAGE_NOW,
        timeZone: CATEGORY_PAGE_TIME_ZONE,
      },
    );

    expect(
      selectCategoryHeroSummary(monthTransactions, allTransactions, "month", {
        now: CATEGORY_PAGE_NOW,
        timeZone: CATEGORY_PAGE_TIME_ZONE,
      }),
    ).toEqual({
      topCategory: {
        category: "Электроника",
        totalExpense: 2500,
        transactionCount: 1,
      },
      topCategorySharePercentage: expect.closeTo(42.016806722689076, 10),
      fastestGrowingCategory: {
        category: "Электроника",
        currentExpense: 2500,
        previousExpense: 1000,
        deltaExpense: 1500,
      },
      otherCategory: {
        category: "Прочее",
        totalExpense: 1000,
        transactionCount: 2,
      },
      otherCategorySharePercentage: expect.closeTo(16.80672268907563, 10),
    });

    expect(
      selectCategoryHeroSummary(monthTransactions, allTransactions, "all", {
        now: CATEGORY_PAGE_NOW,
        timeZone: CATEGORY_PAGE_TIME_ZONE,
      }).fastestGrowingCategory,
    ).toBeNull();
  });

  it("builds category drilldown merchants and recent rows in descending order", () => {
    const monthTransactions = selectFilteredExpenses(
      CATEGORY_PAGE_TRANSACTIONS,
      defaultExpenseFilters,
      {
        now: CATEGORY_PAGE_NOW,
        timeZone: CATEGORY_PAGE_TIME_ZONE,
      },
    );

    expect(selectCategoryDrilldownData(monthTransactions, "Прочее")).toEqual({
      category: "Прочее",
      topMerchants: [
        {
          merchant: "MYSTERY SHOP",
          totalExpense: 700,
          transactionCount: 1,
        },
        {
          merchant: "UNKNOWN PAY",
          totalExpense: 300,
          transactionCount: 1,
        },
      ],
      recentTransactions: [
        expect.objectContaining({ id: "cat-4" }),
        expect.objectContaining({ id: "cat-5" }),
      ],
    });
  });

  it("builds analytics summary and empty-state aggregates", () => {
    const analyticsTransactions = selectAnalyticsExpenses(
      ANALYTICS_TRANSACTIONS,
      defaultExpenseFilters,
      OPTIONS,
    );

    expect(selectAnalyticsSummary(analyticsTransactions, OPTIONS)).toEqual({
      totalExpense: 12650,
      monthlyAverageExpense: 3162.5,
      topCategoryName: "Покупки",
      topCategorySharePercentage: expect.closeTo(64.82213438735178, 10),
      peakMonthLabel: "ЯНВАРЬ 2026",
      peakMonthTotalExpense: 4300,
    });

    const analyticsWithTransfers = selectAnalyticsExpenses(
      ANALYTICS_TRANSACTIONS,
      { ...defaultExpenseFilters, hideTransfers: false },
      OPTIONS,
    );

    expect(selectAnalyticsSummary(analyticsWithTransfers, OPTIONS)).toEqual({
      totalExpense: 17650,
      monthlyAverageExpense: 4412.5,
      topCategoryName: "Покупки",
      topCategorySharePercentage: expect.closeTo(64.82213438735178, 10),
      peakMonthLabel: "ЯНВАРЬ 2026",
      peakMonthTotalExpense: 9300,
    });

    expect(selectExpensesByMonth([], OPTIONS)).toEqual([]);
    expect(selectExpensesByMerchant([])).toEqual([]);
    expect(selectExpensesByCategoryByMonth([], "Еда", OPTIONS)).toEqual([]);
    expect(selectAnalyticsSummary([], OPTIONS)).toEqual({
      totalExpense: 0,
      monthlyAverageExpense: 0,
      topCategoryName: "—",
      topCategorySharePercentage: 0,
      peakMonthLabel: "—",
      peakMonthTotalExpense: 0,
    });
  });
});
