import type { ForecastPoint } from "@/lib/sp500"

function fmt(n: number) {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  })
}

export function ForecastTable({
  forecast,
  lastClose,
}: {
  forecast: ForecastPoint[]
  lastClose: number
}) {
  // Show a readable subset of key horizon milestones.
  const milestones = forecast.filter((_, i) => {
    const n = forecast.length
    return i === 0 || i === Math.floor(n / 4) || i === Math.floor(n / 2) || i === Math.floor((3 * n) / 4) || i === n - 1
  })

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="border-b border-border px-5 py-4">
        <h3 className="text-sm font-semibold text-foreground">Projected milestones</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Trend value and 90% confidence range at key points in the horizon
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-5 py-3 font-medium">Date</th>
              <th className="px-5 py-3 text-right font-medium">Forecast</th>
              <th className="px-5 py-3 text-right font-medium">Range</th>
              <th className="px-5 py-3 text-right font-medium">vs. today</th>
            </tr>
          </thead>
          <tbody>
            {milestones.map((p) => {
              const delta = ((p.value - lastClose) / lastClose) * 100
              const up = delta >= 0
              return (
                <tr key={p.date} className="border-t border-border/60">
                  <td className="px-5 py-3 text-foreground">{fmtDate(p.date)}</td>
                  <td className="px-5 py-3 text-right font-mono tabular-nums text-foreground">
                    {fmt(p.value)}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-xs tabular-nums text-muted-foreground">
                    {fmt(p.lower)} – {fmt(p.upper)}
                  </td>
                  <td
                    className={`px-5 py-3 text-right font-mono tabular-nums ${
                      up ? "text-primary" : "text-destructive"
                    }`}
                  >
                    {up ? "+" : ""}
                    {delta.toFixed(2)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
