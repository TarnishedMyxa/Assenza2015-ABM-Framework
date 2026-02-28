import yaml
from engine import SimulationEngine
import matplotlib.pyplot as plt
import numpy as np


def main():
    # 1. Import Data
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Initialize the Engine (which creates all agents)
    economy = SimulationEngine(config)

    GDP=[]

    # 3. Run Simulation Loop
    for t in range(config['simulation']['periods']):
        data=economy.run_step()
        GDP.append(data[0])

    #print(GDP)
    return GDP


if __name__ == "__main__":
    GDP=[]
    N=5
    for i in range(N):
        print(f"Running simulation {(i+1)/N*100}%...")
        """
        try:
            data=main()
        except:
            print("Error in simulation run, skipping...")
            continue
        GDP.append(data)
        """
        data=main()
        GDP.append(data)
    data = np.array(GDP, dtype=float)

    burn_in=1
    # Slice for "Post-Initialization" analysis
    data_subset = data[:, burn_in:]
    x = np.arange(burn_in, burn_in + data_subset.shape[1])

    # --- 3. IDENTIFY EXTREMES ---
    # Calculate the mean of each individual run to find best/worst overall performers
    run_means = np.mean(data_subset, axis=1)
    top_idx = np.argmax(run_means)
    bottom_idx = np.argmin(run_means)

    # --- 4. STATISTICAL TRACES ---
    ensemble_mean = np.mean(data_subset, axis=0)
    ensemble_std = np.std(data_subset, axis=0)

    # --- 5. PLOTTING ---
    plt.figure(figsize=(14, 7))

    # Plot all runs with high transparency
    for i, run in enumerate(data_subset):
        if i not in [top_idx, bottom_idx]:
            plt.plot(x, run, color='gray', alpha=0.03, linewidth=0.5)

    # Highlight the Extremes with distinct colors
    plt.plot(x, data_subset[top_idx], color='#2ecc71', linewidth=1.8,
             label=f'Best Performing Run (Index {top_idx})', zorder=5)
    plt.plot(x, data_subset[bottom_idx], color='#3498db', linewidth=1.8,
             label=f'Worst Performing Run (Index {bottom_idx})', zorder=5)

    # Plot the Global Mean
    plt.plot(x, ensemble_mean, color='red', linewidth=2.5,
             label='Ensemble Mean', zorder=6)

    # Add the 1 Std Dev Shadow
    plt.fill_between(x, ensemble_mean - ensemble_std, ensemble_mean + ensemble_std,
                     color='red', alpha=0.15, label='1 Std Dev Band', zorder=4)

    plt.title(f"GDP")
    plt.xlabel("Time Step (t)")
    plt.ylabel("GDP")
    plt.legend(loc='upper left')
    plt.grid(alpha=0.2)
    plt.show()