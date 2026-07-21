import type { ExpensePeriod } from "../lib/expenses";
import { PERIOD_OPTIONS } from "./periodOptions";

interface PeriodSelectorProps {
  ariaLabel?: string;
  className?: string;
  period: ExpensePeriod;
  onChange: (period: ExpensePeriod) => void;
}

export function PeriodSelector({
  ariaLabel = "Период",
  className = "filters__chips",
  period,
  onChange,
}: PeriodSelectorProps) {
  return (
    <div className={className} role="group" aria-label={ariaLabel}>
      {PERIOD_OPTIONS.map((option) => {
        const isActive = period === option.value;

        return (
          <button
            key={option.value}
            type="button"
            className={`filter-chip${isActive ? " is-active" : ""}`}
            aria-pressed={isActive}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
