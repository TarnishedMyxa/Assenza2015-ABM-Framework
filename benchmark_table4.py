"""Benchmark the model against the journal Table 4 protocol."""
import argparse
import json
import multiprocessing as mp
import os

from experiment_utils import apply_overrides, load_config, parse_override, run_seed, summarize_table4


TABLE4_TARGETS = {
    "GDP": {"std": 1.4369, "ac1": 0.6831},
    "Investment": {"std": 15.2645, "ac1": 0.5547},
    "Consumption": {"std": 1.1784, "ac1": 0.6778},
    "Unemployment": {"std": 17.3468, "ac1": 0.6530},
}


def _worker(payload):
    config, seed, periods, burn = payload
    result = run_seed(config, seed, periods, burn=burn, capture_diagnostics=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--periods", type=int, default=3000)
    parser.add_argument("--burn", type=int, default=1000)
    parser.add_argument("--seed-start", type=int, default=100)
    parser.add_argument("--num-seeds", type=int, default=20)
    parser.add_argument("--processes", type=int, default=4)
    parser.add_argument("--set", dest="overrides", action="append", default=[], help="Override config with dotted.path=value")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    config = load_config(config_path)
    overrides = [parse_override(text) for text in args.overrides]
    config = apply_overrides(config, overrides)

    seeds = list(range(args.seed_start, args.seed_start + args.num_seeds))
    payloads = [(config, seed, args.periods, args.burn) for seed in seeds]

    results = []
    if args.processes == 1:
        for payload in payloads:
            result = _worker(payload)
            results.append(result)
            print(
                f"seed={result['seed']} "
                f"GDP_std={result['metrics']['GDP']['std']:.4f} "
                f"GDP_ac1={result['metrics']['GDP']['ac1']:.4f} "
                f"meanU={result['summary']['mean_unemployment']:.2f}"
            )
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(args.processes) as pool:
            for result in pool.imap_unordered(_worker, payloads):
                results.append(result)
                print(
                    f"seed={result['seed']} "
                    f"GDP_std={result['metrics']['GDP']['std']:.4f} "
                    f"GDP_ac1={result['metrics']['GDP']['ac1']:.4f} "
                    f"meanU={result['summary']['mean_unemployment']:.2f}",
                    flush=True,
                )

    results.sort(key=lambda item: item["seed"])
    summary = summarize_table4(results)

    print("\nTable 4 comparison")
    for label in ("GDP", "Investment", "Consumption", "Unemployment"):
        print(
            f"{label:12s} "
            f"std={summary[label]['std_mean']:.4f} "
            f"(target {TABLE4_TARGETS[label]['std']:.4f}) "
            f"ac1={summary[label]['ac1_mean']:.4f} "
            f"(target {TABLE4_TARGETS[label]['ac1']:.4f})"
        )
    print(f"Mean employment={summary['mean_employment']:.2f}")
    print(f"Mean unemployment={summary['mean_unemployment']:.2f}")

    if args.output:
        payload = {
            "config": config_path,
            "overrides": dict(overrides),
            "periods": args.periods,
            "burn": args.burn,
            "seeds": seeds,
            "summary": summary,
            "per_seed": results,
            "targets": TABLE4_TARGETS,
        }
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        print(f"\nSaved benchmark results to {args.output}")


if __name__ == "__main__":
    main()
