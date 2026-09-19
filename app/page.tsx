import { Dashboard } from "@/components/dashboard"
import { getAllHistories } from "@/lib/stocks"

export default function Page() {
  // Deterministic synthetic history for every stock, generated on the server
  // and handed to the client dashboard, which recomputes each stock's trend
  // forecast per selected horizon.
  const histories = getAllHistories()
  return <Dashboard histories={histories} />
}
