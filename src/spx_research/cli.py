import argparse
from pathlib import Path

from .backtest import expanding_window_backtest
from .demo import synthetic_dataset
from .pipeline import enforce_point_in_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual-LLM SPX research scaffold")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    if args.command == "demo":
        args.output.mkdir(parents=True, exist_ok=True)
        frame = enforce_point_in_time(synthetic_dataset())
        result = expanding_window_backtest(frame)
        result.predictions.to_csv(args.output / "predictions.csv", index=False)
        result.metrics.to_csv(args.output / "metrics.csv", index=False)
        print(result.metrics.to_string(index=False))


if __name__ == "__main__":
    main()
