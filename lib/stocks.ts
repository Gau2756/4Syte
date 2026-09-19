// A universe of individual S&P 500 constituents. Each stock gets its own
// deterministic synthetic price history (unique seed, drift, and volatility)
// so per-stock forecasts are stable and reproducible. No external API needed.

import { forecast, generateSeries, type ForecastResult, type PricePoint } from "@/lib/sp500"

export type Stock = {
  ticker: string
  name: string
  sector: string
  /** Current (most recent) close the series is locked to. */
  price: number
  /** Mean daily log-return. */
  drift: number
  /** Baseline daily volatility. */
  vol: number
}

// Illustrative constituents spanning several sectors. Prices, drift, and
// volatility are hand-tuned to give each name a distinct character.
export const STOCKS: Stock[] = [
  { ticker: "AAPL", name: "Apple Inc.", sector: "Information Technology", price: 232.4, drift: 0.0004, vol: 0.014 },
  { ticker: "MSFT", name: "Microsoft Corp.", sector: "Information Technology", price: 428.9, drift: 0.00045, vol: 0.013 },
  { ticker: "NVDA", name: "NVIDIA Corp.", sector: "Information Technology", price: 121.6, drift: 0.0011, vol: 0.028 },
  { ticker: "AMZN", name: "Amazon.com Inc.", sector: "Consumer Discretionary", price: 186.3, drift: 0.0005, vol: 0.018 },
  { ticker: "GOOGL", name: "Alphabet Inc.", sector: "Communication Services", price: 164.2, drift: 0.00042, vol: 0.016 },
  { ticker: "META", name: "Meta Platforms Inc.", sector: "Communication Services", price: 512.7, drift: 0.0006, vol: 0.021 },
  { ticker: "TSLA", name: "Tesla Inc.", sector: "Consumer Discretionary", price: 248.5, drift: 0.0003, vol: 0.036 },
  { ticker: "BRK.B", name: "Berkshire Hathaway", sector: "Financials", price: 462.1, drift: 0.0003, vol: 0.01 },
  { ticker: "JPM", name: "JPMorgan Chase & Co.", sector: "Financials", price: 214.8, drift: 0.00035, vol: 0.013 },
  { ticker: "V", name: "Visa Inc.", sector: "Financials", price: 276.4, drift: 0.00038, vol: 0.012 },
  { ticker: "UNH", name: "UnitedHealth Group", sector: "Health Care", price: 584.9, drift: 0.00025, vol: 0.015 },
  { ticker: "JNJ", name: "Johnson & Johnson", sector: "Health Care", price: 162.3, drift: 0.00015, vol: 0.009 },
  { ticker: "LLY", name: "Eli Lilly & Co.", sector: "Health Care", price: 892.6, drift: 0.0007, vol: 0.019 },
  { ticker: "XOM", name: "Exxon Mobil Corp.", sector: "Energy", price: 118.7, drift: 0.0002, vol: 0.015 },
  { ticker: "CVX", name: "Chevron Corp.", sector: "Energy", price: 148.2, drift: 0.00012, vol: 0.014 },
  { ticker: "WMT", name: "Walmart Inc.", sector: "Consumer Staples", price: 79.4, drift: 0.0004, vol: 0.011 },
  { ticker: "PG", name: "Procter & Gamble", sector: "Consumer Staples", price: 171.8, drift: 0.0002, vol: 0.009 },
  { ticker: "KO", name: "Coca-Cola Co.", sector: "Consumer Staples", price: 69.3, drift: 0.00018, vol: 0.008 },
  { ticker: "HD", name: "Home Depot Inc.", sector: "Consumer Discretionary", price: 402.5, drift: 0.0003, vol: 0.013 },
  { ticker: "CAT", name: "Caterpillar Inc.", sector: "Industrials", price: 388.9, drift: 0.00033, vol: 0.016 },
  { ticker: "BA", name: "Boeing Co.", sector: "Industrials", price: 154.6, drift: -0.0001, vol: 0.022 },
  { ticker: "DIS", name: "Walt Disney Co.", sector: "Communication Services", price: 96.2, drift: 0.00008, vol: 0.017 },
  { ticker: "NFLX", name: "Netflix Inc.", sector: "Communication Services", price: 701.3, drift: 0.0006, vol: 0.02 },
  { ticker: "AMD", name: "Advanced Micro Devices", sector: "Information Technology", price: 152.9, drift: 0.0007, vol: 0.03 },
]

// Stable per-ticker seed so each stock's series is deterministic.
function seedFor(ticker: string): number {
  let h = 2166136261
  for (let i = 0; i < ticker.length; i++) {
    h ^= ticker.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return (h >>> 0) % 2147483647
}

export function getStockHistory(stock: Stock): PricePoint[] {
  return generateSeries({
    endValue: stock.price,
    drift: stock.drift,
    baseVol: stock.vol,
    seed: seedFor(stock.ticker),
  })
}

/** Full history for every stock, keyed by ticker. Computed on the server. */
export function getAllHistories(): Record<string, PricePoint[]> {
  const out: Record<string, PricePoint[]> = {}
  for (const s of STOCKS) out[s.ticker] = getStockHistory(s)
  return out
}

export type StockSnapshot = {
  ticker: string
  name: string
  sector: string
  lastClose: number
  dayChangePct: number
  /** Projected % change over the default horizon, used for list sorting. */
  forecastPct: number
  rSquared: number
}

/** Lightweight per-stock summary for list rendering and sorting. */
export function getSnapshots(
  histories: Record<string, PricePoint[]>,
  horizonDays = 21,
): StockSnapshot[] {
  return STOCKS.map((s) => {
    const r: ForecastResult = forecast(histories[s.ticker], horizonDays)
    return {
      ticker: s.ticker,
      name: s.name,
      sector: s.sector,
      lastClose: r.lastClose,
      dayChangePct: r.dayChangePct,
      forecastPct: r.changePct,
      rSquared: r.rSquared,
    }
  })
}
