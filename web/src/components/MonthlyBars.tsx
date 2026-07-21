import { useState } from "react";

import {
  selectExpensesByCategoryForMonth,
  selectExpensesByMerchantForMonth,
  type ExpenseSelectorOptions,
  type MonthExpense,
} from "../lib/expenses";
import { pluralRu } from "../lib/pluralRu";
import type { Transaction } from "../types/transaction";

interface MonthlyBarsProps extends ExpenseSelectorOptions {
  entries: MonthExpense[];
  transactions: Transaction[];
  title?: string;
  eyebrow?: string;
  merchantLimit?: number;
}

function formatRub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function getMaxTotal(entries: Array<{ totalExpense: number }>): number {
  return Math.max(...entries.map((entry) => entry.totalExpense), 0);
}

export function MonthlyBars({
  entries,
  transactions,
  now,
  timeZone,
  title = "ПО МЕСЯЦАМ",
  eyebrow = "All-time Timeline",
  merchantLimit = 5,
}: MonthlyBarsProps) {
  const [expandedMonth, setExpandedMonth] = useState<string | null>(null);
  const activeExpandedMonth =
    expandedMonth && entries.some((entry) => entry.month === expandedMonth)
      ? expandedMonth
      : null;
  const maxTotal = getMaxTotal(entries);

  return (
    <section className="monthly-bars frame" aria-label={title}>
      <div className="monthly-bars__header">
        <div>
          <p className="monthly-bars__eyebrow">{eyebrow}</p>
          <h2 className="monthly-bars__title panel-title glow">{title}</h2>
        </div>
      </div>

      {entries.length > 0 ? (
        <div className="monthly-bars__list">
          {entries.map((entry) => {
            const isExpanded = entry.month === activeExpandedMonth;
            const widthPercentage =
              maxTotal > 0 ? (entry.totalExpense / maxTotal) * 100 : 0;
            const categoryEntries = isExpanded
              ? selectExpensesByCategoryForMonth(transactions, entry.month, {
                  now,
                  timeZone,
                })
              : [];
            const merchantEntries = isExpanded
              ? selectExpensesByMerchantForMonth(
                  transactions,
                  entry.month,
                  { now, timeZone },
                  merchantLimit,
                )
              : [];
            const maxCategoryTotal = getMaxTotal(categoryEntries);

            return (
              <div key={entry.month} className="monthly-bars__entry">
                <button
                  type="button"
                  className={
                    "monthly-bars__row monthly-bars__row--button" +
                    (isExpanded ? " is-expanded" : "")
                  }
                  aria-expanded={isExpanded}
                  onClick={() =>
                    setExpandedMonth(isExpanded ? null : entry.month)
                  }
                >
                  <p className="monthly-bars__label">{entry.label}</p>

                  <div className="monthly-bars__bar" aria-hidden="true">
                    <div
                      className="monthly-bars__fill"
                      style={{ width: String(widthPercentage) + "%" }}
                    />
                  </div>

                  <p className="monthly-bars__value">
                    <span>{formatRub(entry.totalExpense)} ₽</span>
                    <span>
                      {entry.transactionCount}{" "}
                      {pluralRu(entry.transactionCount, [
                        "трата",
                        "траты",
                        "трат",
                      ])}
                    </span>
                  </p>
                </button>

                {isExpanded ? (
                  <div className="monthly-bars__detail">
                    <p className="monthly-bars__detail-selected">
                      {entry.label}
                    </p>

                    <div className="monthly-bars__detail-grid">
                      <section
                        className="monthly-bars__detail-panel"
                        aria-label={"Категории " + entry.label}
                      >
                        <p className="monthly-bars__detail-title">
                          КАТЕГОРИИ МЕСЯЦА
                        </p>

                        {categoryEntries.length > 0 ? (
                          <div className="monthly-bars__detail-list">
                            {categoryEntries.map((categoryEntry) => {
                              const categoryWidth =
                                maxCategoryTotal > 0
                                  ? (categoryEntry.totalExpense /
                                      maxCategoryTotal) *
                                    100
                                  : 0;

                              return (
                                <div
                                  key={
                                    entry.month + "-" + categoryEntry.category
                                  }
                                  className="monthly-bars__row monthly-bars__detail-row"
                                >
                                  <p className="monthly-bars__detail-name">
                                    {categoryEntry.category}
                                  </p>

                                  <div
                                    className="monthly-bars__bar"
                                    aria-hidden="true"
                                  >
                                    <div
                                      className="monthly-bars__fill"
                                      style={{
                                        width: String(categoryWidth) + "%",
                                      }}
                                    />
                                  </div>

                                  <p className="monthly-bars__detail-value">
                                    <span>
                                      {formatRub(categoryEntry.totalExpense)} ₽
                                    </span>
                                    <span>
                                      {categoryEntry.transactionCount}{" "}
                                      {pluralRu(
                                        categoryEntry.transactionCount,
                                        ["трата", "траты", "трат"],
                                      )}
                                    </span>
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="monthly-bars__empty">
                            Нет категорий для отображения.
                          </p>
                        )}
                      </section>

                      <section
                        className="monthly-bars__detail-panel"
                        aria-label={"Мерчанты " + entry.label}
                      >
                        <p className="monthly-bars__detail-title">
                          ТОП-5 МЕРЧАНТОВ
                        </p>

                        {merchantEntries.length > 0 ? (
                          <ol className="top-merchants__list monthly-bars__merchant-list">
                            {merchantEntries.map((merchantEntry, index) => (
                              <li
                                key={entry.month + "-" + merchantEntry.merchant}
                                className="top-merchants__row"
                              >
                                <span className="top-merchants__rank">
                                  {index + 1}.
                                </span>
                                <span className="top-merchants__merchant">
                                  {merchantEntry.merchant}
                                </span>
                                <span className="top-merchants__count">
                                  {merchantEntry.transactionCount}{" "}
                                  {pluralRu(merchantEntry.transactionCount, [
                                    "трата",
                                    "траты",
                                    "трат",
                                  ])}
                                </span>
                                <span className="top-merchants__total">
                                  {formatRub(merchantEntry.totalExpense)} ₽
                                </span>
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p className="top-merchants__empty">
                            Нет мерчантов для отображения.
                          </p>
                        )}
                      </section>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="monthly-bars__empty">Нет данных по месяцам.</p>
      )}
    </section>
  );
}
