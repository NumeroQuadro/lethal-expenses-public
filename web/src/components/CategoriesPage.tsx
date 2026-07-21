import { useMemo, useState } from "react";

import { useExpenseDashboard } from "../context/expenseDashboardContext";
import {
  displayMerchant,
  selectCategoryBreakdown,
  selectCategoryDrilldownData,
  selectCategoryHeroSummary,
} from "../lib/expenses";
import { pluralRu } from "../lib/pluralRu";
import { PeriodSelector } from "./PeriodSelector";

const OTHER_CATEGORY = "Прочее";

function formatRub(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

function truncateLabel(value: string, limit = 40): string {
  if (value.length <= limit) {
    return value;
  }

  return `${value.slice(0, limit - 1)}…`;
}

function categoryRowId(category: string): string {
  return `category-row-${category
    .toLowerCase()
    .replace(/[^a-zа-яё0-9]+/gi, "-")
    .replace(/^-+|-+$/g, "")}`;
}

function scrollToCategory(category: string): void {
  document.getElementById(categoryRowId(category))?.scrollIntoView?.({
    behavior: "smooth",
    block: "center",
  });
}

export function CategoriesPage() {
  const {
    analyticsTransactions,
    filters,
    periodScopedTransactions,
    selectorOptions,
    setPeriod,
  } = useExpenseDashboard();
  const entries = useMemo(
    () => selectCategoryBreakdown(periodScopedTransactions),
    [periodScopedTransactions],
  );
  const summary = useMemo(
    () =>
      selectCategoryHeroSummary(
        periodScopedTransactions,
        analyticsTransactions,
        filters.period,
        selectorOptions,
      ),
    [
      analyticsTransactions,
      filters.period,
      periodScopedTransactions,
      selectorOptions,
    ],
  );
  const [selectedCategory, setSelectedCategory] = useState<string | null>(
    entries[0]?.category ?? null,
  );
  const activeSelectedCategory =
    selectedCategory === null
      ? null
      : entries.some((entry) => entry.category === selectedCategory)
        ? selectedCategory
        : (entries[0]?.category ?? null);
  const selectedDrilldown = activeSelectedCategory
    ? selectCategoryDrilldownData(
        periodScopedTransactions,
        activeSelectedCategory,
        10,
        20,
        displayMerchant,
      )
    : null;

  const handleOtherClick = () => {
    const hasOtherCategory = entries.some(
      (entry) => entry.category === OTHER_CATEGORY,
    );

    if (!hasOtherCategory) {
      return;
    }

    if (activeSelectedCategory === OTHER_CATEGORY) {
      scrollToCategory(OTHER_CATEGORY);
      return;
    }

    setSelectedCategory(OTHER_CATEGORY);
    requestAnimationFrame(() => scrollToCategory(OTHER_CATEGORY));
  };

  return (
    <section className="categories-page" aria-label="Категории">
      <header className="categories-page__header">
        <div>
          <p className="categories-page__eyebrow">Lethal Expenses</p>
          <h1 className="categories-page__title panel-title glow">КАТЕГОРИИ</h1>
        </div>
        <p className="categories-page__copy">
          Category-specific breakdown for the active period. Period chips update
          live; dashboard category chips are ignored here so the ranking stays
          complete.
        </p>
      </header>

      <section
        className="categories-page__period frame"
        aria-label="Выбор периода"
      >
        <p className="filters__label">ПЕРИОД</p>
        <PeriodSelector period={filters.period} onChange={setPeriod} />
      </section>

      {entries.length > 0 ? (
        <>
          <div className="categories-page__hero">
            <article className="overview-card frame">
              <p className="overview-card__label panel-title">ТОП КАТЕГОРИЯ</p>
              <p className="categories-page__hero-value glow">
                {summary.topCategory?.category ?? "—"}
              </p>
              <p className="overview-card__meta">
                {formatRub(summary.topCategory?.totalExpense ?? 0)} ₽ ·{" "}
                {formatPercent(summary.topCategorySharePercentage)}% от трат
              </p>
            </article>

            <article className="overview-card frame">
              <p className="overview-card__label panel-title">
                ВЫРОСЛО vs ПРОШЛЫЙ МЕС
              </p>
              <p className="categories-page__hero-value glow">
                {summary.fastestGrowingCategory?.category ?? "—"}
              </p>
              <p className="overview-card__meta">
                {summary.fastestGrowingCategory
                  ? `+${formatRub(summary.fastestGrowingCategory.deltaExpense)} ₽`
                  : "—"}
              </p>
            </article>

            <button
              type="button"
              className="overview-card frame categories-page__hero-card"
              onClick={handleOtherClick}
            >
              <p className="overview-card__label panel-title">ПРОЧЕЕ</p>
              <p className="overview-card__value glow">
                {summary.otherCategory?.transactionCount ?? 0}
              </p>
              <p className="overview-card__meta">
                {formatRub(summary.otherCategory?.totalExpense ?? 0)} ₽ ·{" "}
                {formatPercent(summary.otherCategorySharePercentage)}% от трат
              </p>
            </button>
          </div>

          <section
            className="categories-page__list frame"
            aria-label="Список категорий"
          >
            <div className="categories-page__list-header">
              <div>
                <p className="categories-page__section-eyebrow">
                  Current Period
                </p>
                <h2 className="categories-page__section-title panel-title glow">
                  СПИСОК КАТЕГОРИЙ
                </h2>
              </div>
            </div>

            <div className="categories-page__rows">
              {entries.map((entry) => {
                const isExpanded = entry.category === activeSelectedCategory;
                const drilldown =
                  isExpanded && selectedDrilldown?.category === entry.category
                    ? selectedDrilldown
                    : null;

                return (
                  <div key={entry.category} className="categories-page__entry">
                    <button
                      id={categoryRowId(entry.category)}
                      type="button"
                      className={`categories-page__row${isExpanded ? " is-expanded" : ""}`}
                      aria-expanded={isExpanded}
                      onClick={() =>
                        setSelectedCategory((current) =>
                          current === entry.category ? null : entry.category,
                        )
                      }
                    >
                      <span className="categories-page__row-name">
                        {entry.category}
                      </span>

                      <span
                        className="categories-page__row-bar"
                        aria-hidden="true"
                      >
                        <span
                          className="categories-page__row-fill"
                          style={{ width: `${entry.widthPercentage}%` }}
                        />
                      </span>

                      <span className="categories-page__row-count">
                        {entry.transactionCount}{" "}
                        {pluralRu(entry.transactionCount, [
                          "трата",
                          "траты",
                          "трат",
                        ])}
                      </span>

                      <span className="categories-page__row-value">
                        {formatRub(entry.totalExpense)} ₽ (
                        {formatPercent(entry.sharePercentage)}%)
                      </span>
                    </button>

                    {drilldown ? (
                      <div
                        className="categories-page__detail"
                        aria-label={`Детали категории ${entry.category}`}
                      >
                        <div className="categories-page__detail-grid">
                          <section className="categories-page__column">
                            <p className="categories-page__column-title">
                              ТОП МЕРЧАНТЫ
                            </p>

                            {drilldown.topMerchants.length > 0 ? (
                              <ol className="top-merchants__list categories-page__merchant-list">
                                {drilldown.topMerchants.map(
                                  (merchant, index) => (
                                    <li
                                      key={`${entry.category}-${merchant.merchant}`}
                                      className="top-merchants__row"
                                    >
                                      <span className="top-merchants__rank">
                                        {index + 1}.
                                      </span>
                                      <span className="top-merchants__merchant">
                                        {truncateLabel(merchant.merchant)}
                                      </span>
                                      <span className="top-merchants__count">
                                        {merchant.transactionCount}{" "}
                                        {pluralRu(merchant.transactionCount, [
                                          "трата",
                                          "траты",
                                          "трат",
                                        ])}
                                      </span>
                                      <span className="top-merchants__total">
                                        {formatRub(merchant.totalExpense)} ₽
                                      </span>
                                    </li>
                                  ),
                                )}
                              </ol>
                            ) : (
                              <p className="top-merchants__empty">
                                Нет мерчантов для отображения.
                              </p>
                            )}
                          </section>

                          <section className="categories-page__column">
                            <p className="categories-page__column-title">
                              ПОСЛЕДНИЕ ОПЕРАЦИИ
                            </p>

                            {drilldown.recentTransactions.length > 0 ? (
                              <ol className="categories-page__recent-list">
                                {drilldown.recentTransactions.map(
                                  (transaction) => (
                                    <li
                                      key={transaction.id}
                                      className="categories-page__recent-row"
                                    >
                                      <span className="categories-page__recent-date">
                                        {formatDate(transaction.date)}
                                      </span>
                                      <span className="categories-page__recent-merchant">
                                        {truncateLabel(
                                          transaction.merchant_raw ||
                                            transaction.description ||
                                            "БЕЗ НАЗВАНИЯ",
                                        )}
                                      </span>
                                      <span className="categories-page__recent-amount">
                                        -
                                        {formatRub(
                                          Math.abs(Number(transaction.amount)),
                                        )}{" "}
                                        ₽
                                      </span>
                                    </li>
                                  ),
                                )}
                              </ol>
                            ) : (
                              <p className="top-merchants__empty">
                                Нет операций для отображения.
                              </p>
                            )}
                          </section>
                        </div>

                        {entry.category === OTHER_CATEGORY ? (
                          <p className="categories-page__hint">
                            Чтобы убрать из Прочего: добавь regex в
                            parser/categories_overrides.yaml и перезапусти
                            build.
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>
        </>
      ) : (
        <section
          className="placeholder-panel frame"
          aria-label="Пустой период категорий"
        >
          <h2 className="panel-title glow">НЕТ ТРАТ</h2>
          <p>
            Для выбранного периода нет расходов. Переключите период или покажите
            переводы, если хотите проверить пустой срез.
          </p>
        </section>
      )}
    </section>
  );
}
