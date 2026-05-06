#!/usr/bin/env python3
"""
Paper trading step for deploy.sh: run any registered strategy runner, load signal JSON, execute Alpaca.

Expects the runner's single-date mode to write ``signal_<YYYY-MM-DD>.json`` under ``paths.weights_dir``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, help="Path to strategy runner .py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--dry-run", choices=("true", "false"), default="false")
    parser.add_argument("--account", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    runner = Path(args.runner)
    if not runner.is_file():
        raise FileNotFoundError(runner)

    print(f"\n--- Step 3a: Generating signal via {runner.name} for {args.date} ---\n")
    cmd = [
        sys.executable,
        str(runner.resolve()),
        "--config",
        args.config,
        "--data-dir",
        args.data_dir,
        "--date",
        args.date,
    ]
    subprocess.check_call(cmd, cwd=str(project_root))

    import yaml

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    weights_dir = Path(cfg["paths"]["weights_dir"])
    signal_file = weights_dir / f"signal_{args.date}.json"
    if not signal_file.is_file():
        print(f"Error: signal file not found: {signal_file}")
        sys.exit(1)

    signal_data = json.loads(signal_file.read_text(encoding="utf-8"))
    target_weights = signal_data.get("weights") or {}
    if not target_weights:
        print("\n  No positions to trade. Exiting.")
        sys.exit(0)

    print(f"\n  Regime: {signal_data.get('regime')}")
    print(f"  Signal file: {signal_file}")

    dry_run = args.dry_run.lower() == "true"
    account_name = args.account.strip() or None

    print(f"\n--- Step 3b: {'[DRY RUN] ' if dry_run else ''}Executing on Alpaca Paper Trading ---\n")

    from src.trading.alpaca_manager import AlpacaManager, create_alpaca_account_from_env

    if account_name:
        account = create_alpaca_account_from_env(account_name)
    else:
        account = create_alpaca_account_from_env()

    if not account.is_paper:
        print("  ERROR: Account is NOT paper trading!")
        print(f"  Base URL: {account.base_url}")
        sys.exit(1)

    manager = AlpacaManager([account])
    account_info = manager.get_account_info()
    print(f"  Account:        {account.name} (paper)")
    print(f"  Equity:         ${float(account_info.get('equity', 0)):,.2f}")
    print(f"  Cash:           ${float(account_info.get('cash', 0)):,.2f}")
    print(f"  Portfolio Value: ${float(account_info.get('portfolio_value', 0)):,.2f}")

    positions = manager.get_positions()
    print(f"  Current Positions: {len(positions)}")
    if positions:
        for pos in positions:
            sym = pos.get("symbol", "?")
            qty = pos.get("qty", 0)
            mv = float(pos.get("market_value", 0))
            print(f"    {sym:8s}: {qty} shares (${mv:,.2f})")

    print(f"\n  Target weights: {json.dumps(target_weights, indent=4)}")

    result = manager.execute_portfolio_rebalance(
        target_weights=target_weights,
        account_name=account.name,
        dry_run=dry_run,
        market_closed_action="skip",
    )

    print(f"\n  {'[DRY RUN] ' if dry_run else ''}Rebalance result:")
    if dry_run or result.get("orders_plan"):
        orders_plan = result.get("orders_plan", result)
        print(f"    Plan: {json.dumps(orders_plan, indent=4, default=str)}")
    else:
        n_placed = result.get("orders_placed", 0)
        orders = result.get("orders", [])
        print(f"    Orders placed: {n_placed}")
        for o in orders:
            if isinstance(o, dict):
                side = o.get("side", "?")
                sym = o.get("symbol", "?")
                qty = o.get("qty", o.get("quantity", "?"))
            else:
                side = getattr(o, "side", "?")
                sym = getattr(o, "symbol", "?")
                qty = getattr(o, "qty", getattr(o, "quantity", "?"))
            print(f"      {str(side).upper():5s} {sym:8s} x {qty}")

    exec_file = weights_dir / f"execution_{args.date}.json"
    exec_data = {
        "date": args.date,
        "dry_run": dry_run,
        "account": account.name,
        "signal": signal_data,
        "result": result,
    }
    exec_file.write_text(json.dumps(exec_data, indent=2, default=str), encoding="utf-8")
    print(f"\n  Execution log saved to: {exec_file}")


if __name__ == "__main__":
    main()
