// Self-contained S&P 500 data + trend-line forecast.
// History is generated deterministically (seeded) so the dashboard is stable
// across renders and reloads. No external API required.

export type PricePoint = {
  /** ISO date string, e.g. "2026-09-19" */
  date: string
  /** Closing index value */
  close: number
}

export type ForecastPoint = {
  date: string
  /** Central trend-line projection */
  value: number
  /** Lower confidence bound */
  lower: number
  /** Upper confidence bound */
  upper: number
}

export type ForecastResult = {
  history: PricePoint[]
  forecast: ForecastPoint[]
  /** Last known close */
  lastClose: number
  /** Projected close at the end of the horizon */
  projectedClose: number
  /** Absolute change over the horizon */
  changeAbs: number
  /** Percent change over the horizon */
  changePct: number
  /** Daily change vs the previous close */
  dayChangeAbs: number
  dayChangePct: number
  /** Annualized trend (compounded daily slope) */
  annualizedTrendPct: number
  /** R^2 of the fitted trend line on the recent window (0..1) */
  rSquared: number
  /** Coefficient of one-sigma band as a percent of price */
  volatilityPct: number
  horizonDays: number
}

// Mulberry32 seeded PRNG for deterministic, reproducible history.
function mulberry32(seed: number) {
  let a = seed
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// Standard normal via Box–Muller.
function randNormal(rng: () => number) {
  let u = 0
  let v = 0
  while (u === 0) u = rng()
  while (v === 0) v = rng()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

function isWeekend(d: Date) {
  const day = d.getUTCDay()
  return day === 0 || day === 6
}

function fmt(d: Date) {
  return d.toISOString().slice(0, 10)
}

export type SeriesOptions = {
  tradingDays?: number
  /** Value the series is locked to on its final (most recent) close. */
  endValue?: number
  seed?: number
  /** Mean daily log-return (drift). ~0.0003 ≈ 7.8% annualized. */
  drift?: number
  /** Baseline daily volatility (std dev of log-returns). */
  baseVol?: number
  /** Chance per day of entering a volatility spike. */
  spikeChance?: number
  /**
   * Fixed reference date (ISO `YYYY-MM-DD`) the most recent close is anchored
   * to. Must be deterministic — never derive it from `new Date()` at render
   * time, or the server-rendered dates will drift from the client and cause a
   * hydration mismatch.
   */
  anchorDate?: string
}

/** Deterministic "as of" date for all generated series. */
export const ANCHOR_DATE = "2026-09-18"

/**
 * Generate ~`tradingDays` of synthetic daily closes ending today, using a
 * geometric random walk with configurable drift and occasional volatility
 * clusters so the series looks like a real traded asset.
 */
export function generateSeries(opts: SeriesOptions = {}): PricePoint[] {
  const {
    tradingDays = 504,
    endValue = 5810,
    seed = 20260919,
    drift = 0.0003,
    baseVol = 0.006,
    spikeChance = 0.015,
    anchorDate = ANCHOR_DATE,
  } = opts
  const rng = mulberry32(seed)
  const points: PricePoint[] = []

  // Walk backwards in calendar time to collect trading days, then reverse.
  // The cursor starts from a FIXED anchor date (parsed as UTC) so the series is
  // identical on server and client — no live-clock drift, no hydration mismatch.
  const dates: Date[] = []
  const cursor = new Date(`${anchorDate}T00:00:00.000Z`)
  while (dates.length < tradingDays) {
    if (!isWeekend(cursor)) dates.push(new Date(cursor))
    cursor.setUTCDate(cursor.getUTCDate() - 1)
  }
  dates.reverse()

  // Build a forward series then rescale so the final close equals endValue.
  let logPrice = Math.log(endValue) - drift * tradingDays
  let vol = baseVol
  const raw: number[] = []
  for (let i = 0; i < tradingDays; i++) {
    // Volatility clustering: occasionally spike, then decay back to baseline.
    if (rng() < spikeChance) vol = baseVol * 2 + rng() * baseVol * 2
    vol += (baseVol - vol) * 0.06
    const shock = randNormal(rng) * vol
    logPrice += drift + shock
    raw.push(Math.exp(logPrice))
  }

  // Rescale to lock the last value to endValue for a clean, current-looking chart.
  const scale = endValue / raw[raw.length - 1]
  const decimals = endValue < 2000 ? 100 : 1
  for (let i = 0; i < tradingDays; i++) {
    points.push({ date: fmt(dates[i]), close: Math.round(raw[i] * scale * decimals) / decimals })
  }
  return points
}

/** Back-compat helper for the whole-index series. */
export function generateHistory(tradingDays = 504, endValue = 5810, seed = 20260919): PricePoint[] {
  return generateSeries({ tradingDays, endValue, seed })
}

// Ordinary least squares on (x, y).
function linreg(xs: number[], ys: number[]) {
  const n = xs.length
  const meanX = xs.reduce((s, v) => s + v, 0) / n
  const meanY = ys.reduce((s, v) => s + v, 0) / n
  let sxy = 0
  let sxx = 0
  let syy = 0
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - meanX
    const dy = ys[i] - meanY
    sxy += dx * dy
    sxx += dx * dx
    syy += dy * dy
  }
  const slope = sxy / sxx
  const intercept = meanY - slope * meanX
  const r2 = syy === 0 ? 0 : (sxy * sxy) / (sxx * syy)
  return { slope, intercept, r2 }
}

function addTradingDays(from: Date, count: number): Date[] {
  const out: Date[] = []
  const cursor = new Date(from)
  while (out.length < count) {
    cursor.setUTCDate(cursor.getUTCDate() + 1)
    if (!isWeekend(cursor)) out.push(new Date(cursor))
  }
  return out
}

/**
 * Fit a linear trend on the log-price of the recent window and project it
 * forward. A confidence band is derived from the residual standard deviation.
 */
export function forecast(history: PricePoint[], horizonDays = 30, window = 120): ForecastResult {
  const recent = history.slice(-window)
  const xs = recent.map((_, i) => i)
  const ys = recent.map((p) => Math.log(p.close))
  const { slope, intercept, r2 } = linreg(xs, ys)

  // Residual std dev on the fitted window (in log space).
  let sse = 0
  for (let i = 0; i < recent.length; i++) {
    const fitted = intercept + slope * xs[i]
    sse += (ys[i] - fitted) ** 2
  }
  const sigma = Math.sqrt(sse / Math.max(1, recent.length - 2))

  const lastIndex = recent.length - 1
  const lastDate = new Date(history[history.length - 1].date)
  const futureDates = addTradingDays(lastDate, horizonDays)

  const forecastPoints: ForecastPoint[] = futureDates.map((d, k) => {
    const x = lastIndex + k + 1
    const logVal = intercept + slope * x
    // Band widens with the square root of the projection distance.
    const spread = 1.645 * sigma * Math.sqrt(k + 1) // ~90% band
    return {
      date: fmt(d),
      value: Math.round(Math.exp(logVal) * 100) / 100,
      lower: Math.round(Math.exp(logVal - spread) * 100) / 100,
      upper: Math.round(Math.exp(logVal + spread) * 100) / 100,
    }
  })

  const lastClose = history[history.length - 1].close
  const prevClose = history[history.length - 2].close
  const projectedClose = forecastPoints[forecastPoints.length - 1].value
  const changeAbs = Math.round((projectedClose - lastClose) * 100) / 100
  const changePct = (changeAbs / lastClose) * 100
  const dayChangeAbs = Math.round((lastClose - prevClose) * 100) / 100
  const dayChangePct = (dayChangeAbs / prevClose) * 100
  const annualizedTrendPct = (Math.exp(slope * 252) - 1) * 100
  const volatilityPct = (Math.exp(sigma) - 1) * 100

  return {
    history,
    forecast: forecastPoints,
    lastClose,
    projectedClose,
    changeAbs,
    changePct,
    dayChangeAbs,
    dayChangePct,
    annualizedTrendPct,
    rSquared: Math.round(r2 * 1000) / 1000,
    volatilityPct: Math.round(volatilityPct * 100) / 100,
    horizonDays,
  }
}

export function getForecastData(horizonDays = 30): ForecastResult {
  const history = generateHistory()
  return forecast(history, horizonDays)
}
