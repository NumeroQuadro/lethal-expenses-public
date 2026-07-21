import { useState } from "react";

import {
  selectCategoryBreakdown,
  selectExpensesByCategoryByMonth,
  type ExpenseSelectorOptions,
} from "../lib/expenses";
import { pluralRu } from "../lib/pluralRu";
import type { Transaction } from "../types/transaction";

interface CategoryDrilldownProps extends ExpenseSelectorOptions {
  transactions: Transaction[];
}

function formatRub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

export function CategoryDrilldown({
  transactions,
  now,
  timeZone,
}: CategoryDrilldownProps) {
  const categories = selectCategoryBreakdown(transactions);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(
    categories[0]?.category ?? null,
  );
  const activeCategory =
    selectedCategory &&
    categories.some((entry) => entry.category === selectedCategory)
      ? selectedCategory
      : (categories[0]?.category ?? null);

  const monthlyBreakdown = activeCategory
    ? selectExpensesByCategoryByMonth(transactions, activeCategory, {
        now,
        timeZone,
      })
    : [];
  const maxTotal = Math.max(
    ...monthlyBreakdown.map((entry) => entry.totalExpense),
    0,
  );

  return (
    <section
      className="category-drilldown frame"
      aria-label="Категории по месяцам"
    >
      <div className="category-drilldown__header">
        <div>
          <p className="category-drilldown__eyebrow">Category Drill-down</p>
          <h2 className="category-drilldown__title panel-title glow">
            КАТЕГОРИИ × МЕСЯЦЫ
          </h2>
        </div>
      </div>

      {categories.length > 0 ? (
        <>
          <div
            className="category-drilldown__chips"
            role="group"
            aria-label="Категории аналитики"
          >
            {categories.map((entry) => {
              const isActive = entry.category === activeCategory;

              return (
                <button
                  key={entry.category}
                  type="button"
                  className={`filter-chip${isActive ? " is-active" : ""}`}
                  aria-pressed={isActive}
                  onClick={() => setSelectedCategory(entry.category)}
                >
                  {entry.category}
                </button>
              );
            })}
          </div>

          {activeCategory ? (
            <div className="category-drilldown__panel">
              <p className="category-drilldown__selected">{activeCategory}</p>

              {monthlyBreakdown.length > 0 ? (
                <div className="monthly-bars__list">
                  {monthlyBreakdown.map((entry) => {
                    const widthPercentage =
                      maxTotal > 0 ? (entry.totalExpense / maxTotal) * 100 : 0;

                    return (
                      <div
                        key={`${activeCategory}-${entry.month}`}
                        className="monthly-bars__row"
                      >
                        <p className="monthly-bars__label">{entry.label}</p>

                        <div className="monthly-bars__bar" aria-hidden="true">
                          <div
                            className="monthly-bars__fill"
                            style={{ width: `${widthPercentage}%` }}
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
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="category-drilldown__empty">
                  Нет трат в этой категории.
                </p>
              )}
            </div>
          ) : null}
        </>
      ) : (
        <p className="category-drilldown__empty">
          Нет категорий для drill-down.
        </p>
      )}
    </section>
  );
}
