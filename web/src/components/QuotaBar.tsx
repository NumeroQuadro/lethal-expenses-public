interface QuotaBarProps {
  percentage: number
}

function clampPercentage(value: number): number {
  return Math.max(0, Math.min(100, value))
}

export function QuotaBar({ percentage }: QuotaBarProps) {
  const width = clampPercentage(percentage)
  const color = percentage > 90 ? 'var(--accent)' : 'var(--fg-0)'

  return (
    <div className="quota-bar" aria-hidden="true">
      <div
        className="quota-bar__fill"
        style={{ backgroundColor: color, width: `${width}%` }}
      />
    </div>
  )
}
