"use client"

import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import type { StockSnapshot } from "@/lib/stocks"

type SortKey = "forecastPct" | "dayChangePct" | "ticker"

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`
}

export function StockList({
  snapshots,
  selected,
  onSelect,
}: {
  snapshots: StockSnapshot[]
  selected: string
  onSelect: (ticker: string) => void
}) {
  const [query, setQuery] = useState("")
  const [sortKey, setSortKey] = useState<SortKey>("forecastPct")

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = snapshots.filter(
      (s) =>
        !q ||
        s.ticker.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.sector.toLowerCase().includes(q),
    )
    const sorted = [...filtered].sort((a, b) => {
      if (sortKey === "ticker") return a.ticker.localeCompare(b.ticker)
      return b[sortKey] - a[sortKey]
    })
    return sorted
  }, [snapshots, query, sortKey])

  const sorts: { key: SortKey; label: string }[] = [
    { key: "forecastPct", label: "Forecast" },
    { key: "dayChangePct", label: "Today" },
    { key: "ticker", label: "A–Z" },
  ]

  return (
    <div className="flex h-full flex-col rounded-2xl border border-border bg-card">
      <div className="border-b border-border p-4">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search ticker, name, sector"
            aria-label="Search stocks"
            className="w-full rounded-lg border border-border bg-secondary py-2 pl-9 pr-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>

        <div className="mt-3 flex items-center gap-1" role="group" aria-label="Sort stocks by">
          <span className="mr-1 text-xs text-muted-foreground">Sort</span>
          {sorts.map((s) => {
            const active = sortKey === s.key
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => setSortKey(s.key)}
                aria-pressed={active}
                className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {s.label}
              </button>
            )
          })}
        </div>
      </div>

      <ul className="min-h-0 flex-1 overflow-y-auto p-2">
        {rows.map((s) => {
          const active = s.ticker === selected
          const up = s.forecastPct >= 0
          return (
            <li key={s.ticker}>
              <button
                type="button"
                onClick={() => onSelect(s.ticker)}
                aria-current={active}
                className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                  active ? "bg-secondary ring-1 ring-inset ring-primary/40" : "hover:bg-secondary/60"
                }`}
              >
                <span className="min-w-0">
                  <span className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-foreground">
                      {s.ticker}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">{s.name}</span>
                  </span>
                  <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">
                    {s.sector}
                  </span>
                </span>
                <span className="flex shrink-0 flex-col items-end">
                  <span className="font-mono text-sm tabular-nums text-foreground">
                    {s.lastClose.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                  <span
                    className={`font-mono text-xs tabular-nums ${
                      up ? "text-primary" : "text-destructive"
                    }`}
                  >
                    {pct(s.forecastPct)}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
        {rows.length === 0 && (
          <li className="px-3 py-8 text-center text-sm text-muted-foreground">No matches.</li>
        )}
      </ul>
    </div>
  )
}
