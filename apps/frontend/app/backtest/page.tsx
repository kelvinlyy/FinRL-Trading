import { redirect } from "next/navigation";

/** Backtest UI merged into home; keep this route for bookmarks. */
export default function BacktestLegacyRedirect() {
  redirect("/#run-backtest");
}
