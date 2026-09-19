"use client"

import { useMemo, useRef, useState } from "react"
import type { ForecastPoint, PricePoint } from "@/lib/sp500"

const W = 1000
const H = 380
const PAD = { top: 20, right: 64, bottom: 28, left: 12 }

type Node = {
  date: string
  value: number
  lower?: number
  upper?: number
  kind: "history" | "forecast"
}

function formatShortDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })
}

function formatValue(n: number) {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function ForecastChart({
  history,
  forecast,
}: {
  history: PricePoint[]
  forecast: ForecastPoint[]
}) {
  const svgRef = useRef<SVGSVGElement | null>(null)
  const [hover, setHover] = useState<number | null>(null)

  const {
    nodes,
    historyPath,
    forecastPath,
    bandPath,
    gridLines,
    splitX,
    xFor,
    yFor,
  } = useMemo(() => {
    const nodes: Node[] = [
      ...history.map((p) => ({ date: p.date, value: p.close, kind: "history" as const })),
      ...forecast.map((p) => ({
        date: p.date,
        value: p.value,
        lower: p.lower,
        upper: p.upper,
        kind: "forecast" as const,
      })),
    ]

    const values: number[] = []
    for (const n of nodes) {
      values.push(n.value)
      if (n.lower !== undefined) values.push(n.lower)
      if (n.upper !== undefined) values.push(n.upper)
    }
    const rawMin = Math.min(...values)
    const rawMax = Math.max(...values)
    const pad = (rawMax - rawMin) * 0.08 || 1
    const yMin = rawMin - pad
    const yMax = rawMax + pad

    const total = nodes.length
    const xFor = (i: number) =>
      PAD.left + (i / (total - 1)) * (W - PAD.left - PAD.right)
    const yFor = (v: number) =>
      PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom)

    const historyPath = history
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i).toFixed(2)} ${yFor(p.close).toFixed(2)}`)
      .join(" ")

    // Forecast line begins at the last historical point for continuity.
    const startIdx = history.length - 1
    const forecastNodes = [
      { i: startIdx, v: history[history.length - 1].close },
      ...forecast.map((p, k) => ({ i: history.length + k, v: p.value })),
    ]
    const forecastPath = forecastNodes
      .map((n, i) => `${i === 0 ? "M" : "L"} ${xFor(n.i).toFixed(2)} ${yFor(n.v).toFixed(2)}`)
      .join(" ")

    // Confidence band as a closed area (upper edge then lower edge reversed).
    const upperPts = [
      { i: startIdx, v: history[history.length - 1].close },
      ...forecast.map((p, k) => ({ i: history.length + k, v: p.upper })),
    ]
    const lowerPts = [
      ...forecast.map((p, k) => ({ i: history.length + k, v: p.lower })),
      { i: startIdx, v: history[history.length - 1].close },
    ].reverse()
    const bandPath =
      upperPts.map((n, i) => `${i === 0 ? "M" : "L"} ${xFor(n.i).toFixed(2)} ${yFor(n.v).toFixed(2)}`).join(" ") +
      " " +
      lowerPts.map((n) => `L ${xFor(n.i).toFixed(2)} ${yFor(n.v).toFixed(2)}`).join(" ") +
      " Z"

    const gridCount = 4
    const gridLines = Array.from({ length: gridCount + 1 }, (_, i) => {
      const v = yMin + (i / gridCount) * (yMax - yMin)
      return { y: yFor(v), value: v }
    })

    return {
      nodes,
      historyPath,
      forecastPath,
      bandPath,
      gridLines,
      splitX: xFor(history.length - 1),
      xFor,
      yFor,
    }
  }, [history, forecast])

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const relX = ((e.clientX - rect.left) / rect.width) * W
    const t = (relX - PAD.left) / (W - PAD.left - PAD.right)
    const idx = Math.round(t * (nodes.length - 1))
    setHover(Math.max(0, Math.min(nodes.length - 1, idx)))
  }

  const active = hover !== null ? nodes[hover] : null

  return (
    <div className="relative w-full">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-[300px] sm:h-[380px] touch-none select-none"
        onMouseMove={handleMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="S&P 500 historical prices with trend-line forecast and confidence band"
      >
        <defs>
          <linearGradient id="histFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Gridlines + right-side value axis */}
        {gridLines.map((g, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={g.y}
              y2={g.y}
              stroke="var(--color-border)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
            <text
              x={W - PAD.right + 8}
              y={g.y + 4}
              fill="var(--color-muted-foreground)"
              fontSize={13}
              fontFamily="var(--font-mono)"
            >
              {Math.round(g.value).toLocaleString("en-US")}
            </text>
          </g>
        ))}

        {/* History area fill */}
        <path
          d={`${historyPath} L ${splitX.toFixed(2)} ${H - PAD.bottom} L ${PAD.left} ${H - PAD.bottom} Z`}
          fill="url(#histFill)"
          stroke="none"
        />

        {/* Forecast confidence band */}
        <path d={bandPath} fill="var(--color-accent)" fillOpacity={0.14} stroke="none" />

        {/* Divider between history and forecast */}
        <line
          x1={splitX}
          x2={splitX}
          y1={PAD.top}
          y2={H - PAD.bottom}
          stroke="var(--color-muted-foreground)"
          strokeOpacity={0.4}
          strokeDasharray="3 4"
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />

        {/* History line */}
        <path
          d={historyPath}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Forecast trend line */}
        <path
          d={forecastPath}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={2}
          strokeDasharray="6 5"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Hover crosshair + marker */}
        {active && (
          <g>
            <line
              x1={xFor(hover!)}
              x2={xFor(hover!)}
              y1={PAD.top}
              y2={H - PAD.bottom}
              stroke="var(--color-foreground)"
              strokeOpacity={0.35}
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
            <circle
              cx={xFor(hover!)}
              cy={yFor(active.value)}
              r={4.5}
              fill={active.kind === "forecast" ? "var(--color-accent)" : "var(--color-primary)"}
              stroke="var(--color-background)"
              strokeWidth={2}
            />
          </g>
        )}
      </svg>

      {/* Tooltip */}
      {active && (
        <div
          className="pointer-events-none absolute top-2 rounded-md border border-border bg-popover/95 px-3 py-2 text-xs shadow-lg backdrop-blur"
          style={{
            left: `calc(${(xFor(hover!) / W) * 100}% + 0px)`,
            transform:
              xFor(hover!) > W * 0.6 ? "translateX(-105%)" : "translateX(12px)",
          }}
        >
          <div className="text-muted-foreground">{formatShortDate(active.date)}</div>
          <div className="mt-0.5 font-mono text-sm text-foreground">{formatValue(active.value)}</div>
          <div className="mt-1 flex items-center gap-1.5">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                active.kind === "forecast" ? "bg-accent" : "bg-primary"
              }`}
            />
            <span className="text-muted-foreground">
              {active.kind === "forecast" ? "Forecast" : "Historical"}
            </span>
          </div>
          {active.kind === "forecast" && active.lower !== undefined && active.upper !== undefined && (
            <div className="mt-1 font-mono text-[11px] text-muted-foreground">
              {formatValue(active.lower)} – {formatValue(active.upper)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
