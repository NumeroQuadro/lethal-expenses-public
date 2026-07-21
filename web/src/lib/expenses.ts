import type { Transaction } from "../types/transaction";

export type ExpensePeriod = "today" | "7d" | "30d" | "month" | "all";

export interface ExpenseFilters {
  period: ExpensePeriod;
  hideTransfers: boolean;
  showExternalAccounts: boolean;
  categoryFilter: string[];
}

export interface ExpenseSelectorOptions {
  now?: Date;
  timeZone?: string;
}

export interface CategoryExpense {
  category: string;
  totalExpense: number;
  transactionCount: number;
}

export interface CategoryBreakdownEntry extends CategoryExpense {
  sharePercentage: number;
  widthPercentage: number;
}

export interface CategoryDelta {
  category: string;
  currentExpense: number;
  previousExpense: number;
  deltaExpense: number;
}

export interface CategoryHeroSummary {
  topCategory: CategoryExpense | null;
  topCategorySharePercentage: number;
  fastestGrowingCategory: CategoryDelta | null;
  otherCategory: CategoryExpense | null;
  otherCategorySharePercentage: number;
}

export interface CategoryDrilldownData {
  category: string;
  topMerchants: MerchantExpense[];
  recentTransactions: Transaction[];
}

export interface MonthExpense {
  month: string;
  label: string;
  totalExpense: number;
  transactionCount: number;
}

export interface MerchantExpense {
  merchant: string;
  totalExpense: number;
  transactionCount: number;
}

export interface AnalyticsSummary {
  totalExpense: number;
  monthlyAverageExpense: number;
  topCategoryName: string;
  topCategorySharePercentage: number;
  peakMonthLabel: string;
  peakMonthTotalExpense: number;
}

export interface DayExpense {
  day: string;
  totalExpense: number;
  transactionCount: number;
}

export interface DayHistogramEntry extends DayExpense {
  heightPercentage: number;
  isToday: boolean;
}

const DAY_IN_MS = 24 * 60 * 60 * 1000;
const OTHER_CATEGORY = "Прочее";
const TRANSFER_CATEGORY = "Переводы";

export const defaultExpenseFilters: ExpenseFilters = {
  period: "month",
  hideTransfers: true,
  showExternalAccounts: false,
  categoryFilter: [],
};

function resolveNow(options?: ExpenseSelectorOptions): Date {
  return options?.now ?? new Date();
}

function resolveTimeZone(options?: ExpenseSelectorOptions): string {
  return options?.timeZone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
}

function getAmountInCents(transaction: Transaction): number {
  return Math.round(Number(transaction.amount) * 100);
}

function centsToRubles(cents: number): number {
  return cents / 100;
}

function formatMonthLabel(monthKey: string, timeZone: string): string {
  const [year, month] = monthKey.split("-").map(Number);
  const rawLabel = new Date(
    Date.UTC(year, month - 1, 1, 12),
  ).toLocaleDateString("ru-RU", {
    month: "long",
    timeZone,
    year: "numeric",
  });

  return rawLabel
    .toUpperCase()
    .replace(/\sГ\.$/, "")
    .trim();
}

function getMerchantLabel(transaction: Transaction): string {
  return (
    transaction.merchant_raw.trim() ||
    transaction.description.trim() ||
    "БЕЗ НАЗВАНИЯ"
  );
}

type MerchantSelector = (transaction: Transaction) => string;

function normalizeMerchantText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function sanitizeDisplayMerchant(value: string): string {
  return normalizeMerchantText(value)
    .replace(/[«»"]/g, "")
    .replace(/\s+[–—-].*$/u, "")
    .replace(/\s+БЕЗ НДС.*$/iu, "")
    .replace(/[.,;:!?-]+$/u, "")
    .trim();
}

function hasTransferBoilerplate(value: string): boolean {
  return /\b(?:перевод|сбп|sbol|списание|пополнение|зачисление)\b/iu.test(
    value,
  );
}

function isLikelyTransferToken(value: string): boolean {
  return /\b(?:[AB]\d[A-Z0-9]{10,}|(?:AD|BD)[A-Z0-9]{8,}|[A-Z0-9]{16,})\b/u.test(
    value,
  );
}

function isCleanTransferMerchant(value: string): boolean {
  const normalized = normalizeMerchantText(value);

  return (
    normalized.length > 0 &&
    normalized.length <= 60 &&
    !/^(?:без названия)$/iu.test(normalized) &&
    !hasTransferBoilerplate(normalized) &&
    !isLikelyTransferToken(normalized)
  );
}

function normalizeUppercaseBrand(value: string): string {
  if (/^(?:ООО|ИП)\b/u.test(value)) {
    return value;
  }

  if (/^[A-Z0-9 -]+$/u.test(value)) {
    return value.split(/\s+/u)[0] ?? value;
  }

  return value;
}

function extractTransferMerchantFromDescription(
  description: string,
): string | null {
  const normalized = normalizeMerchantText(description);
  if (!normalized) {
    return null;
  }

  const recipientMatch = normalized.match(
    /Получатель:\s*([^.]+?)(?=\s+(?:ПЕРЕВОД|Перевод|через)|\.|$)/iu,
  );
  if (recipientMatch) {
    const recipient = sanitizeDisplayMerchant(recipientMatch[1]);
    if (recipient) {
      return recipient;
    }
  }

  const domainMatch = normalized.match(/([a-zA-Z0-9-]+\.(?:RU|ru|com|COM))/u);
  if (domainMatch) {
    return domainMatch[1].toUpperCase();
  }

  const uppercaseBrandMatch = normalized.match(
    /^((?:ООО|ИП|[A-ZА-ЯЁ])[A-ZА-ЯЁ0-9 "'.«»-]+(?:ЦЕНТР|ООО|ИП)?)/u,
  );
  if (uppercaseBrandMatch) {
    const uppercaseBrand = normalizeUppercaseBrand(
      sanitizeDisplayMerchant(uppercaseBrandMatch[1]),
    );
    if (
      uppercaseBrand &&
      !hasTransferBoilerplate(uppercaseBrand) &&
      !isLikelyTransferToken(uppercaseBrand)
    ) {
      return uppercaseBrand;
    }
  }

  return null;
}

export function displayMerchant(transaction: Transaction): string {
  if (transaction.category !== TRANSFER_CATEGORY) {
    return getMerchantLabel(transaction);
  }

  const merchantRaw = normalizeMerchantText(transaction.merchant_raw);
  if (isCleanTransferMerchant(merchantRaw)) {
    return merchantRaw;
  }

  const extractedMerchant = extractTransferMerchantFromDescription(
    transaction.description,
  );
  if (extractedMerchant) {
    return extractedMerchant;
  }

  const fallback = normalizeMerchantText(transaction.description)
    .slice(0, 50)
    .trim();
  return fallback || getMerchantLabel(transaction);
}

function getDateParts(
  date: Date,
  timeZone: string,
): {
  day: string;
  month: string;
  year: string;
} {
  const formatter = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  });

  let day = "";
  let month = "";
  let year = "";

  for (const part of formatter.formatToParts(date)) {
    if (part.type === "day") {
      day = part.value;
    }
    if (part.type === "month") {
      month = part.value;
    }
    if (part.type === "year") {
      year = part.value;
    }
  }

  return { day, month, year };
}

function toDayKey(dateValue: string | Date, timeZone: string): string {
  const date = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
  const { day, month, year } = getDateParts(date, timeZone);
  return `${year}-${month}-${day}`;
}

function toMonthKey(dateValue: string | Date, timeZone: string): string {
  return toDayKey(dateValue, timeZone).slice(0, 7);
}

function matchesMonthKey(
  transaction: Transaction,
  month: string,
  timeZone: string,
): boolean {
  return toMonthKey(transaction.date, timeZone) === month;
}

function compareByDateDesc(left: Transaction, right: Transaction): number {
  const dateDelta =
    new Date(right.date).getTime() - new Date(left.date).getTime();
  if (dateDelta !== 0) {
    return dateDelta;
  }

  return right.id.localeCompare(left.id);
}

function matchesPeriod(
  transaction: Transaction,
  period: ExpensePeriod,
  now: Date,
  timeZone: string,
): boolean {
  if (period === "all") {
    return true;
  }

  const transactionDate = new Date(transaction.date);
  if (period === "today") {
    return toDayKey(transactionDate, timeZone) === toDayKey(now, timeZone);
  }

  if (period === "month") {
    return toMonthKey(transactionDate, timeZone) === toMonthKey(now, timeZone);
  }

  const lookbackWindow = period === "7d" ? 7 : 30;
  const delta = now.getTime() - transactionDate.getTime();
  return delta >= 0 && delta <= lookbackWindow * DAY_IN_MS;
}

function hasCategoryFilter(filters: ExpenseFilters): boolean {
  return (
    filters.categoryFilter.length > 0 && !filters.categoryFilter.includes("ВСЕ")
  );
}

function buildTrailingDayKeys(
  now: Date,
  timeZone: string,
  days: number,
): string[] {
  return Array.from({ length: days }, (_, index) => {
    const offset = days - index - 1;
    return toDayKey(new Date(now.getTime() - offset * DAY_IN_MS), timeZone);
  });
}

function daysInCurrentMonth(now: Date, timeZone: string): number {
  const { month, year } = getDateParts(now, timeZone);
  return new Date(Date.UTC(Number(year), Number(month), 0, 12)).getUTCDate();
}

function selectTransactionsWithinRange(
  transactions: Transaction[],
  startInclusiveMs: number,
  endExclusiveMs: number,
): Transaction[] {
  return transactions
    .filter((transaction) => {
      const timestamp = new Date(transaction.date).getTime();
      return timestamp >= startInclusiveMs && timestamp < endExclusiveMs;
    })
    .sort(compareByDateDesc);
}

function previousMonthAnchor(now: Date, timeZone: string): Date {
  const { month, year } = getDateParts(now, timeZone);
  let previousYear = Number(year);
  let previousMonth = Number(month) - 1;

  if (previousMonth === 0) {
    previousMonth = 12;
    previousYear -= 1;
  }

  return new Date(Date.UTC(previousYear, previousMonth - 1, 15, 12));
}

function selectPreviousPeriodTransactions(
  transactions: Transaction[],
  period: ExpensePeriod,
  options?: ExpenseSelectorOptions,
): Transaction[] {
  const now = resolveNow(options);
  const timeZone = resolveTimeZone(options);

  switch (period) {
    case "all":
      return [];
    case "today":
      return selectTransactionsByPeriod(transactions, "today", {
        now: new Date(now.getTime() - DAY_IN_MS),
        timeZone,
      });
    case "7d": {
      const windowMs = 7 * DAY_IN_MS;
      return selectTransactionsWithinRange(
        transactions,
        now.getTime() - 2 * windowMs,
        now.getTime() - windowMs,
      );
    }
    case "30d": {
      const windowMs = 30 * DAY_IN_MS;
      return selectTransactionsWithinRange(
        transactions,
        now.getTime() - 2 * windowMs,
        now.getTime() - windowMs,
      );
    }
    case "month":
      return selectTransactionsByPeriod(transactions, "month", {
        now: previousMonthAnchor(now, timeZone),
        timeZone,
      });
  }
}

function toExpenseMap(
  entries: CategoryExpense[],
): Map<string, CategoryExpense> {
  return new Map(entries.map((entry) => [entry.category, entry]));
}

export function quotaForPeriod(
  period: ExpensePeriod,
  monthlyQuota: number,
  now: Date,
  timeZone: string,
): number | null {
  switch (period) {
    case "month":
    case "30d":
      return monthlyQuota;
    case "7d":
      return (monthlyQuota * 7) / 30;
    case "today":
      return monthlyQuota / daysInCurrentMonth(now, timeZone);
    case "all":
      return null;
  }
}

export function selectTransactionsByPeriod(
  transactions: Transaction[],
  period: ExpensePeriod,
  options?: ExpenseSelectorOptions,
): Transaction[] {
  const now = resolveNow(options);
  const timeZone = resolveTimeZone(options);

  return transactions
    .filter((transaction) => matchesPeriod(transaction, period, now, timeZone))
    .sort(compareByDateDesc);
}

export function selectFilteredExpenses(
  transactions: Transaction[],
  filters: ExpenseFilters = defaultExpenseFilters,
  options?: ExpenseSelectorOptions,
): Transaction[] {
  const now = resolveNow(options);
  const timeZone = resolveTimeZone(options);

  return transactions
    .filter((transaction) => getAmountInCents(transaction) < 0)
    .filter(
      (transaction) =>
        filters.showExternalAccounts || !transaction.is_external_account,
    )
    .filter((transaction) => !filters.hideTransfers || !transaction.is_transfer)
    .filter((transaction) =>
      matchesPeriod(transaction, filters.period, now, timeZone),
    )
    .filter(
      (transaction) =>
        !hasCategoryFilter(filters) ||
        filters.categoryFilter.includes(transaction.category),
    )
    .sort(compareByDateDesc);
}

export function selectAnalyticsExpenses(
  transactions: Transaction[],
  filters: ExpenseFilters = defaultExpenseFilters,
  options?: ExpenseSelectorOptions,
): Transaction[] {
  return selectFilteredExpenses(
    transactions,
    {
      ...filters,
      categoryFilter: [],
      period: "all",
    },
    options,
  );
}

export function selectAvailableCategories(
  transactions: Transaction[],
  limit = 8,
): string[] {
  return selectExpensesByCategory(transactions)
    .slice(0, limit)
    .map((entry) => entry.category);
}

export function selectTotalExpense(transactions: Transaction[]): number {
  const totalInCents = transactions.reduce(
    (sum, transaction) => sum + Math.abs(getAmountInCents(transaction)),
    0,
  );

  return centsToRubles(totalInCents);
}

export function selectExpensesByCategory(
  transactions: Transaction[],
): CategoryExpense[] {
  const categoryTotals = new Map<string, CategoryExpense>();

  for (const transaction of transactions) {
    const current = categoryTotals.get(transaction.category);
    const expenseAmount = centsToRubles(
      Math.abs(getAmountInCents(transaction)),
    );

    categoryTotals.set(transaction.category, {
      category: transaction.category,
      totalExpense: (current?.totalExpense ?? 0) + expenseAmount,
      transactionCount: (current?.transactionCount ?? 0) + 1,
    });
  }

  return [...categoryTotals.values()].sort((left, right) => {
    if (right.totalExpense !== left.totalExpense) {
      return right.totalExpense - left.totalExpense;
    }

    return left.category.localeCompare(right.category);
  });
}

export function selectCategoryBreakdown(
  transactions: Transaction[],
): CategoryBreakdownEntry[] {
  const categoryTotals = selectExpensesByCategory(transactions);
  const totalExpense = selectTotalExpense(transactions);
  const maxCategoryTotal = categoryTotals[0]?.totalExpense ?? 0;

  return categoryTotals.map((entry) => ({
    ...entry,
    sharePercentage:
      totalExpense > 0 ? (entry.totalExpense / totalExpense) * 100 : 0,
    widthPercentage:
      maxCategoryTotal > 0 ? (entry.totalExpense / maxCategoryTotal) * 100 : 0,
  }));
}

export function selectCategoryHeroSummary(
  currentTransactions: Transaction[],
  referenceTransactions: Transaction[],
  period: ExpensePeriod,
  options?: ExpenseSelectorOptions,
): CategoryHeroSummary {
  const currentCategories = selectExpensesByCategory(
    currentTransactions,
  ).filter((entry) => entry.category !== TRANSFER_CATEGORY);
  const currentCategoryTotal = currentCategories.reduce(
    (sum, entry) => sum + entry.totalExpense,
    0,
  );
  const topCategory = currentCategories[0] ?? null;
  const otherCategory =
    currentCategories.find((entry) => entry.category === OTHER_CATEGORY) ??
    null;

  let fastestGrowingCategory: CategoryDelta | null = null;

  if (period !== "all") {
    const previousCategories = selectExpensesByCategory(
      selectPreviousPeriodTransactions(referenceTransactions, period, options),
    ).filter((entry) => entry.category !== TRANSFER_CATEGORY);
    const currentCategoryMap = toExpenseMap(currentCategories);
    const previousCategoryMap = toExpenseMap(previousCategories);

    for (const category of new Set([
      ...currentCategoryMap.keys(),
      ...previousCategoryMap.keys(),
    ])) {
      const currentExpense =
        currentCategoryMap.get(category)?.totalExpense ?? 0;
      const previousExpense =
        previousCategoryMap.get(category)?.totalExpense ?? 0;
      const deltaExpense = currentExpense - previousExpense;

      if (deltaExpense <= 0) {
        continue;
      }

      if (
        !fastestGrowingCategory ||
        deltaExpense > fastestGrowingCategory.deltaExpense ||
        (deltaExpense === fastestGrowingCategory.deltaExpense &&
          currentExpense > fastestGrowingCategory.currentExpense) ||
        (deltaExpense === fastestGrowingCategory.deltaExpense &&
          currentExpense === fastestGrowingCategory.currentExpense &&
          category.localeCompare(fastestGrowingCategory.category) < 0)
      ) {
        fastestGrowingCategory = {
          category,
          currentExpense,
          previousExpense,
          deltaExpense,
        };
      }
    }
  }

  return {
    topCategory,
    topCategorySharePercentage:
      currentCategoryTotal > 0 && topCategory
        ? (topCategory.totalExpense / currentCategoryTotal) * 100
        : 0,
    fastestGrowingCategory,
    otherCategory,
    otherCategorySharePercentage:
      currentCategoryTotal > 0 && otherCategory
        ? (otherCategory.totalExpense / currentCategoryTotal) * 100
        : 0,
  };
}

export function selectExpensesByMonth(
  transactions: Transaction[],
  options?: ExpenseSelectorOptions,
): MonthExpense[] {
  const timeZone = resolveTimeZone(options);
  const monthTotals = new Map<string, MonthExpense>();

  for (const transaction of transactions) {
    const month = toMonthKey(transaction.date, timeZone);
    const current = monthTotals.get(month);
    const expenseAmount = centsToRubles(
      Math.abs(getAmountInCents(transaction)),
    );

    monthTotals.set(month, {
      month,
      label: formatMonthLabel(month, timeZone),
      totalExpense: (current?.totalExpense ?? 0) + expenseAmount,
      transactionCount: (current?.transactionCount ?? 0) + 1,
    });
  }

  return [...monthTotals.values()].sort((left, right) =>
    right.month.localeCompare(left.month),
  );
}

export function selectExpensesByMerchant(
  transactions: Transaction[],
  limit = 20,
  merchantSelector: MerchantSelector = getMerchantLabel,
): MerchantExpense[] {
  const merchantTotals = new Map<string, MerchantExpense>();

  for (const transaction of transactions) {
    const merchant = merchantSelector(transaction);
    const current = merchantTotals.get(merchant);
    const expenseAmount = centsToRubles(
      Math.abs(getAmountInCents(transaction)),
    );

    merchantTotals.set(merchant, {
      merchant,
      totalExpense: (current?.totalExpense ?? 0) + expenseAmount,
      transactionCount: (current?.transactionCount ?? 0) + 1,
    });
  }

  return [...merchantTotals.values()]
    .sort((left, right) => {
      if (right.totalExpense !== left.totalExpense) {
        return right.totalExpense - left.totalExpense;
      }

      if (right.transactionCount !== left.transactionCount) {
        return right.transactionCount - left.transactionCount;
      }

      return left.merchant.localeCompare(right.merchant);
    })
    .slice(0, limit);
}

export function selectCategoryDrilldownData(
  transactions: Transaction[],
  category: string,
  merchantLimit = 10,
  recentLimit = 20,
  merchantSelector: MerchantSelector = getMerchantLabel,
): CategoryDrilldownData {
  const categoryTransactions = transactions.filter(
    (transaction) => transaction.category === category,
  );

  return {
    category,
    topMerchants: selectExpensesByMerchant(
      categoryTransactions,
      merchantLimit,
      merchantSelector,
    ),
    recentTransactions: selectRecentExpenses(categoryTransactions, recentLimit),
  };
}

export function selectExpensesByCategoryByMonth(
  transactions: Transaction[],
  category: string,
  options?: ExpenseSelectorOptions,
): MonthExpense[] {
  return selectExpensesByMonth(
    transactions.filter((transaction) => transaction.category === category),
    options,
  );
}

export function selectExpensesByCategoryForMonth(
  transactions: Transaction[],
  month: string,
  options?: ExpenseSelectorOptions,
): CategoryExpense[] {
  const timeZone = resolveTimeZone(options);

  return selectExpensesByCategory(
    transactions.filter((transaction) =>
      matchesMonthKey(transaction, month, timeZone),
    ),
  );
}

export function selectExpensesByMerchantForMonth(
  transactions: Transaction[],
  month: string,
  options?: ExpenseSelectorOptions,
  limit = 5,
): MerchantExpense[] {
  const timeZone = resolveTimeZone(options);

  return selectExpensesByMerchant(
    transactions.filter((transaction) =>
      matchesMonthKey(transaction, month, timeZone),
    ),
    limit,
  );
}

export function selectAnalyticsSummary(
  transactions: Transaction[],
  options?: ExpenseSelectorOptions,
): AnalyticsSummary {
  const totalExpense = selectTotalExpense(transactions);
  const months = selectExpensesByMonth(transactions, options);
  const categories = selectExpensesByCategory(transactions);
  const nonTransferCategories = categories.filter(
    (entry) => entry.category !== TRANSFER_CATEGORY,
  );
  const nonTransferTotalExpense = nonTransferCategories.reduce(
    (sum, entry) => sum + entry.totalExpense,
    0,
  );
  const topCategory = nonTransferCategories[0];
  const peakMonth = [...months].sort((left, right) => {
    if (right.totalExpense !== left.totalExpense) {
      return right.totalExpense - left.totalExpense;
    }

    return right.month.localeCompare(left.month);
  })[0];

  return {
    totalExpense,
    monthlyAverageExpense: months.length > 0 ? totalExpense / months.length : 0,
    topCategoryName: topCategory?.category ?? "—",
    topCategorySharePercentage:
      nonTransferTotalExpense > 0 && topCategory
        ? (topCategory.totalExpense / nonTransferTotalExpense) * 100
        : 0,
    peakMonthLabel: peakMonth?.label ?? "—",
    peakMonthTotalExpense: peakMonth?.totalExpense ?? 0,
  };
}

export function selectExpensesByDay(
  transactions: Transaction[],
  options?: ExpenseSelectorOptions,
): DayExpense[] {
  const timeZone = resolveTimeZone(options);
  const dayTotals = new Map<string, DayExpense>();

  for (const transaction of transactions) {
    const day = toDayKey(transaction.date, timeZone);
    const current = dayTotals.get(day);
    const expenseAmount = centsToRubles(
      Math.abs(getAmountInCents(transaction)),
    );

    dayTotals.set(day, {
      day,
      totalExpense: (current?.totalExpense ?? 0) + expenseAmount,
      transactionCount: (current?.transactionCount ?? 0) + 1,
    });
  }

  return [...dayTotals.values()].sort((left, right) =>
    right.day.localeCompare(left.day),
  );
}

export function selectExpenseHistogram(
  transactions: Transaction[],
  options?: ExpenseSelectorOptions,
  days = 30,
): DayHistogramEntry[] {
  const now = resolveNow(options);
  const timeZone = resolveTimeZone(options);
  const expenseDays = new Map(
    selectExpensesByDay(transactions, options).map((entry) => [
      entry.day,
      entry,
    ]),
  );
  const dayKeys = buildTrailingDayKeys(now, timeZone, days);
  const todayKey = toDayKey(now, timeZone);

  const entries = dayKeys.map((day) => {
    const current = expenseDays.get(day);

    return {
      day,
      totalExpense: current?.totalExpense ?? 0,
      transactionCount: current?.transactionCount ?? 0,
    };
  });
  const maxDayExpense = Math.max(
    ...entries.map((entry) => entry.totalExpense),
    0,
  );

  return entries.map((entry) => ({
    ...entry,
    heightPercentage:
      maxDayExpense > 0 ? (entry.totalExpense / maxDayExpense) * 100 : 0,
    isToday: entry.day === todayKey,
  }));
}

export function selectRecentExpenses(
  transactions: Transaction[],
  count: number,
): Transaction[] {
  return [...transactions].sort(compareByDateDesc).slice(0, count);
}
