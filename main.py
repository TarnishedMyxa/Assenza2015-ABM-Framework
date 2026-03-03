import yaml
from engine import SimulationEngine
import time


def main():

    # 1. Import Data
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Initialize the Engine (which creates all agents)
    economy = SimulationEngine(config)

    # 3. Run Simulation Loop
    for t in range(config['simulation']['periods']):
        data=economy.run_step()

    return data


if __name__ == "__main__":
    GDP=[]
    N=1
    for i in range(N):
        print(f"Running simulation {(i+1)/N*100:.0f}%...")
        start_time=time.perf_counter()
        data=main()
        end_time=time.perf_counter()
        print(f"Simulation completed in {end_time - start_time:.2f} seconds.")
