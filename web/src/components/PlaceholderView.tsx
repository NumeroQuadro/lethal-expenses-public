interface PlaceholderViewProps {
  title: string
  copy: string
}

export function PlaceholderView({ title, copy }: PlaceholderViewProps) {
  return (
    <section className="placeholder-view" aria-label={title}>
      <header className="placeholder-view__header">
        <p className="placeholder-view__eyebrow">Lethal Expenses</p>
        <h1 className="placeholder-view__title panel-title glow">{title}</h1>
        <p className="placeholder-view__copy">{copy}</p>
      </header>

      <section className="placeholder-panel frame">
        <h2 className="panel-title glow">СТАТУС</h2>
        <p>
          Этот экран остаётся минимальным stub до следующего батча. Навигация уже живая,
          поэтому сюда можно безопасно наращивать отдельные потоки без ломки overview.
        </p>
      </section>
    </section>
  )
}
