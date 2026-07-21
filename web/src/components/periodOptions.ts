import type { ExpensePeriod } from "../lib/expenses";

export const PERIOD_OPTIONS: Array<{ label: string; value: ExpensePeriod }> = [
  { label: "СЕГОДНЯ", value: "today" },
  { label: "7Д", value: "7d" },
  { label: "30Д", value: "30d" },
  { label: "МЕСЯЦ", value: "month" },
  { label: "ВСЁ ВРЕМЯ", value: "all" },
];
