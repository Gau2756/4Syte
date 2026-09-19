import type { ReactNode } from "react"

export function StatCard({
  label,
  value,
  sub,
  tone = "neutral",
  icon,
}: {
  label: string
  value: string
  sub?: ReactNode
  tone?: "neutral" | "up" | "down"
  icon?: ReactNode
}) {
  const toneClass =
    tone === "up"
      ? "text-primary"
      : tone === "down"
        ? "text-destructive"
        : "text-foreground"

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        {icon ? <span className="text-muted-foreground">{icon}</span> : null}
      </div>
      <div className={`mt-3 font-mono text-2xl font-semibold tabular-nums ${toneClass}`}>
        {value}
      </div>
      {sub ? <div className="mt-1 text-sm text-muted-foreground">{sub}</div> : null}
    </div>
  )
}
