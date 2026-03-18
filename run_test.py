"""Quick test run using YAML config — no database needed."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from engine import runManager

settings = {
    "CONFIG": "YAML",
    "yaml_config_path": "config.yaml",
    "db_config_id": None,
    "create_new_config_in_db": False
}

rm = runManager(settings)
run = rm.create_new_run()

PERIODS = 1000
TRANSIENT = 200
gdp_series = []
employment_series = []
bank_equity_series = []
bankruptcies_series = []
total_credit_series = []
capital_stock_series = []
avg_wealth_series = []
avg_firm_liquidity_series = []
avg_production_series = []
total_demand_series = []

for t in range(PERIODS):
    run.run_step()

    # GDP = sum of C-firm production * price
    gdp = sum(f.production * f.price for f in run.c_firms)
    gdp_series.append(gdp)

    # Employment rate
    employed = sum(1 for w in run.workers if w.employed)
    employment_series.append(employed / len(run.workers) * 100)

    # Bank equity
    bank_equity_series.append(run.bank.equity)

    # Bankruptcies this period
    bankruptcies_series.append(len(run.to_process_bankruptcies))

    # Total outstanding credit (sum of firm debt)
    total_credit = sum(f.debt for f in run.c_firms) + sum(f.debt for f in run.k_firms)
    total_credit_series.append(total_credit)

    # Aggregate capital stock (C-firms)
    cap_stock = sum(f.capital for f in run.c_firms)
    capital_stock_series.append(cap_stock)

    # Average household wealth (workers only)
    avg_wealth = np.mean([w.wealth for w in run.workers])
    avg_wealth_series.append(avg_wealth)

    # Average C-firm liquidity
    avg_liq = np.mean([f.liquidity for f in run.c_firms])
    avg_firm_liquidity_series.append(avg_liq)

    # Average C-firm production
    avg_prod = np.mean([f.production for f in run.c_firms])
    avg_production_series.append(avg_prod)

    # Total household demand (budgets)
    total_demand = sum(h.budget for h in run.workers) + sum(h.budget for h in run.capitalists)
    total_demand_series.append(total_demand)

    if (t + 1) <= 10 or (t + 1) % 50 == 0:
        k_inv = sum(f.inventory for f in run.k_firms)
        k_prod = sum(f.production for f in run.k_firms)
        c_invest = sum(f.planned_investment for f in run.c_firms)
        avg_c_prod = np.mean([f.production for f in run.c_firms])
        avg_c_inv = np.mean([f.inventory for f in run.c_firms])
        c_workers = sum(len(f.staff) for f in run.c_firms)
        k_workers = sum(len(f.staff) for f in run.k_firms)
        print(f"t={t+1:4d}: GDP={gdp:.0f} Empl={employment_series[-1]:.1f}% "
              f"(C:{c_workers} K:{k_workers}) CapStock={cap_stock:.0f} "
              f"AvgCProd={avg_c_prod:.2f} AvgCInv={avg_c_inv:.2f} "
              f"KProd={k_prod:.1f} KInv={k_inv:.1f} CInvest={c_invest:.1f} "
              f"AvgW={avg_wealth:.2f} Credit={total_credit:.0f}")

# --- Basic plots ---
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('CC-MABM Simulation Results', fontsize=14)

axes[0, 0].plot(gdp_series)
axes[0, 0].set_title('GDP (nominal)')
axes[0, 0].set_xlabel('Period')

axes[0, 1].plot(employment_series)
axes[0, 1].set_title('Employment Rate (%)')
axes[0, 1].set_xlabel('Period')

axes[1, 0].plot(bank_equity_series)
axes[1, 0].set_title('Bank Equity')
axes[1, 0].set_xlabel('Period')

axes[1, 1].plot(bankruptcies_series)
axes[1, 1].set_title('Bankruptcies per Period')
axes[1, 1].set_xlabel('Period')

plt.tight_layout()
plt.savefig('simulation_results.png', dpi=150)
print(f"\nBasic plots saved to simulation_results.png")

# --- Diagnostic plots ---
fig2, axes2 = plt.subplots(2, 3, figsize=(18, 10))
fig2.suptitle('CC-MABM Diagnostic Plots', fontsize=14)

# HP-filtered GDP
gdp_arr = np.array(gdp_series)
positive_mask = gdp_arr > 0
if np.sum(positive_mask) > 10:
    log_gdp = np.log(gdp_arr[positive_mask])
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter
        cycle, trend = hpfilter(log_gdp, lamb=1600)
        axes2[0, 0].plot(np.where(positive_mask)[0], cycle, linewidth=0.8)
        axes2[0, 0].axhline(y=0, color='k', linestyle='--', alpha=0.3)
        axes2[0, 0].set_title('HP-filtered log GDP (cyclical component)')
    except ImportError:
        axes2[0, 0].plot(log_gdp)
        axes2[0, 0].set_title('Log GDP (no HP filter)')
else:
    axes2[0, 0].text(0.5, 0.5, 'GDP too low for log transform', ha='center', va='center')
    axes2[0, 0].set_title('HP-filtered log GDP')
axes2[0, 0].set_xlabel('Period')

# Total credit
axes2[0, 1].plot(total_credit_series, linewidth=0.8)
axes2[0, 1].set_title('Total Outstanding Credit')
axes2[0, 1].set_xlabel('Period')

# Capital stock
axes2[0, 2].plot(capital_stock_series, linewidth=0.8)
axes2[0, 2].set_title('Aggregate Capital Stock')
axes2[0, 2].set_xlabel('Period')

# Average worker wealth
axes2[1, 0].plot(avg_wealth_series, linewidth=0.8)
axes2[1, 0].set_title('Average Worker Wealth')
axes2[1, 0].set_xlabel('Period')

# Average C-firm liquidity
axes2[1, 1].plot(avg_firm_liquidity_series, linewidth=0.8)
axes2[1, 1].set_title('Average C-Firm Liquidity')
axes2[1, 1].set_xlabel('Period')

# Total household demand vs GDP
axes2[1, 2].plot(total_demand_series, linewidth=0.8, label='Total Demand')
axes2[1, 2].plot(gdp_series, linewidth=0.8, label='GDP', alpha=0.7)
axes2[1, 2].set_title('Demand vs GDP')
axes2[1, 2].set_xlabel('Period')
axes2[1, 2].legend()

plt.tight_layout()
plt.savefig('simulation_diagnostics.png', dpi=150)
print(f"Diagnostic plots saved to simulation_diagnostics.png")

# --- Summary statistics ---
if TRANSIENT < PERIODS:
    gdp_post = np.array(gdp_series[TRANSIENT:])
    empl_post = np.array(employment_series[TRANSIENT:])

    print(f"\nSummary (periods {TRANSIENT}-{PERIODS}):")
    print(f"  Mean GDP: {np.mean(gdp_post):.2f}")
    if np.mean(gdp_post) > 0:
        print(f"  GDP std dev: {np.std(gdp_post):.2f} ({np.std(gdp_post)/np.mean(gdp_post)*100:.2f}% of mean)")
    else:
        print(f"  GDP std dev: {np.std(gdp_post):.2f} (mean is zero)")
    print(f"  Mean employment: {np.mean(empl_post):.1f}%")
    print(f"  Total bankruptcies: {sum(bankruptcies_series)}")
    print(f"  Final bank equity: {bank_equity_series[-1]:.1f}")
    print(f"  Mean credit outstanding: {np.mean(total_credit_series[TRANSIENT:]):.1f}")
    print(f"  Final avg worker wealth: {avg_wealth_series[-1]:.2f}")
    print(f"  Final capital stock: {capital_stock_series[-1]:.1f}")

    # HP-filtered GDP statistics
    pos_post = gdp_post[gdp_post > 0]
    if len(pos_post) > 10:
        log_gdp_post = np.log(pos_post)
        try:
            from statsmodels.tsa.filters.hp_filter import hpfilter
            cycle_post, _ = hpfilter(log_gdp_post, lamb=1600)
            print(f"\n  HP-filtered log GDP:")
            print(f"    Std dev of cycle: {np.std(cycle_post)*100:.2f}% (target: ~1.66%)")
            if len(log_gdp_post) > 2:
                ac1 = np.corrcoef(log_gdp_post[:-1], log_gdp_post[1:])[0, 1]
                print(f"    Autocorrelation(1) of log GDP: {ac1:.3f} (target: ~0.85)")
        except ImportError:
            print("  (statsmodels not available — skipping HP filter stats)")
