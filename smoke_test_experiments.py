"""Run short multi-seed smoke tests for experimental K-firm and bank variants."""
import argparse
import json
import os

from experiment_utils import apply_overrides, load_config, longest_run_below, parse_override, run_seed


def evaluate_result(result, thresholds):
    employment = result["series"]["employment"]
    bank_equity = result["series"]["bank_equity"]
    total_credit = result["series"]["total_credit"]
    investment_ac1 = result["metrics"]["Investment"]["ac1"]
    mean_employment = result["summary"]["mean_employment"]
    longest_low_run = longest_run_below(employment, thresholds["low_employment_threshold"])

    failures = []
    if longest_low_run >= thresholds["low_employment_span"]:
        failures.append("persistent low employment")
    if mean_employment < thresholds["min_mean_employment"] or mean_employment > thresholds["max_mean_employment"]:
        failures.append("mean employment outside band")
    if max(bank_equity) > thresholds["max_bank_equity"]:
        failures.append("bank equity runaway")
    if max(total_credit) > thresholds["max_total_credit"]:
        failures.append("credit runaway")
    if investment_ac1 < thresholds["min_investment_ac1"]:
        failures.append("investment AC(1) below threshold")
    if not all(value == value for value in employment + bank_equity + total_credit):
        failures.append("non-finite series")

    return {
        "passed": not failures,
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--periods", type=int, default=500)
    parser.add_argument("--burn", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--num-seeds", type=int, default=5)
    parser.add_argument("--low-employment-threshold", type=float, default=70.0)
    parser.add_argument("--low-employment-span", type=int, default=100)
    parser.add_argument("--min-mean-employment", type=float, default=85.0)
    parser.add_argument("--max-mean-employment", type=float, default=98.0)
    parser.add_argument("--max-bank-equity-multiple", type=float, default=25.0)
    parser.add_argument("--max-credit-multiple", type=float, default=50.0)
    parser.add_argument("--min-investment-ac1", type=float, default=0.0)
    parser.add_argument("--set", dest="overrides", action="append", default=[], help="Override config with dotted.path=value")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    config = load_config(config_path)
    overrides = [parse_override(text) for text in args.overrides]
    config = apply_overrides(config, overrides)
    config["experiments"]["diagnostics"] = True

    thresholds = {
        "low_employment_span": args.low_employment_span,
        "low_employment_threshold": args.low_employment_threshold,
        "min_mean_employment": args.min_mean_employment,
        "max_mean_employment": args.max_mean_employment,
        "max_bank_equity": config["bank"]["initial_equity"] * args.max_bank_equity_multiple,
        "max_total_credit": config["bank"]["initial_equity"] * args.max_credit_multiple,
        "min_investment_ac1": args.min_investment_ac1,
    }

    results = []
    for seed in range(args.seed_start, args.seed_start + args.num_seeds):
        result = run_seed(config, seed, args.periods, burn=args.burn, capture_diagnostics=True)
        verdict = evaluate_result(result, thresholds)
        result["smoke"] = verdict
        results.append(result)
        status = "PASS" if verdict["passed"] else "FAIL"
        print(
            f"{status} seed={seed} "
            f"mean_employment={result['summary']['mean_employment']:.2f} "
            f"investment_ac1={result['metrics']['Investment']['ac1']:.4f} "
            f"max_credit={result['summary']['max_total_credit']:.2f}"
        )
        if verdict["failures"]:
            print(f"  failures: {', '.join(verdict['failures'])}")

    passed = sum(1 for result in results if result["smoke"]["passed"])
    print(f"\nSmoke suite: {passed}/{len(results)} seeds passed")

    if args.output:
        payload = {
            "config": config_path,
            "overrides": dict(overrides),
            "thresholds": thresholds,
            "results": results,
        }
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        print(f"Saved smoke results to {args.output}")


if __name__ == "__main__":
    main()
