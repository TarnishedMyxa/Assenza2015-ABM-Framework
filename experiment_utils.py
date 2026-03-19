import copy
import os
import random
import sys

import numpy as np
import yaml

from statsmodels.tsa.filters.hp_filter import hpfilter


REPO_ROOT = os.path.dirname(__file__)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine import SimulationEngine, ensure_experiment_defaults


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return ensure_experiment_defaults(config)


def parse_override(text):
    if "=" not in text:
        raise ValueError(f"Override must be KEY=VALUE, got: {text}")
    key, raw_value = text.split("=", 1)
    return key, yaml.safe_load(raw_value)


def set_nested(mapping, dotted_key, value):
    target = mapping
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            target[part] = {}
        target = target[part]
    target[parts[-1]] = value


def apply_overrides(config, overrides):
    updated = copy.deepcopy(config)
    for key, value in overrides:
        set_nested(updated, key, value)
    return ensure_experiment_defaults(updated)


def hp_moments(series, burn):
    arr = np.asarray(series[burn:], dtype=float)
    arr = np.maximum(arr, 1e-8)
    cycle, _ = hpfilter(np.log(arr), lamb=1600)
    cycle = np.asarray(cycle, dtype=float)
    std = float(np.std(cycle) * 100.0)
    if len(cycle) > 1 and np.std(cycle[:-1]) > 1e-12 and np.std(cycle[1:]) > 1e-12:
        ac1 = float(np.corrcoef(cycle[1:], cycle[:-1])[0, 1])
    else:
        ac1 = float("nan")
    return {"std": std, "ac1": ac1}


def longest_run_below(series, threshold):
    longest = 0
    current = 0
    for value in series:
        if value < threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def run_seed(config, seed, periods, burn=0, capture_diagnostics=False):
    config_copy = copy.deepcopy(config)
    if capture_diagnostics:
        config_copy.setdefault("experiments", {})
        config_copy["experiments"]["diagnostics"] = True
    config_copy = ensure_experiment_defaults(config_copy)

    random.seed(seed)
    np.random.seed(seed)
    run = SimulationEngine(config_copy, name=f"seed_{seed}", start_seed=seed)

    gdp = []
    consumption = []
    investment = []
    planned_investment = []
    investment_fulfillment = []
    k_queue_total = []
    employment = []
    unemployment = []
    bank_equity = []
    total_credit = []

    for _ in range(periods):
        run.run_step()
        gdp.append(sum(f.production for f in run.c_firms) + sum(f.production for f in run.k_firms))
        consumption.append(sum(f.sales for f in run.c_firms))
        realized_investment = sum(f.sales for f in run.k_firms)
        current_planned_investment = sum(f.planned_investment for f in run.c_firms)
        investment.append(realized_investment)
        planned_investment.append(current_planned_investment)
        investment_fulfillment.append(
            realized_investment / current_planned_investment if current_planned_investment > 0 else 0.0
        )
        k_queue_total.append(sum(f.queue for f in run.k_firms))
        employed = sum(1 for worker in run.workers if worker.employed)
        employment_rate = employed / len(run.workers) * 100.0
        employment.append(employment_rate)
        unemployment.append(100.0 - employment_rate)
        bank_equity.append(run.bank.equity)
        total_credit.append(sum(f.debt for f in run.c_firms) + sum(f.debt for f in run.k_firms))

    metrics = {
        "GDP": hp_moments(gdp, burn),
        "Investment": hp_moments(investment, burn),
        "Consumption": hp_moments(consumption, burn),
        "Unemployment": hp_moments(unemployment, burn),
    }

    return {
        "seed": seed,
        "metrics": metrics,
        "summary": {
            "mean_gdp": float(np.mean(gdp[burn:])),
            "mean_employment": float(np.mean(employment[burn:])),
            "mean_unemployment": float(np.mean(unemployment[burn:])),
            "max_bank_equity": float(np.max(bank_equity)),
            "max_total_credit": float(np.max(total_credit)),
            "longest_low_employment_run": int(longest_run_below(employment, 70.0)),
        },
        "series": {
            "gdp": gdp,
            "consumption": consumption,
            "investment": investment,
            "planned_investment": planned_investment,
            "investment_fulfillment": investment_fulfillment,
            "k_queue_total": k_queue_total,
            "employment": employment,
            "unemployment": unemployment,
            "bank_equity": bank_equity,
            "total_credit": total_credit,
        },
        "diagnostics": run.step_diagnostics_history if capture_diagnostics else [],
    }


def summarize_table4(results):
    summary = {}
    for label in ("GDP", "Investment", "Consumption", "Unemployment"):
        stds = [result["metrics"][label]["std"] for result in results]
        ac1s = [result["metrics"][label]["ac1"] for result in results]
        summary[label] = {
            "std_mean": float(np.mean(stds)),
            "std_sd": float(np.std(stds)),
            "ac1_mean": float(np.mean(ac1s)),
            "ac1_sd": float(np.std(ac1s)),
        }
    summary["mean_gdp"] = float(np.mean([result["summary"]["mean_gdp"] for result in results]))
    summary["mean_employment"] = float(np.mean([result["summary"]["mean_employment"] for result in results]))
    summary["mean_unemployment"] = float(np.mean([result["summary"]["mean_unemployment"] for result in results]))
    return summary
