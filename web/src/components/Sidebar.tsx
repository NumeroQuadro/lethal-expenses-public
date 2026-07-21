export type DashboardView =
  | 'overview'
  | 'transactions'
  | 'categories'
  | 'analytics'
  | 'settings'

interface SidebarProps {
  currentView: DashboardView
  onSelectView: (view: DashboardView) => void
}

const NAV_ITEMS: Array<{ label: string; view: DashboardView }> = [
  { label: 'Обзор', view: 'overview' },
  { label: 'Траты', view: 'transactions' },
  { label: 'Категории', view: 'categories' },
  { label: 'Аналитика', view: 'analytics' },
  { label: 'Настройки', view: 'settings' },
]

export function Sidebar({ currentView, onSelectView }: SidebarProps) {
  return (
    <aside className="sidebar frame" aria-label="Primary">
      <div className="sidebar__brand">
        <p className="sidebar__eyebrow">LETHAL</p>
        <h2 className="sidebar__title panel-title glow">Expenses</h2>
      </div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => {
          const isActive = item.view === currentView

          return (
            <button
              key={item.view}
              type="button"
              className={`sidebar__item${isActive ? ' is-active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => onSelectView(item.view)}
            >
              {item.label}
            </button>
          )
        })}
      </nav>
    </aside>
  )
}
