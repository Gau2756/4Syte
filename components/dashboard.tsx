"use client"

import { useMemo, useState } from "react"
import { Activity, ArrowDownRight, ArrowUpRight, Gauge, Target, TrendingUp } from "lucide-react"
import { forecast as computeForecast, type PricePoint } from "@/lib/sp500"
import { getSnapshots, STOCKS } from "@/lib/stocks"
import { ForecastChart } from "@/components/forecast-chart"
import { ForecastTable } from "@/components/forecast-table"
import { StatCard } from "@/components/stat-card"
import { StockList } from "@/components/stock-list"

const HORIZONS = [
  { label: "1W", days: 5 },
  { label: "1M", days: 21 },
  { label: "3M", days: 63 },
] as const

function fmt(n: number) {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function Dashboard({ histories }: { histories: Record<string, PricePoint[]> }) {
  const [horizon, setHorizon] = useState<number>(21)
  const [selected, setSelected] = useState<string>(STOCKS[0].ticker)

  const snapshots = useMemo(() => getSnapshots(histories, horizon), [histories, horizon])

  const stock = useMemo(() => STOCKS.find((s) => s.ticker === selected)!, [selected])
  const history = histories[selected]
  const result = useMemo(() => computeForecast(history, horizon), [history, horizon])
  const chartHistory = useMemo(() => history.slice(-140), [history])

  const dayUp = result.dayChangeAbs >= 0
  const horUp = result.changeAbs >= 0
  const asOf = new Date(history[history.length - 1].date).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  })

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
      {/* Header */}
      <header className="border-b border-border pb-6">
        <div className="flex items-center gap-2 text-primary">
          <TrendingUp className="h-5 w-5" aria-hidden />
          <span className="text-sm font-semibold uppercase tracking-widest">Meridian</span>
        </div>
        <h1 className="mt-3 text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          S&amp;P 500 Stock Forecaster
        </h1>
        <p className="mt-2 max-w-2xl text-pretty text-sm leading-relaxed text-muted-foreground">
          Pick any constituent to see a trend-line projection built from a least-squares fit on its
          recent performance, with a 90% confidence band that widens over the horizon.
        </p>
      </header>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,20rem)_1fr]">
        {/* Stock picker */}
        <div className="lg:h-[calc(100vh-8rem)] lg:min-h-[32rem]">
          <StockList snapshots={snapshots} selected={selected} onSelect={setSelected} />
        </div>

        {/* Detail */}
        <div>
          {/* Selected stock header */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-2xl font-semibold text-foreground">
                  {stock.ticker}
                </span>
                <span className="text-sm text-muted-foreground">{stock.name}</span>
              </div>
              <span className="mt-1 inline-block rounded-full border border-border bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground">
                {stock.sector}
              </span>
            </div>

            <div className="flex flex-col items-start gap-1 sm:items-end">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">
                Last close · {asOf}
              </span>
              <div className="font-mono text-3xl font-semibold tabular-nums text-foreground">
                {fmt(result.lastClose)}
              </div>
              <div
                className={`flex items-center gap-1 font-mono text-sm ${
                  dayUp ? "text-primary" : "text-destructive"
                }`}
              >
                {dayUp ? (
                  <ArrowUpRight className="h-4 w-4" aria-hidden />
                ) : (
                  <ArrowDownRight className="h-4 w-4" aria-hidden />
                )}
                {dayUp ? "+" : ""}
                {fmt(result.dayChangeAbs)} ({dayUp ? "+" : ""}
                {result.dayChangePct.toFixed(2)}%)
              </div>
            </div>
          </div>

          {/* Chart card */}
          <section className="mt-6 rounded-2xl border border-border bg-card p-4 sm:p-6">
            <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-2">
                  <span className="inline-block h-0.5 w-5 rounded bg-primary" />
                  Historical
                </span>
                <span className="flex items-center gap-2">
                  <span className="inline-block h-0.5 w-5 rounded bg-accent" />
                  Forecast
                </span>
                <span className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-4 rounded-sm bg-accent/25" />
                  90% confidence
                </span>
              </div>

              <div
                className="inline-flex items-center rounded-lg border border-border bg-secondary p-1"
                role="group"
                aria-label="Forecast horizon"
              >
                {HORIZONS.map((h) => {
                  const activeSel = horizon === h.days
                  return (
                    <button
                      key={h.label}
                      type="button"
                      onClick={() => setHorizon(h.days)}
                      aria-pressed={activeSel}
                      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                        activeSel
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {h.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <ForecastChart key={selected} history={chartHistory} forecast={result.forecast} />
          </section>

          {/* Stats */}
          <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={`Target · ${result.horizonDays}d`}
              value={fmt(result.projectedClose)}
              tone={horUp ? "up" : "down"}
              icon={<Target className="h-4 w-4" aria-hidden />}
              sub={
                <span className={horUp ? "text-primary" : "text-destructive"}>
                  {horUp ? "+" : ""}
                  {fmt(result.changeAbs)} ({horUp ? "+" : ""}
                  {result.changePct.toFixed(2)}%)
                </span>
              }
            />
            <StatCard
              label="Annualized trend"
              value={`${result.annualizedTrendPct >= 0 ? "+" : ""}${result.annualizedTrendPct.toFixed(2)}%`}
              tone={result.annualizedTrendPct >= 0 ? "up" : "down"}
              icon={<TrendingUp className="h-4 w-4" aria-hidden />}
              sub="Compounded slope of the fit"
            />
            <StatCard
              label="Trend fit (R²)"
              value={result.rSquared.toFixed(3)}
              icon={<Gauge className="h-4 w-4" aria-hidden />}
              sub={
                result.rSquared > 0.7
                  ? "Strong linear fit"
                  : result.rSquared > 0.4
                    ? "Moderate linear fit"
                    : "Weak linear fit"
              }
            />
            <StatCard
              label="Daily volatility"
              value={`${result.volatilityPct.toFixed(2)}%`}
              icon={<Activity className="h-4 w-4" aria-hidden />}
              sub="1σ of fit residuals"
            />
          </section>

          {/* Table */}
          <section className="mt-6">
            <ForecastTable forecast={result.forecast} lastClose={result.lastClose} />
          </section>
        </div>
      </div>

      <footer className="mt-10 border-t border-border pt-6 text-xs leading-relaxed text-muted-foreground">
        <p className="max-w-2xl text-pretty">
          Illustrative model on synthetic per-stock data. A linear trend extrapolation cannot
          capture earnings, news, or macro shocks and is not investment advice.
        </p>
      </footer>
    </main>
  )
}
