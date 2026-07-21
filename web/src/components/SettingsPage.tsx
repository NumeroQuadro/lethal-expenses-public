import { MONTHLY_QUOTA_RUB } from '../config'

function formatRub(value: number): string {
  return new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value)
}

interface SettingsPageProps {
  quotaRub?: number
}

export function SettingsPage({ quotaRub = MONTHLY_QUOTA_RUB }: SettingsPageProps) {
  return (
    <section className="settings-page" aria-label="Настройки">
      <header className="settings-page__header">
        <p className="settings-page__eyebrow">Lethal Expenses</p>
        <h1 className="settings-page__title panel-title glow">НАСТРОЙКИ</h1>
        <p className="settings-page__copy">
          Пока только read-only параметры. Persistence и personal tuning придут отдельным
          фиче-паком.
        </p>
      </header>

      <section className="settings-panel frame">
        <div className="settings-panel__row">
          <p className="settings-panel__label">МЕСЯЧНАЯ КВОТА</p>
          <p className="settings-panel__value glow">{formatRub(quotaRub)} ₽</p>
        </div>

        <p className="settings-panel__copy">
          Значение читается из <code>web/src/config.ts</code> и пока не меняется из UI.
        </p>
      </section>
    </section>
  )
}
