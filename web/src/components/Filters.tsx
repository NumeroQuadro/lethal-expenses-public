import { useExpenseDashboard } from "../context/expenseDashboardContext";
import { PeriodSelector } from "./PeriodSelector";

function buildCategoryOptions(
  availableCategories: string[],
  selectedCategories: string[],
): string[] {
  return [...new Set([...selectedCategories, ...availableCategories])];
}

export function Filters() {
  const {
    availableCategories,
    clearCategoryFilter,
    filters,
    setHideTransfers,
    setPeriod,
    setShowExternalAccounts,
    toggleCategory,
  } = useExpenseDashboard();

  const categoryOptions = buildCategoryOptions(
    availableCategories,
    filters.categoryFilter,
  );
  const hasCategoryFilter = filters.categoryFilter.length > 0;

  return (
    <section className="filters frame" aria-label="Фильтры">
      <div className="filters__header">
        <div>
          <p className="filters__eyebrow">Dashboard Controls</p>
          <h2 className="filters__title panel-title glow">ФИЛЬТРЫ</h2>
        </div>
      </div>

      <div className="filters__group">
        <p className="filters__label">ПЕРИОД</p>
        <PeriodSelector period={filters.period} onChange={setPeriod} />
      </div>

      <div className="filters__group filters__group--toggle">
        <div>
          <p className="filters__label">ПЕРЕВОДЫ</p>
          <p className="filters__copy">
            Скрыты по умолчанию и исключены из итогов.
          </p>
        </div>

        <button
          type="button"
          className={`filter-toggle${filters.hideTransfers ? " is-active" : ""}`}
          role="switch"
          aria-checked={filters.hideTransfers}
          data-testid="hide-transfers-toggle"
          onClick={() => setHideTransfers(!filters.hideTransfers)}
        >
          СКРЫТЬ ПЕРЕВОДЫ
        </button>
      </div>

      <div className="filters__group filters__group--toggle">
        <div>
          <p className="filters__label">ВНЕШНИЕ СЧЕТА</p>
          <p className="filters__copy">
            Скрыты по умолчанию, чтобы relay-операции не смешивались с вашими
            итогами.
          </p>
        </div>

        <button
          type="button"
          className={`filter-toggle${filters.showExternalAccounts ? " is-active" : ""}`}
          role="switch"
          aria-checked={filters.showExternalAccounts}
          data-testid="show-external-toggle"
          onClick={() => setShowExternalAccounts(!filters.showExternalAccounts)}
        >
          ПОКАЗАТЬ ВНЕШНИЕ СЧЕТА
        </button>
      </div>

      <div className="filters__group">
        <p className="filters__label">КАТЕГОРИИ</p>
        <div className="filters__chips" role="group" aria-label="Категории">
          <button
            type="button"
            className={`filter-chip${!hasCategoryFilter ? " is-active" : ""}`}
            aria-pressed={!hasCategoryFilter}
            onClick={clearCategoryFilter}
          >
            ВСЕ
          </button>

          {categoryOptions.map((category) => {
            const isActive = filters.categoryFilter.includes(category);

            return (
              <button
                key={category}
                type="button"
                className={`filter-chip${isActive ? " is-active" : ""}`}
                aria-pressed={isActive}
                onClick={() => toggleCategory(category)}
              >
                {category}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
